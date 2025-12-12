"""
Detection Pipeline

Main smart detection pipeline that combines YOLO, motion, and LLM.
"""

import logging
import time
from pathlib import Path
from typing import Optional, List, Dict

from .models import DetectionLevel, MotionLevel, DetectionResult, Detection
from .yolo import YOLODetector, is_yolo_available
from .motion import MotionDetector

from ..config import config

logger = logging.getLogger(__name__)


class SmartDetector:
    """
    Intelligent detection pipeline optimized for tracking.
    
    Uses multiple detection methods in order of speed:
    1. YOLO (fast, accurate) - object detection
    2. Motion detection - frame differencing
    3. Small LLM - validate/summarize (optional)
    """
    
    def __init__(
        self,
        focus: str = "person",
        use_yolo: bool = True,
        use_motion: bool = True,
        confidence: float = 0.5,
        motion_threshold: float = 0.5,
        guarder_model: str = "gemma:2b",
    ):
        """
        Initialize smart detector.
        
        Args:
            focus: Target object class (person, car, etc.)
            use_yolo: Whether to use YOLO detection
            use_motion: Whether to use motion detection
            confidence: Detection confidence threshold
            motion_threshold: Motion percentage threshold
            guarder_model: Small LLM model for validation
        """
        self.focus = focus.lower()
        self.use_yolo = use_yolo and is_yolo_available()
        self.use_motion = use_motion
        self.confidence = confidence
        self.motion_threshold = motion_threshold
        self.guarder_model = guarder_model
        
        # Initialize detectors
        self._yolo = None
        self._motion = None
        
        # State
        self._prev_frame = None
        self._prev_detections: List[Detection] = []
    
    @property
    def yolo(self) -> Optional[YOLODetector]:
        """Lazy load YOLO detector."""
        if self._yolo is None and self.use_yolo:
            self._yolo = YOLODetector(confidence=self.confidence)
        return self._yolo
    
    @property
    def motion(self) -> MotionDetector:
        """Lazy load motion detector."""
        if self._motion is None:
            self._motion = MotionDetector()
        return self._motion
    
    def analyze(
        self,
        frame_path: str,
        prev_frame_path: Optional[str] = None,
        use_llm: bool = False,
    ) -> DetectionResult:
        """
        Analyze frame for target objects.
        
        Args:
            frame_path: Path to current frame
            prev_frame_path: Path to previous frame (optional)
            use_llm: Whether to use LLM for validation
        
        Returns:
            DetectionResult with analysis
        """
        start_time = time.time()
        result = DetectionResult()
        
        frame_path = Path(frame_path)
        if not frame_path.exists():
            result.skip_reason = "Frame not found"
            return result
        
        # 1. Motion detection (fastest)
        if self.use_motion:
            motion_start = time.time()
            motion_result = self.motion.detect(
                str(frame_path),
                str(prev_frame_path) if prev_frame_path else None,
            )
            result.opencv_ms = (time.time() - motion_start) * 1000
            
            result.motion_percent = motion_result.get("motion_percent", 0)
            result.motion_level = motion_result.get("motion_level", MotionLevel.NONE)
            result.motion_regions = motion_result.get("regions", [])
            
            # Early exit if no motion
            if not motion_result.get("has_motion", False):
                if motion_result.get("first_frame"):
                    result.skip_reason = "first_frame"
                else:
                    result.skip_reason = f"motion_gate_{result.motion_percent:.0f}%"
                result.detection_method = "motion"
                result.total_ms = (time.time() - start_time) * 1000
                return result
        
        # 2. YOLO detection
        if self.use_yolo and self.yolo:
            yolo_start = time.time()
            detections = self.yolo.detect_class(str(frame_path), self.focus)
            result.yolo_ms = (time.time() - yolo_start) * 1000
            
            result.detections = detections
            result.detection_count = len(detections)
            result.detection_method = "yolo"
            
            if detections:
                result.has_target = True
                result.confidence = max(d.confidence for d in detections)
                result.detection_level = self._get_detection_level(result.confidence)
                result.should_notify = True
                
                # Generate quick summary
                result.quick_summary = self._generate_summary(detections)
            else:
                result.skip_reason = "yolo_no_target"
        
        # 3. Determine if LLM processing needed
        result.should_process_llm = self._should_use_llm(result, use_llm)
        
        # 4. Optional: LLM validation
        if use_llm and result.should_process_llm:
            llm_start = time.time()
            llm_result = self._validate_with_llm(frame_path, result)
            result.small_llm_ms = (time.time() - llm_start) * 1000
            
            if llm_result:
                result.quick_summary = llm_result
                result.detection_level = DetectionLevel.CONFIRMED
        
        result.total_ms = (time.time() - start_time) * 1000
        
        # Store for next iteration
        self._prev_frame = str(frame_path)
        self._prev_detections = result.detections
        
        return result
    
    def _get_detection_level(self, confidence: float) -> DetectionLevel:
        """Convert confidence to detection level."""
        if confidence >= 0.8:
            return DetectionLevel.HIGH
        elif confidence >= 0.5:
            return DetectionLevel.MEDIUM
        elif confidence >= 0.3:
            return DetectionLevel.LOW
        else:
            return DetectionLevel.NONE
    
    def _generate_summary(self, detections: List[Detection]) -> str:
        """Generate quick summary from detections."""
        if not detections:
            return ""
        
        count = len(detections)
        focus = self.focus
        
        if count == 1:
            d = detections[0]
            pos = d.position
            return f"{focus.title()} detected on {pos}"
        else:
            positions = list(set(d.position for d in detections))
            pos_str = ", ".join(positions)
            return f"{count} {focus}s detected ({pos_str})"
    
    def _should_use_llm(self, result: DetectionResult, force: bool = False) -> bool:
        """Determine if LLM should be used."""
        if force:
            return True
        
        # Use LLM for uncertain detections
        if result.detection_level == DetectionLevel.LOW:
            return True
        
        # Use LLM if motion but no YOLO detection
        if result.motion_level.value >= MotionLevel.MEDIUM.value and not result.has_target:
            return True
        
        return False
    
    def _validate_with_llm(self, frame_path: Path, result: DetectionResult) -> Optional[str]:
        """Validate detection with small LLM."""
        try:
            import requests
            
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            
            prompt = f"""Look at this image and answer briefly:
Is there a {self.focus} visible? Answer YES or NO, then describe what you see in 10 words or less.
Example: YES - person walking left"""
            
            # This would need vision model - simplified for now
            return None
            
        except Exception as e:
            logger.debug(f"LLM validation failed: {e}")
            return None
    
    def reset(self):
        """Reset detector state."""
        self._prev_frame = None
        self._prev_detections = []
        if self._motion:
            self._motion.reset()


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_smart_detector(
    focus: str = "person",
    **kwargs
) -> SmartDetector:
    """
    Get configured smart detector.
    
    Args:
        focus: Target object class
        **kwargs: Additional arguments for SmartDetector
    
    Returns:
        Configured SmartDetector instance
    """
    return SmartDetector(focus=focus, **kwargs)
