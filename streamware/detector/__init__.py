"""
Detector Module - Smart detection pipeline.

Refactored from smart_detector.py into modular components:
- models.py: Enums and data classes
- yolo.py: YOLO detection wrapper
- motion.py: Motion detection
- pipeline.py: Main detection pipeline

Usage:
    from streamware.detector import SmartDetector, DetectionResult
    
    detector = SmartDetector(focus="person")
    result = detector.analyze(frame_path)
"""

from .models import (
    DetectionLevel,
    MotionLevel,
    DetectionResult,
)

from .yolo import (
    YOLODetector,
    is_yolo_available,
    install_yolo,
)

from .motion import (
    MotionDetector,
    detect_motion,
)

from .pipeline import (
    SmartDetector,
    get_smart_detector,
)

__all__ = [
    # Models
    "DetectionLevel",
    "MotionLevel", 
    "DetectionResult",
    # YOLO
    "YOLODetector",
    "is_yolo_available",
    "install_yolo",
    # Motion
    "MotionDetector",
    "detect_motion",
    # Pipeline
    "SmartDetector",
    "get_smart_detector",
]
