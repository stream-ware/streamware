"""
Concurrent Frame Processor - Non-blocking frame analysis with timeout

Architecture:
- FastCapture produces frames at configured FPS
- FrameProcessor manages a pool of workers
- Each frame is processed independently with timeout
- Slow frames don't block new captures

Usage:
    processor = ConcurrentFrameProcessor(max_workers=2, timeout=5.0)
    processor.start()
    
    # Submit frames (non-blocking)
    processor.submit(frame_path, frame_num, callback=on_result)
    
    # Or get results
    results = processor.get_results()  # Non-blocking, returns available results
    
    processor.stop()
"""

import logging
import time
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError, Future
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue, Empty
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class FrameTask:
    """A frame processing task."""
    frame_path: Path
    frame_num: int
    frame_data: Any = None  # Pre-loaded numpy array
    submitted_at: float = field(default_factory=time.time)
    priority: int = 0  # Higher = more important


@dataclass 
class FrameResult:
    """Result of frame processing."""
    frame_num: int
    success: bool
    description: str = ""
    summary: str = ""
    processing_time_ms: float = 0
    error: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class ConcurrentFrameProcessor:
    """Process frames concurrently with timeout support.
    
    Key features:
    - Non-blocking frame submission
    - Configurable worker pool (default: 2 workers)
    - Timeout per frame (default: 5s)
    - Automatic cancellation of slow tasks
    - Results queue for async consumption
    """
    
    def __init__(
        self,
        max_workers: int = None,
        timeout: float = None,
        model: str = None,
        ollama_url: str = None,
        focus: str = "person",
    ):
        # Load from config with defaults
        self.max_workers = max_workers or int(config.get("SQ_CONCURRENT_WORKERS", "2"))
        
        # Calculate timeout from FPS/interval (not hardcoded)
        # timeout = interval between frames = 1/FPS
        if timeout:
            self.timeout = timeout
        else:
            stream_interval = float(config.get("SQ_STREAM_INTERVAL", "5"))
            capture_fps = float(config.get("SQ_CAPTURE_FPS", "0.2"))
            # Use the larger of: stream_interval or 1/capture_fps
            self.timeout = max(stream_interval, 1.0 / capture_fps if capture_fps > 0 else 5.0)
        
        self.model = model or config.get("SQ_MODEL", "llava:7b")
        self.ollama_url = ollama_url or config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        self.focus = focus
        
        # Thread pool
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running = False
        
        # Task tracking
        self._pending_futures: Dict[int, Future] = {}  # frame_num -> future
        self._results_queue: Queue[FrameResult] = Queue()
        
        # Stats
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "timed_out": 0,
            "errors": 0,
            "avg_time_ms": 0,
            "total_time_ms": 0,
        }
        
        # Lock for thread safety
        self._lock = threading.Lock()
        
    def start(self):
        """Start the processor."""
        if self._running:
            return
            
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="frame_worker"
        )
        self._running = True
        
        # Start cleanup thread for timed-out tasks
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"ConcurrentFrameProcessor started: {self.max_workers} workers, {self.timeout}s timeout")
        
    def stop(self):
        """Stop the processor and wait for pending tasks."""
        self._running = False
        
        if self._executor:
            # Cancel pending futures
            with self._lock:
                for frame_num, future in self._pending_futures.items():
                    future.cancel()
                self._pending_futures.clear()
            
            self._executor.shutdown(wait=False)
            self._executor = None
            
        logger.info(f"ConcurrentFrameProcessor stopped. Stats: {self._stats}")
        
    def submit(
        self, 
        frame_path: Path, 
        frame_num: int,
        frame_data: Any = None,
        callback: Callable[[FrameResult], None] = None,
    ) -> bool:
        """Submit a frame for processing (non-blocking).
        
        Args:
            frame_path: Path to frame image
            frame_num: Frame number for tracking
            frame_data: Optional pre-loaded image data (numpy array)
            callback: Optional callback when result is ready
            
        Returns:
            True if submitted, False if processor not running
        """
        if not self._running or not self._executor:
            return False
            
        task = FrameTask(
            frame_path=frame_path,
            frame_num=frame_num,
            frame_data=frame_data,
        )
        
        # Submit to thread pool
        future = self._executor.submit(self._process_frame, task, callback)
        
        with self._lock:
            # Cancel old task for same frame if exists
            if frame_num in self._pending_futures:
                self._pending_futures[frame_num].cancel()
            self._pending_futures[frame_num] = future
            self._stats["submitted"] += 1
            
        return True
        
    def get_results(self, max_results: int = 10) -> List[FrameResult]:
        """Get available results (non-blocking).
        
        Returns:
            List of completed results (may be empty)
        """
        results = []
        for _ in range(max_results):
            try:
                result = self._results_queue.get_nowait()
                results.append(result)
            except Empty:
                break
        return results
        
    def get_latest_result(self) -> Optional[FrameResult]:
        """Get the most recent result (non-blocking)."""
        results = self.get_results(max_results=100)
        if results:
            # Return highest frame_num (most recent)
            return max(results, key=lambda r: r.frame_num)
        return None
        
    def _process_frame(
        self, 
        task: FrameTask, 
        callback: Callable[[FrameResult], None] = None
    ) -> FrameResult:
        """Process a single frame (runs in worker thread)."""
        start_time = time.time()
        result = FrameResult(frame_num=task.frame_num, success=False)
        
        try:
            # Import here to avoid circular imports
            from .image_optimizer import optimize_for_llm, get_optimal_size_for_model
            from .response_filter import is_significant_smart
            
            # Optimize image
            optimal_size = get_optimal_size_for_model(self.model)
            optimized_path = optimize_for_llm(
                task.frame_path, 
                max_size=optimal_size, 
                quality=75,
                image_data=task.frame_data
            )
            
            if not optimized_path or not optimized_path.exists():
                optimized_path = task.frame_path
                
            # Call LLM
            description = self._call_llm(optimized_path)
            
            if description:
                # Validate with guarder
                is_significant, summary = is_significant_smart(
                    description,
                    focus=self.focus,
                    tracking_data={},
                )
                
                result.success = True
                result.description = description
                result.summary = summary if is_significant else ""
            else:
                result.error = "No LLM response"
                
        except Exception as e:
            result.error = str(e)
            logger.debug(f"Frame {task.frame_num} processing error: {e}")
            
        # Calculate timing
        result.processing_time_ms = (time.time() - start_time) * 1000
        
        # Update stats
        with self._lock:
            self._stats["completed"] += 1
            self._stats["total_time_ms"] += result.processing_time_ms
            self._stats["avg_time_ms"] = self._stats["total_time_ms"] / self._stats["completed"]
            
            if task.frame_num in self._pending_futures:
                del self._pending_futures[task.frame_num]
                
            if not result.success:
                self._stats["errors"] += 1
                
        # Queue result
        self._results_queue.put(result)
        
        # Callback if provided
        if callback:
            try:
                callback(result)
            except Exception as e:
                logger.debug(f"Callback error: {e}")
                
        return result
        
    def _call_llm(self, image_path: Path) -> str:
        """Call vision LLM for image description."""
        import requests
        import base64
        
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
                
            # Build prompt
            prompt = f"Look at this image carefully. Is there a {self.focus} visible? Describe what you see briefly."
            
            # Call Ollama
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                },
                timeout=self.timeout,
            )
            
            if response.ok:
                return response.json().get("response", "")
                
        except requests.Timeout:
            logger.debug(f"LLM timeout ({self.timeout}s)")
            with self._lock:
                self._stats["timed_out"] += 1
        except Exception as e:
            logger.debug(f"LLM error: {e}")
            
        return ""
        
    def _cleanup_loop(self):
        """Background thread to cleanup timed-out tasks."""
        while self._running:
            time.sleep(1.0)  # Check every second
            
            now = time.time()
            with self._lock:
                to_cancel = []
                for frame_num, future in self._pending_futures.items():
                    # Check if task has been running too long
                    if not future.done():
                        # Future doesn't track start time, so we rely on timeout in requests
                        pass
                        
                for frame_num in to_cancel:
                    if frame_num in self._pending_futures:
                        self._pending_futures[frame_num].cancel()
                        del self._pending_futures[frame_num]
                        
    @property
    def stats(self) -> Dict:
        """Get processor statistics."""
        with self._lock:
            return self._stats.copy()
            
    @property
    def pending_count(self) -> int:
        """Number of pending tasks."""
        with self._lock:
            return len(self._pending_futures)


# Singleton instance
_processor: Optional[ConcurrentFrameProcessor] = None


def get_concurrent_processor(**kwargs) -> ConcurrentFrameProcessor:
    """Get or create the concurrent frame processor."""
    global _processor
    if _processor is None:
        _processor = ConcurrentFrameProcessor(**kwargs)
    return _processor


def stop_concurrent_processor():
    """Stop the global processor."""
    global _processor
    if _processor:
        _processor.stop()
        _processor = None
