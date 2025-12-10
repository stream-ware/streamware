"""
Centralized LLM Client for Streamware

Provides unified interface for calling vision LLMs (Ollama, OpenAI, etc.)
with built-in optimizations:
- Connection pooling (requests.Session)
- Rate limiting
- Automatic retries
- Image optimization
- Metrics/timing

Usage:
    from streamware.llm_client import LLMClient, vision_query

    # Quick usage
    result = vision_query(image_path, "Describe what you see")

    # Full client
    client = LLMClient()
    result = client.analyze_image(image_path, prompt)
"""

import base64
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Union

import requests

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class LLMMetrics:
    """Track LLM performance metrics."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_time_ms: float = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    
    @property
    def avg_time_ms(self) -> float:
        return self.total_time_ms / max(1, self.total_calls)
    
    @property
    def success_rate(self) -> float:
        return self.successful_calls / max(1, self.total_calls)
    
    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "successful": self.successful_calls,
            "failed": self.failed_calls,
            "avg_time_ms": round(self.avg_time_ms, 1),
            "success_rate": f"{self.success_rate:.1%}",
        }


@dataclass
class LLMConfig:
    """LLM client configuration."""
    provider: str = "ollama"
    model: str = "llava:7b"
    ollama_url: str = "http://localhost:11434"
    timeout: int = 60
    max_retries: int = 2
    optimize_images: bool = True
    image_preset: str = "fast"
    
    @classmethod
    def from_env(cls) -> "LLMConfig":
        """Load config from environment/.env"""
        return cls(
            provider=config.get("SQ_LLM_PROVIDER", "ollama"),
            model=config.get("SQ_MODEL", "llava:7b"),
            ollama_url=config.get("SQ_OLLAMA_URL", "http://localhost:11434"),
            timeout=int(config.get("SQ_LLM_TIMEOUT", "60")),
            max_retries=int(config.get("SQ_LLM_RETRIES", "2")),
            optimize_images=config.get("SQ_IMAGE_OPTIMIZE", "true").lower() == "true",
            image_preset=config.get("SQ_IMAGE_PRESET", "fast"),
        )


class LLMClient:
    """Centralized LLM client with connection pooling and metrics."""
    
    _instance: Optional["LLMClient"] = None
    _lock = Lock()
    
    def __new__(cls, config: Optional[LLMConfig] = None):
        """Singleton pattern for connection reuse."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance
    
    def __init__(self, llm_config: Optional[LLMConfig] = None):
        if self._initialized:
            return
        
        self.config = llm_config or LLMConfig.from_env()
        self.metrics = LLMMetrics()
        
        # Connection pool
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
        })
        
        # Rate limiting (simple token bucket)
        self._last_call = 0.0
        self._min_interval = 0.1  # 100ms between calls
        
        self._initialized = True
    
    def analyze_image(
        self,
        image: Union[str, Path, bytes],
        prompt: str,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Analyze image with vision LLM.
        
        Args:
            image: Path to image, or raw bytes, or base64 string
            prompt: Analysis prompt
            model: Override model (optional)
            timeout: Override timeout (optional)
            
        Returns:
            Dict with 'response', 'success', 'time_ms', 'error'
        """
        start_time = time.time()
        self.metrics.total_calls += 1
        
        # Rate limiting
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call = time.time()
        
        try:
            # Prepare image
            image_b64 = self._prepare_image(image)
            
            # Call appropriate provider
            if self.config.provider == "ollama":
                result = self._call_ollama(
                    image_b64, 
                    prompt, 
                    model or self.config.model,
                    timeout or self.config.timeout
                )
            elif self.config.provider == "openai":
                result = self._call_openai(image_b64, prompt, model, timeout)
            else:
                result = {"success": False, "error": f"Unknown provider: {self.config.provider}"}
            
            # Record metrics
            time_ms = (time.time() - start_time) * 1000
            result["time_ms"] = round(time_ms, 1)
            self.metrics.total_time_ms += time_ms
            
            if result.get("success"):
                self.metrics.successful_calls += 1
            else:
                self.metrics.failed_calls += 1
            
            return result
            
        except Exception as e:
            self.metrics.failed_calls += 1
            time_ms = (time.time() - start_time) * 1000
            return {
                "success": False,
                "response": "",
                "error": str(e),
                "time_ms": round(time_ms, 1),
            }
    
    def _prepare_image(self, image: Union[str, Path, bytes]) -> str:
        """Convert image to optimized base64."""
        # Already base64?
        if isinstance(image, str) and not Path(image).exists():
            return image
        
        # Raw bytes?
        if isinstance(image, bytes):
            return base64.b64encode(image).decode()
        
        # File path - optimize if enabled
        image_path = Path(image)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image}")
        
        if self.config.optimize_images:
            from .image_optimize import prepare_image_for_llm_base64
            return prepare_image_for_llm_base64(image_path, preset=self.config.image_preset)
        else:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    
    def _call_ollama(
        self, 
        image_b64: str, 
        prompt: str, 
        model: str, 
        timeout: int
    ) -> Dict[str, Any]:
        """Call Ollama vision API."""
        url = f"{self.config.ollama_url}/api/generate"
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self._session.post(
                    url,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False,
                    },
                    timeout=timeout,
                )
                
                if response.ok:
                    data = response.json()
                    resp_text = data.get("response", "").strip()
                    # Debug: log if empty response
                    if not resp_text:
                        logger.warning(f"Ollama returned empty response. Raw data: {str(data)[:200]}")
                    return {
                        "success": True,
                        "response": resp_text,
                        "model": model,
                        "tokens_in": data.get("prompt_eval_count", 0),
                        "tokens_out": data.get("eval_count", 0),
                    }
                else:
                    if attempt < self.config.max_retries:
                        time.sleep(1)
                        continue
                    return {
                        "success": False,
                        "response": "",
                        "error": f"HTTP {response.status_code}",
                    }
                    
            except requests.exceptions.Timeout:
                if attempt < self.config.max_retries:
                    continue
                return {
                    "success": False,
                    "response": "",
                    "error": "Timeout",
                }
            except Exception as e:
                return {
                    "success": False,
                    "response": "",
                    "error": str(e),
                }
        
        return {"success": False, "response": "", "error": "Max retries exceeded"}
    
    def _call_openai(
        self, 
        image_b64: str, 
        prompt: str, 
        model: Optional[str], 
        timeout: Optional[int]
    ) -> Dict[str, Any]:
        """Call OpenAI vision API."""
        api_key = config.get("SQ_OPENAI_API_KEY")
        if not api_key:
            return {"success": False, "error": "SQ_OPENAI_API_KEY not set"}
        
        model = model or "gpt-4-vision-preview"
        
        try:
            response = self._session.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_b64}"
                                    }
                                }
                            ]
                        }
                    ],
                    "max_tokens": 300,
                },
                timeout=timeout or 60,
            )
            
            if response.ok:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return {
                    "success": True,
                    "response": content.strip(),
                    "model": model,
                }
            else:
                return {
                    "success": False,
                    "response": "",
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                }
        except Exception as e:
            return {"success": False, "response": "", "error": str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return self.metrics.to_dict()
    
    def reset_metrics(self):
        """Reset metrics counters."""
        self.metrics = LLMMetrics()


# Convenience functions

def get_client() -> LLMClient:
    """Get singleton LLM client instance."""
    return LLMClient()


def vision_query(
    image: Union[str, Path, bytes],
    prompt: str,
    model: Optional[str] = None,
) -> str:
    """Quick vision query - returns response text or error message."""
    client = get_client()
    result = client.analyze_image(image, prompt, model=model)
    if result.get("success"):
        return result.get("response", "")
    else:
        return f"Error: {result.get('error', 'Unknown error')}"


def analyze_with_timing(
    image: Union[str, Path],
    prompt: str,
) -> Dict[str, Any]:
    """Analyze image and return full result with timing."""
    client = get_client()
    return client.analyze_image(image, prompt)
