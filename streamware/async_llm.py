"""
Async LLM Inference

Non-blocking LLM calls for improved throughput.
Allows processing next frame while waiting for LLM response.

Usage:
    from streamware.async_llm import AsyncLLM
    
    llm = AsyncLLM()
    
    # Submit request (non-blocking)
    future = llm.submit(prompt, image_path, model="llava:7b")
    
    # Do other work...
    process_next_frame()
    
    # Get result when ready
    response = future.result(timeout=10)
"""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from typing import Optional, Dict, Any, Callable
from queue import Queue
import requests

logger = logging.getLogger(__name__)


@dataclass
class LLMRequest:
    """Pending LLM request."""
    prompt: str
    image_path: Optional[str] = None
    model: str = "llava:7b"
    frame_num: int = 0
    timestamp: float = 0.0


@dataclass 
class LLMResponse:
    """LLM response with timing info."""
    text: str
    model: str
    frame_num: int
    latency_ms: float
    success: bool = True
    error: Optional[str] = None


class AsyncLLM:
    """
    Async LLM inference manager.
    
    Maintains a pool of workers for non-blocking LLM calls.
    Results are queued and can be retrieved later.
    """
    
    def __init__(
        self,
        max_workers: int = 2,
        ollama_url: str = "http://localhost:11434",
        default_model: str = "llava:7b",
        timeout: int = 30,
    ):
        self.ollama_url = ollama_url
        self.default_model = default_model
        self.timeout = timeout
        
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="llm")
        self._pending: Dict[int, Future] = {}  # frame_num -> Future
        self._results: Queue = Queue()
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "total_latency_ms": 0,
        }
    
    def submit(
        self,
        prompt: str,
        image_path: Optional[str] = None,
        model: Optional[str] = None,
        frame_num: int = 0,
    ) -> Future:
        """
        Submit LLM request (non-blocking).
        
        Returns Future that can be checked later.
        """
        model = model or self.default_model
        request = LLMRequest(
            prompt=prompt,
            image_path=image_path,
            model=model,
            frame_num=frame_num,
            timestamp=time.time(),
        )
        
        future = self._executor.submit(self._process_request, request)
        self._pending[frame_num] = future
        self._stats["submitted"] += 1
        
        return future
    
    def _process_request(self, request: LLMRequest) -> LLMResponse:
        """Process single LLM request."""
        start_time = time.time()
        
        try:
            # Build request payload
            payload = {
                "model": request.model,
                "prompt": request.prompt,
                "stream": False,
                "options": {
                    "num_predict": 100,
                    "temperature": 0.1,
                }
            }
            
            # Add image if provided
            if request.image_path:
                import base64
                with open(request.image_path, 'rb') as f:
                    image_b64 = base64.b64encode(f.read()).decode()
                payload["images"] = [image_b64]
            
            # Make request
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=self.timeout,
            )
            
            if response.status_code == 200:
                data = response.json()
                text = data.get("response", "").strip()
                latency_ms = (time.time() - start_time) * 1000
                
                self._stats["completed"] += 1
                self._stats["total_latency_ms"] += latency_ms
                
                result = LLMResponse(
                    text=text,
                    model=request.model,
                    frame_num=request.frame_num,
                    latency_ms=latency_ms,
                )
                self._results.put(result)
                return result
            else:
                raise Exception(f"HTTP {response.status_code}")
                
        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._stats["failed"] += 1
            
            result = LLMResponse(
                text="",
                model=request.model,
                frame_num=request.frame_num,
                latency_ms=latency_ms,
                success=False,
                error=str(e),
            )
            self._results.put(result)
            return result
    
    def get_result(self, frame_num: int, timeout: float = 0) -> Optional[LLMResponse]:
        """
        Get result for specific frame.
        
        Args:
            frame_num: Frame number to get result for
            timeout: Max seconds to wait (0 = don't wait)
            
        Returns:
            LLMResponse or None if not ready
        """
        future = self._pending.get(frame_num)
        if not future:
            return None
        
        if timeout > 0:
            try:
                return future.result(timeout=timeout)
            except:
                return None
        else:
            if future.done():
                return future.result()
            return None
    
    def get_any_result(self, timeout: float = 0) -> Optional[LLMResponse]:
        """Get any completed result from queue."""
        try:
            return self._results.get(timeout=timeout if timeout > 0 else 0.001)
        except:
            return None
    
    def pending_count(self) -> int:
        """Number of pending requests."""
        return sum(1 for f in self._pending.values() if not f.done())
    
    def wait_all(self, timeout: float = 30) -> int:
        """Wait for all pending requests. Returns completed count."""
        completed = 0
        deadline = time.time() + timeout
        
        for frame_num, future in list(self._pending.items()):
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                future.result(timeout=remaining)
                completed += 1
            except:
                pass
        
        return completed
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get statistics."""
        avg_latency = 0
        if self._stats["completed"] > 0:
            avg_latency = self._stats["total_latency_ms"] / self._stats["completed"]
        
        return {
            **self._stats,
            "pending": self.pending_count(),
            "avg_latency_ms": avg_latency,
        }
    
    def shutdown(self):
        """Shutdown executor."""
        self._executor.shutdown(wait=False)


# Global instance
_async_llm: Optional[AsyncLLM] = None


def get_async_llm(
    max_workers: int = 2,
    ollama_url: str = None,
) -> AsyncLLM:
    """Get or create global async LLM instance."""
    global _async_llm
    
    if _async_llm is None:
        from .config import config
        url = ollama_url or config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        _async_llm = AsyncLLM(max_workers=max_workers, ollama_url=url)
    
    return _async_llm


def shutdown_async_llm():
    """Shutdown global instance."""
    global _async_llm
    if _async_llm:
        _async_llm.shutdown()
        _async_llm = None
