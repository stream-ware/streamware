"""
YOLO Model Manager Module

Dynamic YOLO model manager - downloads and caches models as needed.
Supports different models for different detection tasks.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, List, Any

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    YOLO = None


class YOLOModelManager:
    """
    Dynamic YOLO model manager - downloads and caches models as needed.
    Supports different models for different detection tasks.
    """
    
    # Available models and their use cases
    MODELS = {
        # General object detection (includes book class 73)
        "yolov8n": {"url": "yolov8n.pt", "classes": "coco", "size": "nano", "speed": "fastest"},
        "yolov8s": {"url": "yolov8s.pt", "classes": "coco", "size": "small", "speed": "fast"},
        "yolov8m": {"url": "yolov8m.pt", "classes": "coco", "size": "medium", "speed": "balanced"},
        "yolov8l": {"url": "yolov8l.pt", "classes": "coco", "size": "large", "speed": "accurate"},
        
        # Segmentation models
        "yolov8n-seg": {"url": "yolov8n-seg.pt", "classes": "coco", "size": "nano", "task": "segment"},
        "yolov8s-seg": {"url": "yolov8s-seg.pt", "classes": "coco", "size": "small", "task": "segment"},
    }
    
    # COCO classes relevant for documents
    # 73: book, 84: book (some versions)
    DOCUMENT_CLASSES = [73]  # book class in COCO
    PAPER_LIKE_CLASSES = [73, 67, 63]  # book, cell phone (rectangular), laptop
    
    def __init__(self, model_dir: Path = None):
        self.model_dir = model_dir or Path.home() / ".streamware" / "models" / "yolo"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_models: Dict[str, Any] = {}
        self.current_model: Optional[Any] = None
        self.current_model_name: Optional[str] = None
    
    def get_model(self, model_name: str = "yolov8n") -> Optional[Any]:
        """Get or download a YOLO model."""
        if not HAS_YOLO:
            print("   ⚠️ YOLO nie zainstalowany. Zainstaluj: pip install ultralytics")
            return None
        
        if model_name in self.loaded_models:
            return self.loaded_models[model_name]
        
        model_info = self.MODELS.get(model_name)
        if not model_info:
            print(f"   ⚠️ Nieznany model: {model_name}")
            return None
        
        try:
            print(f"   📥 Ładowanie modelu YOLO: {model_name}...")
            # YOLO automatically downloads if not present
            model = YOLO(model_info["url"])
            self.loaded_models[model_name] = model
            self.current_model = model
            self.current_model_name = model_name
            print(f"   ✅ Model {model_name} załadowany")
            return model
        except Exception as e:
            print(f"   ❌ Błąd ładowania modelu {model_name}: {e}")
            return None
    
    def detect(self, frame: np.ndarray, model_name: str = "yolov8n", 
               conf_threshold: float = 0.3, classes: List[int] = None) -> Dict[str, Any]:
        """
        Run YOLO detection on frame.
        Returns detection results with bounding boxes and confidence.
        """
        result = {
            "detected": False,
            "confidence": 0.0,
            "bbox": None,
            "class_name": None,
            "all_detections": [],
        }
        
        model = self.get_model(model_name)
        if model is None:
            return result
        
        try:
            # Run inference
            results = model(frame, conf=conf_threshold, verbose=False)
            
            if len(results) > 0 and len(results[0].boxes) > 0:
                boxes = results[0].boxes
                
                # Filter by classes if specified
                target_classes = classes or self.DOCUMENT_CLASSES
                
                best_conf = 0
                best_box = None
                best_class = None
                
                for i, box in enumerate(boxes):
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    
                    # Check if this is a document-like class or any class if not filtering
                    if classes is None or cls_id in target_classes:
                        if conf > best_conf:
                            best_conf = conf
                            best_box = box.xyxy[0].cpu().numpy()  # x1, y1, x2, y2
                            best_class = cls_id
                    
                    # Store all detections
                    result["all_detections"].append({
                        "class_id": cls_id,
                        "class_name": results[0].names.get(cls_id, "unknown"),
                        "confidence": conf,
                        "bbox": box.xyxy[0].cpu().numpy().tolist(),
                    })
                
                if best_box is not None:
                    x1, y1, x2, y2 = best_box
                    result["detected"] = True
                    result["confidence"] = best_conf
                    result["bbox"] = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                    result["class_name"] = results[0].names.get(best_class, "unknown")
        
        except Exception as e:
            print(f"   ⚠️ YOLO detection error: {e}")
        
        return result
    
    def detect_documents(self, frame: np.ndarray, conf_threshold: float = 0.25) -> Dict[str, Any]:
        """Detect documents (books, papers) in frame."""
        return self.detect(frame, model_name="yolov8n", conf_threshold=conf_threshold, 
                          classes=self.DOCUMENT_CLASSES)
    
    def detect_any(self, frame: np.ndarray, conf_threshold: float = 0.3) -> Dict[str, Any]:
        """Detect any objects in frame (no class filter)."""
        return self.detect(frame, model_name="yolov8n", conf_threshold=conf_threshold, 
                          classes=None)


# Global YOLO manager instance
_yolo_manager: Optional[YOLOModelManager] = None

def get_yolo_manager() -> YOLOModelManager:
    """Get or create global YOLO manager."""
    global _yolo_manager
    if _yolo_manager is None:
        _yolo_manager = YOLOModelManager()
    return _yolo_manager
