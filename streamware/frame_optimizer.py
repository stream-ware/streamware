"""
Frame Optimizer for Streamware

Provides intelligent frame processing optimizations:
- Adaptive frame rate based on motion
- SSIM-based frame caching (skip similar frames)
- Local person detection (OpenCV HOG)
- Resolution scaling for LLM

Usage:
    from streamware.frame_optimizer import FrameOptimizer
    
    optimizer = FrameOptimizer()
    
    # Check if frame should be processed
    should_process, reason = optimizer.should_process_frame(frame_path)
    
    # Get adaptive interval
    interval = optimizer.get_adaptive_interval(motion_percent)
    
    # Detect person locally (no LLM)
    has_person, confidence = optimizer.detect_person_local(frame_path)
"""

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# numpy is optional - graceful fallback
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

logger = logging.getLogger(__name__)


@dataclass
class FrameStats:
    """Statistics for a processed frame."""
    timestamp: float
    motion_percent: float = 0.0
    ssim_score: float = 1.0
    has_person: bool = False
    person_confidence: float = 0.0
    processing_time_ms: float = 0.0


@dataclass
class OptimizerConfig:
    """Configuration for frame optimizer."""
    # Adaptive interval settings
    min_interval: float = 1.0      # Minimum interval (high activity)
    max_interval: float = 10.0     # Maximum interval (no activity)
    base_interval: float = 3.0     # Default interval
    
    # Motion thresholds
    high_motion_threshold: float = 10.0   # Above this = high activity
    low_motion_threshold: float = 2.0     # Below this = low activity
    skip_motion_threshold: float = 0.5    # Below this = skip LLM
    
    # SSIM cache settings
    ssim_threshold: float = 0.95   # Above this = frames are "same"
    cache_size: int = 5            # Number of frames to cache
    
    # Person detection
    use_local_detection: bool = True
    person_confidence_threshold: float = 0.5
    
    # Resolution scaling
    max_width: int = 640           # Max width for LLM
    max_height: int = 480          # Max height for LLM


