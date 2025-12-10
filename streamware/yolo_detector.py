"""
YOLO Detector for Streamware

Fast object detection using YOLOv8 (ultralytics).
Automatically installs dependencies on first use.

Features:
- Auto-installation of ultralytics library
- Model download on first use (yolov8n.pt ~6MB)
- GPU acceleration (CUDA) when available
- Integration with ObjectTracker

Usage:
    from streamware.yolo_detector import YOLODetector, ensure_yolo_available
    
    # Check/install YOLO
    if ensure_yolo_available():
        detector = YOLODetector()
        detections = detector.detect(frame_path)
        
        for det in detections:
            print(f"{det['class']}: {det['confidence']:.2f} at ({det['x']}, {det['y']})")
"""

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# YOLO class names for COCO dataset
COCO_CLASSES = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
    5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
    10: 'fire hydrant', 11: 'stop sign', 12: 'parking meter', 13: 'bench',
    14: 'bird', 15: 'cat', 16: 'dog', 17: 'horse', 18: 'sheep', 19: 'cow',
    20: 'elephant', 21: 'bear', 22: 'zebra', 23: 'giraffe', 24: 'backpack',
    25: 'umbrella', 26: 'handbag', 27: 'tie', 28: 'suitcase', 29: 'frisbee',
    30: 'skis', 31: 'snowboard', 32: 'sports ball', 33: 'kite', 34: 'baseball bat',
    35: 'baseball glove', 36: 'skateboard', 37: 'surfboard', 38: 'tennis racket',
    39: 'bottle', 40: 'wine glass', 41: 'cup', 42: 'fork', 43: 'knife',
    44: 'spoon', 45: 'bowl', 46: 'banana', 47: 'apple', 48: 'sandwich',
    49: 'orange', 50: 'broccoli', 51: 'carrot', 52: 'hot dog', 53: 'pizza',
    54: 'donut', 55: 'cake', 56: 'chair', 57: 'couch', 58: 'potted plant',
    59: 'bed', 60: 'dining table', 61: 'toilet', 62: 'tv', 63: 'laptop',
    64: 'mouse', 65: 'remote', 66: 'keyboard', 67: 'cell phone', 68: 'microwave',
    69: 'oven', 70: 'toaster', 71: 'sink', 72: 'refrigerator', 73: 'book',
    74: 'clock', 75: 'vase', 76: 'scissors', 77: 'teddy bear', 78: 'hair drier',
    79: 'toothbrush'
}

# Classes we're typically interested in for security/monitoring
TRACKING_CLASSES = {
    'person': 0,
    'bicycle': 1,
    'car': 2,
    'motorcycle': 3,
    'bus': 5,
    'truck': 7,
    'dog': 16,
    'cat': 15,
}


def check_yolo_available() -> bool:
    """Check if ultralytics (YOLO) is installed."""
    try:
        import ultralytics
        return True
    except ImportError:
        return False


def install_yolo(verbose: bool = True) -> bool:
    """Install ultralytics (YOLO) library.
    
    Returns:
        True if installation successful
    """
    if check_yolo_available():
        return True
    
    if verbose:
        print("📦 Installing YOLO (ultralytics)... This may take a minute.")
    
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "ultralytics", "-q"],
            stdout=subprocess.DEVNULL if not verbose else None,
            stderr=subprocess.DEVNULL if not verbose else None,
        )
        
        if verbose:
            print("✅ YOLO installed successfully")
        
        return True
        
    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"❌ Failed to install YOLO: {e}")
        return False
    except Exception as e:
        if verbose:
            print(f"❌ Error installing YOLO: {e}")
        return False


def ensure_yolo_available(verbose: bool = True) -> bool:
    """Ensure YOLO is available, install if needed.
    
    Returns:
        True if YOLO is ready to use
    """
    if check_yolo_available():
        return True
    
    return install_yolo(verbose)


