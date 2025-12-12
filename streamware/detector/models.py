"""
Detection Models

Enums and data classes for detection pipeline.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class DetectionLevel(Enum):
    """Detection confidence level."""
    NONE = 0        # No target detected
    LOW = 1         # Possible detection (needs verification)
    MEDIUM = 2      # Likely detection
    HIGH = 3        # Confident detection
    CONFIRMED = 4   # LLM confirmed


class MotionLevel(Enum):
    """Motion intensity level."""
    NONE = 0        # No motion
    MINIMAL = 1     # Very slight motion (<1%)
    LOW = 2         # Low motion (1-5%)
    MEDIUM = 3      # Medium motion (5-15%)
    HIGH = 4        # High motion (>15%)
    
    @classmethod
    def from_percent(cls, percent: float) -> "MotionLevel":
        """Get motion level from percentage."""
        if percent < 0.5:
            return cls.NONE
        elif percent < 1:
            return cls.MINIMAL
        elif percent < 5:
            return cls.LOW
        elif percent < 15:
            return cls.MEDIUM
        else:
            return cls.HIGH


@dataclass
class Detection:
    """Single object detection."""
    class_name: str
    confidence: float
    box: Dict[str, float]  # x1, y1, x2, y2 (normalized 0-1)
    track_id: Optional[int] = None
    
    @property
    def center(self) -> tuple:
        """Get center point."""
        x = (self.box.get("x1", 0) + self.box.get("x2", 0)) / 2
        y = (self.box.get("y1", 0) + self.box.get("y2", 0)) / 2
        return (x, y)
    
    @property
    def position(self) -> str:
        """Get human-readable position."""
        x, y = self.center
        h_pos = "left" if x < 0.33 else ("right" if x > 0.66 else "center")
        v_pos = "top" if y < 0.33 else ("bottom" if y > 0.66 else "middle")
        return f"{h_pos}"  # Simplified
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "class": self.class_name,
            "confidence": self.confidence,
            "box": self.box,
            "track_id": self.track_id,
            "position": self.position,
        }


@dataclass
class DetectionResult:
    """Result from smart detection pipeline."""
    # Core results
    has_target: bool = False
    detection_level: DetectionLevel = DetectionLevel.NONE
    motion_level: MotionLevel = MotionLevel.NONE
    
    # Processing decisions
    should_process_llm: bool = False
    should_notify: bool = False
    
    # Details
    quick_summary: str = ""
    motion_percent: float = 0.0
    confidence: float = 0.0
    
    # Detections
    detections: List[Detection] = field(default_factory=list)
    detection_count: int = 0
    motion_regions: List[Dict] = field(default_factory=list)
    
    # Timing (milliseconds)
    opencv_ms: float = 0.0
    yolo_ms: float = 0.0
    small_llm_ms: float = 0.0
    total_ms: float = 0.0
    
    # Debug
    skip_reason: str = ""
    detection_method: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "has_target": self.has_target,
            "detection_level": self.detection_level.name,
            "motion_level": self.motion_level.name,
            "should_process_llm": self.should_process_llm,
            "should_notify": self.should_notify,
            "quick_summary": self.quick_summary,
            "motion_percent": self.motion_percent,
            "confidence": self.confidence,
            "detection_count": self.detection_count,
            "detection_method": self.detection_method,
            "timing_ms": {
                "opencv": self.opencv_ms,
                "yolo": self.yolo_ms,
                "llm": self.small_llm_ms,
                "total": self.total_ms,
            },
        }


@dataclass
class FrameInfo:
    """Information about a video frame."""
    frame_num: int
    timestamp: float
    path: Optional[str] = None
    width: int = 0
    height: int = 0
    
    # Analysis results
    motion_percent: float = 0.0
    has_motion: bool = False
    
    def __str__(self) -> str:
        return f"Frame #{self.frame_num} @ {self.timestamp:.2f}s"
