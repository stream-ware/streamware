"""
YOLO Detection Wrapper

Wrapper for Ultralytics YOLO model.
"""

import logging
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import Detection

logger = logging.getLogger(__name__)


# =============================================================================
# YOLO AVAILABILITY
# =============================================================================

_YOLO_AVAILABLE = None
_YOLO_MODEL = None


def is_yolo_available() -> bool:
    """Check if YOLO is available."""
    global _YOLO_AVAILABLE
    
    if _YOLO_AVAILABLE is None:
        try:
            from ultralytics import YOLO
            _YOLO_AVAILABLE = True
        except ImportError:
            _YOLO_AVAILABLE = False
    
    return _YOLO_AVAILABLE


def install_yolo() -> bool:
    """Install YOLO dependencies."""
    import subprocess
    import sys
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "ultralytics", "-q"
        ])
        
        global _YOLO_AVAILABLE
        _YOLO_AVAILABLE = True
        return True
    except Exception as e:
        logger.error(f"Failed to install YOLO: {e}")
        return False


# =============================================================================
# YOLO DETECTOR
# =============================================================================

class YOLODetector:
    """YOLO object detection wrapper."""
    
    # COCO class names
    COCO_CLASSES = {
        0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
        5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
        10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
        14: "bird", 15: "cat", 16: "dog", 17: "horse", 18: "sheep", 19: "cow",
        20: "elephant", 21: "bear", 22: "zebra", 23: "giraffe", 24: "backpack",
        25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase", 29: "frisbee",
        30: "skis", 31: "snowboard", 32: "sports ball", 33: "kite", 34: "baseball bat",
        35: "baseball glove", 36: "skateboard", 37: "surfboard", 38: "tennis racket",
        39: "bottle", 40: "wine glass", 41: "cup", 42: "fork", 43: "knife",
        44: "spoon", 45: "bowl", 46: "banana", 47: "apple", 48: "sandwich",
        49: "orange", 50: "broccoli", 51: "carrot", 52: "hot dog", 53: "pizza",
        54: "donut", 55: "cake", 56: "chair", 57: "couch", 58: "potted plant",
        59: "bed", 60: "dining table", 61: "toilet", 62: "tv", 63: "laptop",
        64: "mouse", 65: "remote", 66: "keyboard", 67: "cell phone", 68: "microwave",
        69: "oven", 70: "toaster", 71: "sink", 72: "refrigerator", 73: "book",
        74: "clock", 75: "vase", 76: "scissors", 77: "teddy bear", 78: "hair drier",
        79: "toothbrush"
    }
    
    def __init__(
        self,
        model_path: str = "yolo11n.pt",
        confidence: float = 0.5,
        device: str = "cpu",
    ):
        """
        Initialize YOLO detector.
        
        Args:
            model_path: Path to YOLO model or model name
            confidence: Detection confidence threshold
            device: Device to use (cpu, cuda, etc.)
        """
        self.model_path = model_path
        self.confidence = confidence
        self.device = device
        self._model = None
    
    @property
    def model(self):
        """Lazy load YOLO model."""
        if self._model is None:
            if not is_yolo_available():
                raise RuntimeError("YOLO not available. Install with: pip install ultralytics")
            
            from ultralytics import YOLO
            self._model = YOLO(self.model_path)
        
        return self._model
    
    def detect(
        self,
        image_path: str,
        classes: Optional[List[int]] = None,
    ) -> List[Detection]:
        """
        Detect objects in image.
        
        Args:
            image_path: Path to image file
            classes: Optional list of class IDs to detect (None = all)
        
        Returns:
            List of Detection objects
        """
        if not is_yolo_available():
            return []
        
        try:
            results = self.model(
                image_path,
                conf=self.confidence,
                classes=classes,
                verbose=False,
            )
            
            detections = []
            for result in results:
                if result.boxes is None:
                    continue
                
                for box in result.boxes:
                    # Get box coordinates (normalized)
                    xyxyn = box.xyxyn[0].tolist()
                    
                    # Get class and confidence
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.COCO_CLASSES.get(cls_id, f"class_{cls_id}")
                    
                    detections.append(Detection(
                        class_name=class_name,
                        confidence=conf,
                        box={
                            "x1": xyxyn[0],
                            "y1": xyxyn[1],
                            "x2": xyxyn[2],
                            "y2": xyxyn[3],
                        },
                        track_id=int(box.id[0]) if box.id is not None else None,
                    ))
            
            return detections
            
        except Exception as e:
            logger.debug(f"YOLO detection error: {e}")
            return []
    
    def detect_class(
        self,
        image_path: str,
        target_class: str,
    ) -> List[Detection]:
        """
        Detect specific class in image.
        
        Args:
            image_path: Path to image
            target_class: Class name to detect (e.g., "person", "car")
        
        Returns:
            List of Detection objects for target class
        """
        # Find class ID
        class_id = None
        for cid, name in self.COCO_CLASSES.items():
            if name.lower() == target_class.lower():
                class_id = cid
                break
        
        if class_id is None:
            # Try detecting all and filter
            all_detections = self.detect(image_path)
            return [d for d in all_detections if d.class_name.lower() == target_class.lower()]
        
        return self.detect(image_path, classes=[class_id])
    
    def count_class(self, image_path: str, target_class: str) -> int:
        """Count instances of a class in image."""
        detections = self.detect_class(image_path, target_class)
        return len(detections)