@dataclass
class Detection:
    """Single detection result."""
    class_id: int
    class_name: str
    confidence: float
    x: float  # Center X (normalized 0-1)
    y: float  # Center Y (normalized 0-1)
    w: float  # Width (normalized 0-1)
    h: float  # Height (normalized 0-1)
    
    # Pixel coordinates (for reference)
    x_px: int = 0
    y_px: int = 0
    w_px: int = 0
    h_px: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dict for tracker."""
        return {
            "x": self.x,
            "y": self.y,
            "w": self.w,
            "h": self.h,
            "confidence": self.confidence,
            "type": self.class_name,
            "class_id": self.class_id,
        }


class YOLODetector:
    """
    Fast object detection using YOLOv8.
    
    Models (download size / speed):
    - yolov8n: 6MB, fastest (~10ms on GPU, ~100ms on CPU)
    - yolov8s: 22MB, fast (~20ms on GPU)
    - yolov8m: 52MB, balanced (~40ms on GPU)
    - yolov8l: 87MB, accurate (~60ms on GPU)
    - yolov8x: 131MB, most accurate (~100ms on GPU)
    """
    
    def __init__(
        self,
        model: str = "yolov8n",
        confidence_threshold: float = 0.25,
        iou_threshold: float = 0.45,
        classes: List[str] = None,
        device: str = "auto",
    ):
        """
        Initialize YOLO detector.
        
        Args:
            model: Model name (yolov8n, yolov8s, yolov8m, yolov8l, yolov8x)
            confidence_threshold: Minimum confidence for detection
            iou_threshold: IoU threshold for NMS
            classes: List of class names to detect (None = all)
            device: Device to use ('auto', 'cuda', 'cpu')
        """
        self.model_name = model
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        self.device = device
        
        # Filter classes
        if classes:
            self.class_filter = [TRACKING_CLASSES.get(c, -1) for c in classes if c in TRACKING_CLASSES]
        else:
            self.class_filter = None
        
        self._model = None
        self._initialized = False
    
    def _ensure_model(self):
        """Lazy load model on first use."""
        if self._initialized:
            return
        
        if not ensure_yolo_available():
            raise RuntimeError("YOLO (ultralytics) is not available and could not be installed")
        
        from ultralytics import YOLO
        
        # Determine device
        device = self.device
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        
        # Load model (downloads automatically if needed)
        model_path = f"{self.model_name}.pt"
        logger.info(f"Loading YOLO model: {model_path} on {device}")
        
        self._model = YOLO(model_path)
        self._model.to(device)
        
        self._initialized = True
        logger.info(f"YOLO model loaded successfully")
    
    def detect(
        self,
        image_path: Path,
        classes: List[str] = None,
    ) -> List[Detection]:
        """
        Detect objects in image.
        
        Args:
            image_path: Path to image file
            classes: Override class filter for this detection
            
        Returns:
            List of Detection objects
        """
        self._ensure_model()
        
        # Run inference
        results = self._model(
            str(image_path),
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            classes=self.class_filter,
            verbose=False,
        )
        
        detections = []
        
        for result in results:
            if result.boxes is None:
                continue
            
            # Get image dimensions
            img_h, img_w = result.orig_shape
            
            for box in result.boxes:
                # Get box data
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                
                # Filter by class if specified
                if classes:
                    class_ids = [TRACKING_CLASSES.get(c, -1) for c in classes]
                    if cls_id not in class_ids:
                        continue
                
                # Calculate normalized coordinates
                x1, y1, x2, y2 = xyxy
                cx = (x1 + x2) / 2 / img_w
                cy = (y1 + y2) / 2 / img_h
                w = (x2 - x1) / img_w
                h = (y2 - y1) / img_h
                
                detection = Detection(
                    class_id=cls_id,
                    class_name=COCO_CLASSES.get(cls_id, f"class_{cls_id}"),
                    confidence=conf,
                    x=cx,
                    y=cy,
                    w=w,
                    h=h,
                    x_px=int((x1 + x2) / 2),
                    y_px=int((y1 + y2) / 2),
                    w_px=int(x2 - x1),
                    h_px=int(y2 - y1),
                )
                
                detections.append(detection)
        
        return detections
    
    def detect_persons(self, image_path: Path) -> List[Detection]:
        """Detect only persons in image."""
        return self.detect(image_path, classes=["person"])
    
    def detect_vehicles(self, image_path: Path) -> List[Detection]:
        """Detect only vehicles in image."""
        return self.detect(image_path, classes=["car", "truck", "bus", "motorcycle", "bicycle"])
    
    def detect_animals(self, image_path: Path) -> List[Detection]:
        """Detect only animals in image."""
        return self.detect(image_path, classes=["dog", "cat", "bird", "horse", "cow", "sheep"])


class YOLOTracker:
    """
    Combined YOLO detection + object tracking.
    
    Uses YOLOv8's built-in tracking (BoT-SORT or ByteTrack).
    """
    
    def __init__(
        self,
        model: str = "yolov8n",
        tracker: str = "bytetrack",  # "bytetrack" or "botsort"
        confidence_threshold: float = 0.25,
        classes: List[str] = None,
        device: str = "auto",
    ):
        """
        Initialize YOLO tracker.
        
        Args:
            model: YOLO model name
            tracker: Tracker type ("bytetrack" or "botsort")
            confidence_threshold: Minimum confidence
            classes: Classes to track
            device: Device to use
        """
        self.model_name = model
        self.tracker_type = tracker
        self.confidence_threshold = confidence_threshold
        self.device = device
        
        if classes:
            self.class_filter = [TRACKING_CLASSES.get(c, -1) for c in classes if c in TRACKING_CLASSES]
        else:
            self.class_filter = None
        
        self._model = None
        self._initialized = False
        
        # Tracking state
        self._track_history: Dict[int, List[Tuple[float, float]]] = {}
    
    def _ensure_model(self):
        """Lazy load model."""
        if self._initialized:
            return
        
        if not ensure_yolo_available():
            raise RuntimeError("YOLO not available")
        
        from ultralytics import YOLO
        
        device = self.device
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"
        
        self._model = YOLO(f"{self.model_name}.pt")
        self._model.to(device)
        self._initialized = True
    
    def track(
        self,
        image_path: Path,
        persist: bool = True,
    ) -> List[Dict]:
        """
        Track objects in image.
        
        Args:
            image_path: Path to image
            persist: Keep track IDs across calls
            
        Returns:
            List of tracked objects with IDs
        """
        self._ensure_model()
        
        # Run tracking
        results = self._model.track(
            str(image_path),
            conf=self.confidence_threshold,
            classes=self.class_filter,
            tracker=f"{self.tracker_type}.yaml",
            persist=persist,
            verbose=False,
        )
        
        tracked_objects = []
        
        for result in results:
            if result.boxes is None or result.boxes.id is None:
                continue
            
            img_h, img_w = result.orig_shape
            
            for box in result.boxes:
                if box.id is None:
                    continue
                
                # Get data
                track_id = int(box.id[0].cpu().numpy())
                xyxy = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls_id = int(box.cls[0].cpu().numpy())
                
                # Normalized center
                x1, y1, x2, y2 = xyxy
                cx = (x1 + x2) / 2 / img_w
                cy = (y1 + y2) / 2 / img_h
                w = (x2 - x1) / img_w
                h = (y2 - y1) / img_h
                
                # Update track history
                if track_id not in self._track_history:
                    self._track_history[track_id] = []
                
                self._track_history[track_id].append((cx, cy))
                
                # Keep last 30 positions
                if len(self._track_history[track_id]) > 30:
                    self._track_history[track_id].pop(0)
                
                # Calculate direction from history
                direction = self._calculate_direction(track_id)
                
                tracked_objects.append({
                    "id": track_id,
                    "class_id": cls_id,
                    "class_name": COCO_CLASSES.get(cls_id, f"class_{cls_id}"),
                    "confidence": conf,
                    "x": cx,
                    "y": cy,
                    "w": w,
                    "h": h,
                    "direction": direction,
                    "history": self._track_history[track_id].copy(),
                })
        
        return tracked_objects
    
    def _calculate_direction(self, track_id: int) -> str:
        """Calculate movement direction from track history."""
        history = self._track_history.get(track_id, [])
        
        if len(history) < 3:
            return "unknown"
        
        # Use last 5 positions
        recent = history[-5:]
        
        dx = recent[-1][0] - recent[0][0]
        dy = recent[-1][1] - recent[0][1]
        
        # Threshold for movement (1% of frame)
        threshold = 0.01
        
        if abs(dx) < threshold and abs(dy) < threshold:
            return "stationary"
        
        # Determine primary direction
        if abs(dx) > abs(dy) * 1.5:
            # Horizontal dominant
            if dx > 0:
                return "moving_right" if recent[-1][0] < 0.85 else "exiting_right"
            else:
                return "moving_left" if recent[-1][0] > 0.15 else "exiting_left"
        elif abs(dy) > abs(dx) * 1.5:
            # Vertical dominant
            if dy > 0:
                return "approaching" if recent[-1][1] > 0.5 else "moving_down"
            else:
                return "leaving" if recent[-1][1] < 0.5 else "moving_up"
        else:
            # Diagonal
            return "moving"
    
    def reset(self):
        """Reset tracking state."""
        self._track_history.clear()
        if self._model:
            self._model.predictor = None


def get_detector(
    use_yolo: bool = True,
    model: str = "yolov8n",
    fallback_to_hog: bool = True,
) -> Optional['YOLODetector']:
    """
    Get best available detector.
    
    Args:
        use_yolo: Try to use YOLO
        model: YOLO model name
        fallback_to_hog: If YOLO not available, return None (use HOG)
        
    Returns:
        YOLODetector or None
    """
    if use_yolo:
        if ensure_yolo_available(verbose=False):
            return YOLODetector(model=model)
        elif not fallback_to_hog:
            raise RuntimeError("YOLO not available")
    
    return None  # Use HOG fallback


def get_tracker(
    use_yolo: bool = True,
    model: str = "yolov8n",
    tracker: str = "bytetrack",
) -> Optional['YOLOTracker']:
    """
    Get best available tracker.
    
    Args:
        use_yolo: Try to use YOLO
        model: YOLO model name
        tracker: Tracker type
        
    Returns:
        YOLOTracker or None
    """
    if use_yolo and ensure_yolo_available(verbose=False):
        return YOLOTracker(model=model, tracker=tracker)
    
    return None
