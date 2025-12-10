"""
Parallel Processor - Multi-threaded processing for high-performance systems

Features:
- Parallel capture and processing pipeline
- Concurrent LLM calls
- Background image optimization
- Thread pool management
- Work queue with priority

Optimized for systems with multiple cores and high RAM.

Usage:
    from streamware.parallel_processor import ParallelProcessor
    
    processor = ParallelProcessor(max_workers=8)
    processor.start()
    
    # Submit tasks
    future = processor.submit_capture(rtsp_url)
    future = processor.submit_llm(image_path, prompt)
    
    processor.stop()
"""

import logging
import os
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from threading import Lock, Event

from .config import config

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels."""
    HIGH = 0      # Capture, critical processing
    NORMAL = 1    # LLM calls
    LOW = 2       # Optimization, caching


@dataclass
class Task:
    """A task to be processed."""
    id: str
    priority: TaskPriority
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)
    
    def __lt__(self, other):
        return self.priority.value < other.priority.value


@dataclass
class ProcessingResult:
    """Result of parallel processing."""
    task_id: str
    success: bool
    result: Any = None
    error: str = ""
    duration_ms: float = 0


class ParallelProcessor:
    """Multi-threaded task processor."""
    
    def __init__(self, max_workers: int = None):
        # Auto-detect optimal worker count
        if max_workers is None:
            cpu_count = os.cpu_count() or 4
            # Use half of CPUs for I/O-bound tasks, leave rest for main processing
            max_workers = max(4, cpu_count // 2)
        
        self.max_workers = max_workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._running = False
        self._lock = Lock()
        
        # Task tracking
        self._pending_futures: Dict[str, Future] = {}
        self._results: Dict[str, ProcessingResult] = {}
        self._task_counter = 0
        
        # Stats
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._total_time_ms = 0
    
    def start(self):
        """Start the processor."""
        if self._running:
            return
        
        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="sw_parallel"
        )
        self._running = True
        logger.info(f"ParallelProcessor started with {self.max_workers} workers")
    
    def stop(self):
        """Stop the processor."""
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=False)
            self._executor = None
        logger.info("ParallelProcessor stopped")
    
    def submit(
        self,
        func: Callable,
        *args,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Callable = None,
        **kwargs
    ) -> Optional[Future]:
        """Submit a task for parallel execution.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            priority: Task priority
            callback: Called with result when done
            **kwargs: Keyword arguments
            
        Returns:
            Future object or None if not running
        """
        if not self._running or not self._executor:
            # Execute synchronously if not running
            try:
                result = func(*args, **kwargs)
                if callback:
                    callback(result)
                return None
            except Exception as e:
                logger.error(f"Sync execution failed: {e}")
                return None
        
        with self._lock:
            self._task_counter += 1
            task_id = f"task_{self._task_counter}"
        
        def wrapped_task():
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = (time.perf_counter() - start) * 1000
                
                with self._lock:
                    self._tasks_completed += 1
                    self._total_time_ms += duration
                
                if callback:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")
                
                return ProcessingResult(
                    task_id=task_id,
                    success=True,
                    result=result,
                    duration_ms=duration
                )
            except Exception as e:
                duration = (time.perf_counter() - start) * 1000
                
                with self._lock:
                    self._tasks_failed += 1
                
                return ProcessingResult(
                    task_id=task_id,
                    success=False,
                    error=str(e),
                    duration_ms=duration
                )
        
        future = self._executor.submit(wrapped_task)
        
        with self._lock:
            self._pending_futures[task_id] = future
        
        return future
    
    def submit_capture(self, capture_func: Callable, *args, **kwargs) -> Future:
        """Submit a capture task (high priority)."""
        return self.submit(capture_func, *args, priority=TaskPriority.HIGH, **kwargs)
    
    def submit_llm(self, llm_func: Callable, *args, **kwargs) -> Future:
        """Submit an LLM task (normal priority)."""
        return self.submit(llm_func, *args, priority=TaskPriority.NORMAL, **kwargs)
    
    def submit_optimize(self, optimize_func: Callable, *args, **kwargs) -> Future:
        """Submit an optimization task (low priority)."""
        return self.submit(optimize_func, *args, priority=TaskPriority.LOW, **kwargs)
    
    def wait_for(self, future: Future, timeout: float = None) -> Optional[ProcessingResult]:
        """Wait for a specific future to complete."""
        if future is None:
            return None
        try:
            return future.result(timeout=timeout)
        except Exception as e:
            return ProcessingResult(
                task_id="unknown",
                success=False,
                error=str(e)
            )
    
    def wait_all(self, futures: List[Future], timeout: float = None) -> List[ProcessingResult]:
        """Wait for multiple futures to complete."""
        results = []
        for future in as_completed(futures, timeout=timeout):
            try:
                results.append(future.result())
            except Exception as e:
                results.append(ProcessingResult(
                    task_id="unknown",
                    success=False,
                    error=str(e)
                ))
        return results
    
    @property
    def stats(self) -> dict:
        """Get processor statistics."""
        with self._lock:
            avg_time = self._total_time_ms / max(1, self._tasks_completed)
            return {
                "workers": self.max_workers,
                "completed": self._tasks_completed,
                "failed": self._tasks_failed,
                "avg_time_ms": avg_time,
                "pending": len(self._pending_futures),
            }


class PipelineStage:
    """A stage in the processing pipeline."""
    
    def __init__(self, name: str, func: Callable, workers: int = 1):
        self.name = name
        self.func = func
        self.workers = workers
        self._executor: Optional[ThreadPoolExecutor] = None
        self._input_queue: queue.Queue = queue.Queue()
        self._output_queue: queue.Queue = queue.Queue()
        self._running = False
        self._threads: List[threading.Thread] = []
    
    def start(self):
        """Start the stage."""
        self._running = True
        for i in range(self.workers):
            t = threading.Thread(target=self._worker, daemon=True, name=f"{self.name}_{i}")
            t.start()
            self._threads.append(t)
    
    def stop(self):
        """Stop the stage."""
        self._running = False
        # Send poison pills
        for _ in range(self.workers):
            self._input_queue.put(None)
        for t in self._threads:
            t.join(timeout=2)
    
    def _worker(self):
        """Worker thread."""
        while self._running:
            try:
                item = self._input_queue.get(timeout=0.5)
                if item is None:
                    break
                
                result = self.func(item)
                self._output_queue.put(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Pipeline stage {self.name} error: {e}")
    
    def put(self, item):
        """Add item to input queue."""
        self._input_queue.put(item)
    
    def get(self, timeout: float = None):
        """Get item from output queue."""
        return self._output_queue.get(timeout=timeout)


class ParallelPipeline:
    """Multi-stage parallel processing pipeline.
    
    Stages:
    1. Capture (1-2 workers) - Frame capture from RTSP
    2. Detect (2-4 workers) - SmartDetector analysis
    3. Optimize (2 workers) - Image optimization
    4. LLM (1-2 workers) - Vision LLM calls
    5. Filter (1 worker) - Response filtering
    """
    
    def __init__(self, num_capture: int = 2, num_detect: int = 4, num_llm: int = 2):
        self.stages: Dict[str, PipelineStage] = {}
        self._running = False
        
        # Configuration
        self.num_capture = num_capture
        self.num_detect = num_detect
        self.num_llm = num_llm
    
    def add_stage(self, name: str, func: Callable, workers: int = 1):
        """Add a processing stage."""
        self.stages[name] = PipelineStage(name, func, workers)
    
    def start(self):
        """Start all stages."""
        for stage in self.stages.values():
            stage.start()
        self._running = True
        logger.info(f"ParallelPipeline started with {len(self.stages)} stages")
    
    def stop(self):
        """Stop all stages."""
        self._running = False
        for stage in self.stages.values():
            stage.stop()
        logger.info("ParallelPipeline stopped")
    
    def process(self, stage_name: str, item):
        """Submit item to a specific stage."""
        if stage_name in self.stages:
            self.stages[stage_name].put(item)
    
    def get_result(self, stage_name: str, timeout: float = None):
        """Get result from a specific stage."""
        if stage_name in self.stages:
            return self.stages[stage_name].get(timeout=timeout)
        return None


# Global processor instance
_processor: Optional[ParallelProcessor] = None


def get_processor(max_workers: int = None) -> ParallelProcessor:
    """Get or create the global parallel processor."""
    global _processor
    
    if _processor is None:
        _processor = ParallelProcessor(max_workers)
        _processor.start()
    
    return _processor


def shutdown_processor():
    """Shutdown the global processor."""
    global _processor
    if _processor:
        _processor.stop()
        _processor = None