class FrameOptimizer:
    """Intelligent frame processing optimizer."""
    
    def __init__(self, config: OptimizerConfig = None):
        self.config = config or OptimizerConfig()
        self._frame_cache: List[Tuple[Any, float]] = []  # (frame, timestamp)
        self._last_motion: float = 0.0
        self._last_interval: float = self.config.base_interval
        self._hog_detector = None
        self._stats: List[FrameStats] = []
        
    def get_adaptive_interval(self, motion_percent: float) -> float:
        """Calculate adaptive interval based on motion.
        
        High motion → short interval (more frequent checks)
        Low motion → long interval (save resources)
        
        Args:
            motion_percent: Current motion percentage (0-100)
            
        Returns:
            Recommended interval in seconds
        """
        self._last_motion = motion_percent
        
        if motion_percent >= self.config.high_motion_threshold:
            # High activity - check frequently
            interval = self.config.min_interval
        elif motion_percent <= self.config.low_motion_threshold:
            # Low activity - check less often
            interval = self.config.max_interval
        else:
            # Scale linearly between thresholds
            motion_range = self.config.high_motion_threshold - self.config.low_motion_threshold
            interval_range = self.config.max_interval - self.config.min_interval
            
            normalized = (motion_percent - self.config.low_motion_threshold) / motion_range
            interval = self.config.max_interval - (normalized * interval_range)
        
        # Smooth transitions (don't jump too fast)
        if abs(interval - self._last_interval) > 2.0:
            interval = self._last_interval + (2.0 if interval > self._last_interval else -2.0)
        
        self._last_interval = interval
        return interval
    
    def should_process_frame(
        self, 
        frame_path: Path,
        motion_percent: float = None
    ) -> Tuple[bool, str]:
        """Determine if frame should be processed by LLM.
        
        Uses multiple signals:
        - Motion percentage
        - SSIM similarity to cached frames
        - Local person detection
        
        Args:
            frame_path: Path to current frame
            motion_percent: Optional pre-computed motion
            
        Returns:
            (should_process, reason) tuple
        """
        # Skip SSIM check if numpy not available
        if not HAS_NUMPY:
            # Just check motion threshold
            if motion_percent is not None and motion_percent < self.config.skip_motion_threshold:
                return False, f"low_motion_{motion_percent:.1f}%"
            return True, "process"
        
        try:
            from PIL import Image
            img = Image.open(frame_path)
            frame_array = np.array(img.convert('L'))  # Grayscale
        except Exception as e:
            logger.debug(f"Failed to load frame: {e}")
            return True, "load_failed"
        
        # Check motion threshold
        if motion_percent is not None and motion_percent < self.config.skip_motion_threshold:
            return False, f"low_motion_{motion_percent:.1f}%"
        
        # Check SSIM against cached frames
        if self._frame_cache:
            for cached_frame, cached_time in self._frame_cache[-3:]:  # Check last 3
                try:
                    ssim = self._compute_ssim(frame_array, cached_frame)
                    if ssim > self.config.ssim_threshold:
                        return False, f"ssim_cached_{ssim:.2f}"
                except Exception:
                    pass
        
        # Local person detection (if enabled)
        if self.config.use_local_detection:
            has_person, confidence = self.detect_person_local(frame_path)
            if not has_person and confidence < 0.3:
                # No person detected locally - might skip LLM
                # But still process occasionally to catch edge cases
                if len(self._stats) > 0 and len(self._stats) % 5 != 0:
                    return False, f"no_person_local_{confidence:.2f}"
        
        # Add to cache
        self._add_to_cache(frame_array)
        
        return True, "process"
    
    def detect_person_local(self, frame_path: Path) -> Tuple[bool, float]:
        """Detect person using local OpenCV HOG detector.
        
        Much faster than LLM, good for pre-filtering.
        
        Args:
            frame_path: Path to frame
            
        Returns:
            (has_person, confidence) tuple
        """
        try:
            import cv2
            
            # Initialize HOG detector (lazy)
            if self._hog_detector is None:
                self._hog_detector = cv2.HOGDescriptor()
                self._hog_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            # Load and resize image
            img = cv2.imread(str(frame_path))
            if img is None:
                return False, 0.0
            
            # Resize for speed
            height, width = img.shape[:2]
            scale = min(400 / width, 400 / height, 1.0)
            if scale < 1.0:
                img = cv2.resize(img, None, fx=scale, fy=scale)
            
            # Detect
            boxes, weights = self._hog_detector.detectMultiScale(
                img,
                winStride=(8, 8),
                padding=(4, 4),
                scale=1.05
            )
            
            if len(boxes) > 0:
                confidence = float(max(weights)) if len(weights) > 0 else 0.5
                return True, min(confidence, 1.0)
            
            return False, 0.0
            
        except ImportError:
            logger.debug("OpenCV not available for local detection")
            return True, 0.5  # Assume person might be there
        except Exception as e:
            logger.debug(f"Local detection failed: {e}")
            return True, 0.5
    
    def optimize_frame_for_llm(
        self, 
        frame_path: Path,
        output_path: Path = None
    ) -> Path:
        """Optimize frame for LLM processing.
        
        - Resize to max dimensions
        - Convert to efficient format
        - Apply light preprocessing
        
        Args:
            frame_path: Input frame path
            output_path: Optional output path
            
        Returns:
            Path to optimized frame
        """
        try:
            from PIL import Image
            
            img = Image.open(frame_path)
            width, height = img.size
            
            # Calculate scale
            scale = min(
                self.config.max_width / width,
                self.config.max_height / height,
                1.0
            )
            
            if scale < 1.0:
                new_size = (int(width * scale), int(height * scale))
                img = img.resize(new_size, Image.LANCZOS)
            
            # Save optimized
            if output_path is None:
                output_path = frame_path.parent / f"opt_{frame_path.name}"
            
            img.save(output_path, "JPEG", quality=85, optimize=True)
            return output_path
            
        except Exception as e:
            logger.debug(f"Frame optimization failed: {e}")
            return frame_path
    
    def _compute_ssim(self, img1: Any, img2: Any) -> float:
        """Compute Structural Similarity Index between two images.
        
        Simplified SSIM for speed.
        """
        if not HAS_NUMPY or np is None:
            return 0.0  # Can't compute without numpy
        
        # Ensure same size
        if img1.shape != img2.shape:
            from PIL import Image
            img2_pil = Image.fromarray(img2)
            img2_pil = img2_pil.resize((img1.shape[1], img1.shape[0]))
            img2 = np.array(img2_pil)
        
        # Simple SSIM approximation
        c1 = 6.5025  # (0.01 * 255)^2
        c2 = 58.5225  # (0.03 * 255)^2
        
        img1 = img1.astype(np.float64)
        img2 = img2.astype(np.float64)
        
        mu1 = np.mean(img1)
        mu2 = np.mean(img2)
        
        sigma1_sq = np.var(img1)
        sigma2_sq = np.var(img2)
        sigma12 = np.mean((img1 - mu1) * (img2 - mu2))
        
        ssim = ((2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)) / \
               ((mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2))
        
        return float(ssim)
    
    def _add_to_cache(self, frame: Any):
        """Add frame to cache."""
        self._frame_cache.append((frame, time.time()))
        
        # Trim cache
        if len(self._frame_cache) > self.config.cache_size:
            self._frame_cache = self._frame_cache[-self.config.cache_size:]
    
    def get_stats(self) -> Dict:
        """Get optimizer statistics."""
        if not self._stats:
            return {}
        
        return {
            "frames_processed": len(self._stats),
            "avg_motion": sum(s.motion_percent for s in self._stats) / len(self._stats),
            "person_detections": sum(1 for s in self._stats if s.has_person),
            "avg_processing_ms": sum(s.processing_time_ms for s in self._stats) / len(self._stats),
            "current_interval": self._last_interval,
        }
    
    def reset(self):
        """Reset optimizer state."""
        self._frame_cache.clear()
        self._stats.clear()
        self._last_motion = 0.0
        self._last_interval = self.config.base_interval


class BatchGuarder:
    """Batch multiple guarder requests for efficiency."""
    
    def __init__(self, batch_size: int = 3, timeout: float = 5.0):
        self.batch_size = batch_size
        self.timeout = timeout
        self._pending: List[Tuple[str, str]] = []  # (response, focus)
        self._last_batch_time: float = 0.0
    
    def add(self, response: str, focus: str = "person") -> Optional[List[Tuple[bool, str]]]:
        """Add response to batch.
        
        Returns results when batch is full or timeout reached.
        
        Args:
            response: LLM response to validate
            focus: What we're tracking
            
        Returns:
            List of (is_significant, summary) if batch ready, else None
        """
        self._pending.append((response, focus))
        
        # Check if batch ready
        batch_ready = (
            len(self._pending) >= self.batch_size or
            (time.time() - self._last_batch_time > self.timeout and self._pending)
        )
        
        if batch_ready:
            return self._process_batch()
        
        return None
    
    def flush(self) -> List[Tuple[bool, str]]:
        """Process any remaining items."""
        if self._pending:
            return self._process_batch()
        return []
    
    def _process_batch(self) -> List[Tuple[bool, str]]:
        """Process current batch."""
        import requests
        from .config import config
        
        if not self._pending:
            return []
        
        batch = self._pending.copy()
        self._pending.clear()
        self._last_batch_time = time.time()
        
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
        
        # Build batch prompt
        items = "\n".join([
            f"{i+1}. {resp[:100]}..." 
            for i, (resp, _) in enumerate(batch)
        ])
        
        prompt = f"""Summarize each camera detection in ONE short sentence (max 10 words each).

DETECTIONS:
{items}

For each, respond with format: "[number]. [summary]"
If no person: "[number]. No person visible"

Example response:
1. Person: at desk, using computer
2. No person visible
3. Person: walking left

Respond with numbered summaries only:"""

        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": guarder_model, "prompt": prompt, "stream": False},
                timeout=20,
            )
            
            if resp.ok:
                result_text = resp.json().get("response", "")
                return self._parse_batch_response(result_text, batch)
            
        except Exception as e:
            logger.debug(f"Batch guarder failed: {e}")
        
        # Fallback: return all as significant
        return [(True, resp[:80]) for resp, _ in batch]
    
    def _parse_batch_response(
        self, 
        response: str, 
        batch: List[Tuple[str, str]]
    ) -> List[Tuple[bool, str]]:
        """Parse batch response into individual results."""
        results = []
        lines = response.strip().split('\n')
        
        for i, (orig_resp, focus) in enumerate(batch):
            # Find matching line
            summary = orig_resp[:80]  # Default
            is_significant = True
            
            for line in lines:
                if line.strip().startswith(f"{i+1}."):
                    summary = line.split(".", 1)[1].strip() if "." in line else line
                    summary = summary[:80]
                    
                    # Check if noise
                    summary_lower = summary.lower()
                    is_significant = not any(p in summary_lower for p in [
                        "no person", "no " + focus.lower(), "nothing", 
                        "not visible", "empty"
                    ])
                    break
            
            results.append((is_significant, summary))
        
        return results


# Convenience functions
_optimizer: Optional[FrameOptimizer] = None


def get_optimizer(config: OptimizerConfig = None) -> FrameOptimizer:
    """Get or create frame optimizer."""
    global _optimizer
    if _optimizer is None or config is not None:
        _optimizer = FrameOptimizer(config)
    return _optimizer
