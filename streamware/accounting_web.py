"""
Accounting Web Service - Live Screen Preview with Auto-Archiving

Usługa webowa pokazująca podgląd ekranu w przeglądarce.
Co sekundę robi zrzut ekranu, analizuje czy to dokument i automatycznie archiwizuje.

Usage:
    sq accounting-web --project faktury_2024 --port 8080
    # Otwórz http://localhost:8080 w przeglądarce
"""

import asyncio
import base64
import hashlib
import io
import json
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

# Disable PaddleOCR model source check
os.environ.setdefault('DISABLE_MODEL_SOURCE_CHECK', 'True')
# Suppress OpenCV warnings
os.environ.setdefault('OPENCV_LOG_LEVEL', 'ERROR')

try:
    from aiohttp import web
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    import cv2
    import numpy as np
    # Suppress OpenCV warnings about camera
    os.environ.setdefault('OPENCV_LOG_LEVEL', 'ERROR')
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from PIL import ImageGrab
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import av
    HAS_PYAV = True
except ImportError:
    HAS_PYAV = False

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

try:
    from doctr.models import detection_predictor, recognition_predictor
    from doctr.io import DocumentFile
    HAS_DOCTR = True
except ImportError:
    HAS_DOCTR = False

try:
    import layoutparser as lp
    HAS_LAYOUTPARSER = True
except ImportError:
    HAS_LAYOUTPARSER = False


class DocumentDetector:
    """
    Specialized document detector for receipts, invoices, and other documents.
    Uses multiple detection methods for best accuracy.
    """
    
    # Document type patterns (keywords that indicate document type)
    RECEIPT_KEYWORDS = [
        'paragon', 'fiskalny', 'nip', 'ptu', 'vat', 'suma', 'razem', 'gotówka',
        'karta', 'reszta', 'sprzedaż', 'kasjer', 'receipt', 'total', 'subtotal',
        'tax', 'change', 'cash', 'card', 'payment', 'qty', 'price'
    ]
    
    INVOICE_KEYWORDS = [
        'faktura', 'vat', 'nip', 'netto', 'brutto', 'nabywca', 'sprzedawca',
        'termin płatności', 'data wystawienia', 'invoice', 'buyer', 'seller',
        'due date', 'issue date', 'amount', 'quantity', 'unit price'
    ]
    
    def __init__(self):
        self.doctr_detector = None
        self.doctr_recognizer = None
        self.layout_model = None
        self._init_models()
    
    def _init_models(self):
        """Initialize detection models."""
        # DocTR for text detection
        if HAS_DOCTR:
            try:
                self.doctr_detector = detection_predictor(arch='db_resnet50', pretrained=True)
                print("   ✅ DocTR detector załadowany")
            except Exception as e:
                print(f"   ⚠️ DocTR detector error: {e}")
        
        # LayoutParser for document layout analysis
        if HAS_LAYOUTPARSER:
            try:
                # Use PubLayNet model for document layout detection
                self.layout_model = lp.Detectron2LayoutModel(
                    config_path='lp://PubLayNet/faster_rcnn_R_50_FPN_3x/config',
                    label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
                    extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.5]
                )
                print("   ✅ LayoutParser załadowany")
            except Exception as e:
                print(f"   ⚠️ LayoutParser error: {e}")
    
    def detect_document_regions(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect document regions in frame using multiple methods.
        Returns regions with text, tables, etc.
        """
        result = {
            "has_document": False,
            "regions": [],
            "text_density": 0.0,
            "document_type": None,
            "confidence": 0.0,
        }
        
        if frame is None:
            return result
        
        h, w = frame.shape[:2]
        
        # Method 1: Use DocTR for text region detection
        if self.doctr_detector is not None:
            try:
                # DocTR expects RGB
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                doc = self.doctr_detector([rgb_frame])
                
                if doc.pages and len(doc.pages) > 0:
                    page = doc.pages[0]
                    for block in page.blocks:
                        for line in block.lines:
                            # Get bounding box
                            bbox = line.geometry
                            x1, y1 = int(bbox[0][0] * w), int(bbox[0][1] * h)
                            x2, y2 = int(bbox[1][0] * w), int(bbox[1][1] * h)
                            
                            result["regions"].append({
                                "type": "text",
                                "bbox": (x1, y1, x2 - x1, y2 - y1),
                                "confidence": line.confidence if hasattr(line, 'confidence') else 0.8
                            })
                    
                    if result["regions"]:
                        result["has_document"] = True
                        result["text_density"] = len(result["regions"]) / (h * w / 10000)
                        result["confidence"] = 0.7
            except Exception as e:
                pass
        
        # Method 2: Use LayoutParser for layout detection
        if self.layout_model is not None and not result["has_document"]:
            try:
                layout = self.layout_model.detect(frame)
                
                for block in layout:
                    result["regions"].append({
                        "type": block.type,
                        "bbox": (int(block.block.x_1), int(block.block.y_1),
                                int(block.block.width), int(block.block.height)),
                        "confidence": block.score
                    })
                
                if result["regions"]:
                    result["has_document"] = True
                    result["confidence"] = max(b.score for b in layout) if layout else 0
            except Exception as e:
                pass
        
        # Method 3: Simple text detection using edge density
        if not result["has_document"]:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = np.sum(edges > 0) / (h * w)
            
            # High edge density suggests text-heavy document
            if edge_density > 0.03:
                result["has_document"] = True
                result["text_density"] = edge_density
                result["confidence"] = min(0.6, edge_density * 10)
        
        return result
    
    def classify_document_type(self, text: str) -> Tuple[str, float]:
        """
        Classify document type based on extracted text.
        Returns (document_type, confidence).
        """
        if not text:
            return ("unknown", 0.0)
        
        text_lower = text.lower()
        
        # Count keyword matches
        receipt_score = sum(1 for kw in self.RECEIPT_KEYWORDS if kw in text_lower)
        invoice_score = sum(1 for kw in self.INVOICE_KEYWORDS if kw in text_lower)
        
        # Normalize scores
        receipt_conf = min(1.0, receipt_score / 5)
        invoice_conf = min(1.0, invoice_score / 5)
        
        if receipt_conf > invoice_conf and receipt_conf > 0.3:
            return ("paragon", receipt_conf)
        elif invoice_conf > receipt_conf and invoice_conf > 0.3:
            return ("faktura", invoice_conf)
        elif receipt_conf > 0 or invoice_conf > 0:
            return ("dokument", max(receipt_conf, invoice_conf))
        
        return ("unknown", 0.0)
    
    def detect_receipt_features(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect receipt-specific features using multiple methods:
        1. Shape analysis (aspect ratio, white paper)
        2. Text line detection (horizontal lines pattern)
        3. Keyword detection in visible text areas
        """
        result = {
            "is_receipt": False,
            "confidence": 0.0,
            "aspect_ratio": 0.0,
            "features": [],
        }
        
        if frame is None:
            return result
        
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Adaptive threshold for better paper detection
        thresh_adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                                 cv2.THRESH_BINARY, 11, 2)
        
        # Method 2: Also try simple threshold
        _, thresh_simple = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        
        # Combine both thresholds
        thresh = cv2.bitwise_or(thresh_adaptive, thresh_simple)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_score = 0
        best_bbox = None
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < (h * w * 0.05):  # At least 5% of frame (lowered)
                continue
            
            x, y, cw, ch = cv2.boundingRect(contour)
            aspect = ch / cw if cw > 0 else 0
            area_ratio = area / (h * w)
            
            score = 0
            features = []
            
            # Feature 1: Tall narrow shape (thermal receipt)
            if aspect > 1.5:
                score += 0.4
                features.append("tall_narrow")
            elif aspect > 1.0:
                score += 0.2
                features.append("vertical")
            
            # Feature 2: Significant area coverage
            if area_ratio > 0.15:
                score += 0.2
                features.append("large_area")
            
            # Feature 3: Check for horizontal text lines in the region
            roi = gray[y:y+ch, x:x+cw]
            if roi.size > 0:
                # Detect horizontal edges (text lines)
                sobel_h = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
                h_lines = np.sum(np.abs(sobel_h) > 30) / roi.size
                if h_lines > 0.05:
                    score += 0.3
                    features.append("text_lines")
            
            # Feature 4: White/light background
            if roi.size > 0:
                mean_brightness = np.mean(roi)
                if mean_brightness > 150:
                    score += 0.1
                    features.append("bright_paper")
            
            if score > best_score:
                best_score = score
                best_bbox = (x, y, cw, ch)
                result["features"] = features
                result["aspect_ratio"] = aspect
        
        if best_score > 0.3:
            result["is_receipt"] = True
            result["confidence"] = min(1.0, best_score)
            result["bbox"] = best_bbox
        
        return result
    
    def detect_invoice_features(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect invoice-specific features:
        1. A4/Letter aspect ratio (~1.41)
        2. Structured layout (header, table, footer)
        3. Logo/stamp areas
        """
        result = {
            "is_invoice": False,
            "confidence": 0.0,
            "features": [],
        }
        
        if frame is None:
            return result
        
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Threshold for paper detection
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < (h * w * 0.1):
                continue
            
            x, y, cw, ch = cv2.boundingRect(contour)
            aspect = ch / cw if cw > 0 else 0
            
            score = 0
            features = []
            
            # Feature 1: A4 aspect ratio (1.41) or Letter (1.29)
            if 1.2 <= aspect <= 1.6:
                score += 0.4
                features.append("a4_format")
            elif 0.7 <= aspect <= 0.85:  # Landscape A4
                score += 0.3
                features.append("a4_landscape")
            
            # Feature 2: Large rectangular area
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                score += 0.2
                features.append("rectangular")
            
            # Feature 3: Check for structured content
            roi = gray[y:y+ch, x:x+cw]
            if roi.size > 0:
                edges = cv2.Canny(roi, 50, 150)
                edge_density = np.sum(edges > 0) / roi.size
                if 0.03 < edge_density < 0.2:
                    score += 0.2
                    features.append("structured_content")
            
            if score > 0.4:
                result["is_invoice"] = True
                result["confidence"] = min(1.0, score)
                result["bbox"] = (x, y, cw, ch)
                result["features"] = features
                break
        
        return result


# Global document detector instance
_document_detector: Optional[DocumentDetector] = None

def get_document_detector() -> DocumentDetector:
    """Get or create global document detector."""
    global _document_detector
    if _document_detector is None:
        _document_detector = DocumentDetector()
    return _document_detector


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


# HTML Template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>📄 Streamware Accounting - Live Scanner</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
        }
        h1 { font-size: 1.5rem; }
        .status {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        .status-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            font-size: 0.9rem;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4ade80;
            animation: pulse 2s infinite;
        }
        .status-dot.paused { background: #fbbf24; animation: none; }
        .status-dot.error { background: #f87171; animation: none; }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .main-grid {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 15px;
            height: calc(100vh - 100px);
        }
        @media (max-width: 1200px) {
            .main-grid { grid-template-columns: 1fr; height: auto; }
        }
        .docs-table-container {
            flex: 1;
            overflow: auto;
            background: rgba(0,0,0,0.3);
            border-radius: 8px;
        }
        .docs-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
        }
        .docs-table th {
            background: #334155;
            padding: 10px 8px;
            text-align: left;
            position: sticky;
            top: 0;
            cursor: pointer;
        }
        .docs-table th:hover { background: #475569; }
        .docs-table td {
            padding: 8px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .docs-table tr:hover { background: rgba(255,255,255,0.05); }
        .docs-table tr.pending { background: rgba(234,179,8,0.15); }
        .docs-table .thumb { width: 50px; height: 35px; object-fit: cover; border-radius: 4px; }
        .badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: 600; }
        .badge-invoice { background: #3b82f6; }
        .badge-receipt { background: #22c55e; }
        .badge-letter { background: #8b5cf6; }
        .badge-other { background: #6b7280; }
        .filter-bar {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        .filter-bar select {
            padding: 6px 10px;
            border-radius: 4px;
            background: rgba(0,0,0,0.3);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
            font-size: 0.8rem;
        }
        .stats-row {
            display: flex;
            gap: 10px;
            margin-bottom: 10px;
        }
        .stat-card {
            background: rgba(255,255,255,0.08);
            padding: 8px 15px;
            border-radius: 6px;
            text-align: center;
        }
        .stat-value { font-size: 1.3rem; font-weight: 700; color: #60a5fa; }
        .stat-label { font-size: 0.7rem; color: #888; }
        .panel {
            background: rgba(255,255,255,0.05);
            border-radius: 12px;
            padding: 20px;
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .panel-title { font-size: 1.1rem; font-weight: 600; }
        .preview-container {
            position: relative;
            background: #000;
            border-radius: 8px;
            overflow: hidden;
            aspect-ratio: 16/9;
        }
        #preview-img {
            width: 100%;
            height: 100%;
            object-fit: contain;
        }
        .preview-overlay {
            position: absolute;
            bottom: 10px;
            left: 10px;
            right: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .preview-info {
            background: rgba(0,0,0,0.7);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            flex-wrap: wrap;
        }
        button {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary {
            background: #3b82f6;
            color: white;
        }
        .btn-primary:hover { background: #2563eb; }
        .btn-success {
            background: #22c55e;
            color: white;
        }
        .btn-success:hover { background: #16a34a; }
        .btn-warning {
            background: #f59e0b;
            color: white;
        }
        .btn-warning:hover { background: #d97706; }
        .btn-danger {
            background: #ef4444;
            color: white;
        }
        .btn-danger:hover { background: #dc2626; }
        .documents-list {
            max-height: 500px;
            overflow-y: auto;
        }
        .document-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            margin-bottom: 10px;
            transition: background 0.2s;
        }
        .document-item:hover {
            background: rgba(255,255,255,0.1);
        }
        .document-item.new {
            animation: highlight 2s ease-out;
        }
        @keyframes highlight {
            0% { background: rgba(74, 222, 128, 0.3); }
            100% { background: rgba(255,255,255,0.05); }
        }
        .doc-icon {
            font-size: 2rem;
        }
        .doc-info { flex: 1; }
        .doc-type {
            font-weight: 600;
            margin-bottom: 4px;
        }
        .doc-meta {
            font-size: 0.8rem;
            color: #aaa;
        }
        .doc-amount {
            font-size: 1.1rem;
            font-weight: 600;
            color: #4ade80;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .summary-card {
            background: rgba(255,255,255,0.05);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .summary-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #60a5fa;
        }
        .summary-label {
            font-size: 0.85rem;
            color: #aaa;
            margin-top: 5px;
        }
        .log-panel {
            margin-top: 20px;
        }
        .log-content {
            background: #0d1117;
            border-radius: 8px;
            padding: 15px;
            font-family: 'Fira Code', monospace;
            font-size: 0.8rem;
            max-height: 200px;
            overflow-y: auto;
        }
        .log-entry {
            margin-bottom: 5px;
            opacity: 0.8;
        }
        .log-entry.info { color: #58a6ff; }
        .log-entry.success { color: #3fb950; }
        .log-entry.warning { color: #d29922; }
        .log-entry.error { color: #f85149; }
        .settings-row {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 10px;
        }
        .settings-row label {
            min-width: 120px;
        }
        input[type="range"] {
            flex: 1;
        }
        input[type="checkbox"] {
            width: 20px;
            height: 20px;
        }
        select {
            padding: 8px 12px;
            border-radius: 6px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            color: white;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📄 Streamware Accounting - Live Scanner</h1>
            <div class="status">
                <div class="status-item">
                    <div class="status-dot" id="status-dot"></div>
                    <span id="status-text">Skanowanie aktywne</span>
                </div>
                <div class="status-item">
                    <span>Projekt:</span>
                    <strong id="project-name">-</strong>
                </div>
            </div>
        </header>

        <div class="main-grid">
            <!-- Left Sidebar: Preview + Controls -->
            <div class="left-column" style="display:flex;flex-direction:column;gap:10px;">
                <div class="panel" style="padding:10px;">
                    <div class="preview-container" style="aspect-ratio:4/3;">
                        <img id="preview-img" src="" alt="Preview">
                        <div class="preview-overlay">
                            <div class="preview-info" id="detection-info">Oczekiwanie...</div>
                        </div>
                    </div>
                    <div class="controls" style="margin-top:8px;justify-content:center;">
                        <button class="btn-primary" onclick="toggleScanning()" style="padding:6px 12px;">
                            <span id="scan-btn-icon">⏸️</span>
                        </button>
                        <button class="btn-success" onclick="captureNow()" style="padding:6px 12px;">📷</button>
                        <button class="btn-warning" onclick="exportCSV()" style="padding:6px 12px;">📊</button>
                    </div>
                </div>
                
                <div class="panel" style="padding:10px;flex:1;overflow:hidden;display:flex;flex-direction:column;">
                    <div style="font-weight:600;margin-bottom:8px;">📋 Log</div>
                    <div class="log-content" id="log-content" style="flex:1;max-height:none;"></div>
                </div>
            </div>

            <!-- Main Content: Stats + Filters + Documents Table -->
            <div class="right-column" style="display:flex;flex-direction:column;gap:10px;overflow:hidden;">
                <!-- Stats Row -->
                <div class="stats-row">
                    <div class="stat-card"><div class="stat-value" id="total-docs">0</div><div class="stat-label">Dokumenty</div></div>
                    <div class="stat-card"><div class="stat-value" id="total-invoices">0</div><div class="stat-label">Faktury</div></div>
                    <div class="stat-card"><div class="stat-value" id="total-receipts">0</div><div class="stat-label">Paragony</div></div>
                    <div class="stat-card"><div class="stat-value" id="total-amount">0 zł</div><div class="stat-label">Suma</div></div>
                    <div class="stat-card"><div class="stat-value" id="pending-count-stat">0</div><div class="stat-label">Oczekuje</div></div>
                </div>
                
                <!-- Filters -->
                <div class="filter-bar">
                    <select id="filter-type" onchange="filterDocs()">
                        <option value="">Wszystkie typy</option>
                        <option value="invoice">Faktury</option>
                        <option value="receipt">Paragony</option>
                        <option value="letter">Pisma</option>
                        <option value="other">Inne</option>
                    </select>
                    <select id="filter-lang" onchange="filterDocs()">
                        <option value="">Wszystkie języki</option>
                        <option value="pl">Polski</option>
                        <option value="en">English</option>
                        <option value="de">Deutsch</option>
                    </select>
                    <select id="filter-status" onchange="filterDocs()">
                        <option value="">Wszystkie statusy</option>
                        <option value="pending">Oczekujące</option>
                        <option value="saved">Zapisane</option>
                    </select>
                    <input type="text" id="filter-search" placeholder="Szukaj..." onkeyup="filterDocs()" style="flex:1;min-width:150px;">
                </div>
                
                <!-- Documents Table -->
                <div class="docs-table-container">
                    <table class="docs-table">
                        <thead>
                            <tr>
                                <th style="width:60px;">Foto</th>
                                <th onclick="sortDocs('type')">Typ ▼</th>
                                <th onclick="sortDocs('date')">Data ▼</th>
                                <th onclick="sortDocs('amount')">Kwota ▼</th>
                                <th>NIP/ID</th>
                                <th>Język</th>
                                <th>OCR</th>
                                <th style="width:80px;">Akcje</th>
                            </tr>
                        </thead>
                        <tbody id="docs-table-body">
                            <tr><td colspan="8" style="text-align:center;color:#888;padding:40px;">Brak dokumentów</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Documents data store
        let allDocs = [];
        let sortField = 'date';
        let sortDir = -1;
        let ws;
        let scanning = true;
        let frameCount = 0;
        let lastFpsUpdate = Date.now();

        function connect() {
            const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${location.host}/ws`);

            ws.onopen = () => {
                log('Połączono z serwerem', 'success');
                updateStatus('active');
            };

            ws.onclose = () => {
                log('Rozłączono - ponawiam za 2s...', 'warning');
                updateStatus('error');
                setTimeout(connect, 2000);
            };

            ws.onerror = (e) => {
                log('Błąd WebSocket', 'error');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
        }

        function handleMessage(data) {
            switch(data.type) {
                case 'frame':
                    updatePreview(data);
                    break;
                case 'document':
                    addDocument(data.document);
                    log(`Zarchiwizowano: ${data.document.type} - ${data.document.id}`, 'success');
                    break;
                case 'summary':
                    updateSummary(data.summary);
                    break;
                case 'config':
                    document.getElementById('project-name').textContent = data.project;
                    break;
                case 'log':
                    log(data.message, data.level || 'info');
                    break;
                case 'pending_documents':
                    // Add pending documents to the list
                    data.documents.forEach(doc => addPendingDocument(doc));
                    break;
                case 'pending_document':
                    // Single pending document added
                    addPendingDocument(data.document);
                    break;
                case 'documents_list':
                    showDocumentsList(data.documents);
                    break;
                case 'document_detail':
                    showDocumentDetail(data.document);
                    break;
            }
        }
        
        function showPendingDocuments(docs) {
            const modal = document.getElementById('pending-modal');
            const list = document.getElementById('pending-list');
            list.innerHTML = '';
            
            if (docs.length === 0) {
                list.innerHTML = '<p style="color:#888;text-align:center;">Brak dokumentów do potwierdzenia</p>';
            } else {
                docs.forEach((doc, i) => {
                    const item = document.createElement('div');
                    item.className = 'pending-item';
                    item.innerHTML = `
                        <img src="data:image/jpeg;base64,${doc.image}" style="max-width:150px;max-height:100px;border-radius:4px;">
                        <div style="flex:1;padding:0 10px;">
                            <div style="font-weight:bold;">${doc.doc_type}</div>
                            <div style="color:#888;font-size:12px;">Pewność: ${Math.round(doc.confidence*100)}%</div>
                        </div>
                        <div>
                            <button onclick="confirmDoc(${doc.id})" style="background:#22c55e;color:white;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;margin-right:5px;">✓</button>
                            <button onclick="rejectDoc(${doc.id})" style="background:#ef4444;color:white;border:none;padding:8px 16px;border-radius:4px;cursor:pointer;">✗</button>
                        </div>
                    `;
                    list.appendChild(item);
                });
            }
            modal.style.display = 'flex';
        }
        
        function confirmDoc(id) {
            ws.send(JSON.stringify({action: 'confirm_document', id: id}));
            ws.send(JSON.stringify({action: 'get_pending'}));
        }
        
        function rejectDoc(id) {
            ws.send(JSON.stringify({action: 'reject_document', id: id}));
            ws.send(JSON.stringify({action: 'get_pending'}));
        }
        
        function confirmAllDocs() {
            ws.send(JSON.stringify({action: 'confirm_all'}));
            closePendingModal();
        }
        
        function rejectAllDocs() {
            ws.send(JSON.stringify({action: 'reject_all'}));
            closePendingModal();
        }
        
        function showPendingModal() {
            ws.send(JSON.stringify({action: 'get_pending'}));
        }
        
        function closePendingModal() {
            document.getElementById('pending-modal').style.display = 'none';
        }
        
        function showDocumentsList(docs) {
            const modal = document.getElementById('docs-modal');
            const table = document.getElementById('docs-table-body');
            table.innerHTML = '';
            
            docs.forEach(doc => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${doc.id || '-'}</td>
                    <td>${doc.type || '-'}</td>
                    <td>${doc.date || '-'}</td>
                    <td>${doc.amount ? doc.amount + ' zł' : '-'}</td>
                    <td>${doc.nip || '-'}</td>
                    <td><button onclick="showDocDetail('${doc.id}')" style="background:#3b82f6;color:white;border:none;padding:4px 8px;border-radius:4px;cursor:pointer;">Szczegóły</button></td>
                `;
                table.appendChild(row);
            });
            modal.style.display = 'flex';
        }
        
        function showDocDetail(docId) {
            ws.send(JSON.stringify({action: 'get_ocr_data', doc_id: docId}));
        }
        
        function showDocumentDetail(doc) {
            alert('Szczegóły dokumentu:\\n' + JSON.stringify(doc, null, 2));
        }
        
        function showDocsModal() {
            ws.send(JSON.stringify({action: 'get_documents'}));
        }
        
        function closeDocsModal() {
            document.getElementById('docs-modal').style.display = 'none';
        }

        function updatePreview(data) {
            const img = document.getElementById('preview-img');
            img.src = 'data:image/jpeg;base64,' + data.image;

            frameCount++;
            const now = Date.now();
            if (now - lastFpsUpdate > 1000) {
                document.getElementById('fps-counter').textContent = frameCount + ' FPS';
                frameCount = 0;
                lastFpsUpdate = now;
            }

            const info = document.getElementById('detection-info');
            if (data.document_in_view) {
                const conf = Math.round((data.confidence || 0) * 100);
                const docType = data.doc_type || 'dokument';
                const method = data.method || '';
                info.textContent = `🔍 ${docType} (${conf}%) [${method}]`;
                info.style.background = conf >= 85 ? 'rgba(34, 197, 94, 0.9)' : 
                                        conf >= 60 ? 'rgba(234, 179, 8, 0.9)' : 
                                        'rgba(59, 130, 246, 0.8)';
            } else {
                info.textContent = 'Oczekiwanie na dokument...';
                info.style.background = 'rgba(0,0,0,0.7)';
            }
            
            // Update pending count badge
            const pendingBadge = document.getElementById('pending-badge');
            if (pendingBadge) {
                const count = data.pending_count || 0;
                pendingBadge.textContent = count;
                pendingBadge.style.display = count > 0 ? 'inline-block' : 'none';
            }
        }

        function updateSummary(summary) {
            document.getElementById('total-docs').textContent = summary.total_documents || 0;
            document.getElementById('total-invoices').textContent = summary.by_type?.invoice || 0;
            document.getElementById('total-receipts').textContent = summary.by_type?.receipt || 0;
            const total = (summary.total_amounts?.invoices || 0) + (summary.total_amounts?.receipts || 0);
            document.getElementById('total-amount').textContent = Math.round(total) + ' zł';
        }

        function addDocument(doc) {
            // Add to data store
            const existingIdx = allDocs.findIndex(d => d.id === doc.id);
            if (existingIdx >= 0) {
                allDocs[existingIdx] = {...allDocs[existingIdx], ...doc};
            } else {
                allDocs.unshift(doc);
            }
            renderDocsTable();
            updateStats();
        }
        
        function addPendingDocument(doc) {
            addDocument({
                ...doc,
                pending: true,
                type: doc.doc_type || doc.type || 'dokument',
                date: new Date().toLocaleTimeString('pl-PL', {hour:'2-digit', minute:'2-digit'}),
            });
        }
        
        function renderDocsTable() {
            const tbody = document.getElementById('docs-table-body');
            const filtered = getFilteredDocs();
            
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:#888;padding:40px;">Brak dokumentów</td></tr>';
                return;
            }
            
            // Sort
            filtered.sort((a, b) => {
                let va = a[sortField] || '';
                let vb = b[sortField] || '';
                if (sortField === 'amount') {
                    va = parseFloat(va) || 0;
                    vb = parseFloat(vb) || 0;
                }
                return va > vb ? sortDir : va < vb ? -sortDir : 0;
            });
            
            tbody.innerHTML = filtered.map(doc => {
                const isPending = doc.pending === true;
                const typeClass = doc.type === 'invoice' ? 'badge-invoice' : doc.type === 'receipt' ? 'badge-receipt' : doc.type === 'letter' ? 'badge-letter' : 'badge-other';
                const typeName = doc.type === 'invoice' ? 'Faktura' : doc.type === 'receipt' ? 'Paragon' : doc.type === 'paragon' ? 'Paragon' : doc.type === 'faktura' ? 'Faktura' : doc.type || 'Dokument';
                const lang = doc.lang || detectLang(doc.ocr_text);
                const ocrPreview = doc.ocr_text ? doc.ocr_text.substring(0, 50) + '...' : '-';
                
                return `<tr class="${isPending ? 'pending' : ''}" data-id="${doc.id}">
                    <td>${doc.thumbnail ? `<img src="data:image/jpeg;base64,${doc.thumbnail}" class="thumb">` : '📄'}</td>
                    <td><span class="badge ${typeClass}">${typeName}</span>${isPending ? ' ⏳' : ''}</td>
                    <td>${doc.date || '-'}</td>
                    <td>${doc.amount ? doc.amount + ' zł' : '-'}</td>
                    <td>${doc.nip || doc.id || '-'}</td>
                    <td>${lang ? `<span class="badge badge-${lang}">${lang.toUpperCase()}</span>` : '-'}</td>
                    <td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${doc.ocr_text || ''}">${ocrPreview}</td>
                    <td>
                        ${isPending ? `<button onclick="confirmDoc(${doc.id})" style="background:#22c55e;color:white;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;margin-right:4px;">✓</button>` : ''}
                        <button onclick="removeDoc(${doc.id}, ${isPending})" style="background:#ef4444;color:white;border:none;padding:3px 8px;border-radius:4px;cursor:pointer;">✗</button>
                    </td>
                </tr>`;
            }).join('');
        }
        
        function getFilteredDocs() {
            const typeFilter = document.getElementById('filter-type').value;
            const langFilter = document.getElementById('filter-lang').value;
            const statusFilter = document.getElementById('filter-status').value;
            const search = document.getElementById('filter-search').value.toLowerCase();
            
            return allDocs.filter(doc => {
                if (typeFilter && doc.type !== typeFilter && doc.type !== (typeFilter === 'receipt' ? 'paragon' : typeFilter === 'invoice' ? 'faktura' : typeFilter)) return false;
                if (langFilter && (doc.lang || detectLang(doc.ocr_text)) !== langFilter) return false;
                if (statusFilter === 'pending' && !doc.pending) return false;
                if (statusFilter === 'saved' && doc.pending) return false;
                if (search && !JSON.stringify(doc).toLowerCase().includes(search)) return false;
                return true;
            });
        }
        
        function detectLang(text) {
            if (!text) return null;
            const t = text.toLowerCase();
            if (t.includes('faktura') || t.includes('paragon') || t.includes('nip') || t.includes('zł')) return 'pl';
            if (t.includes('invoice') || t.includes('receipt') || t.includes('total')) return 'en';
            if (t.includes('rechnung') || t.includes('quittung') || t.includes('€')) return 'de';
            return null;
        }
        
        function sortDocs(field) {
            if (sortField === field) sortDir *= -1;
            else { sortField = field; sortDir = -1; }
            renderDocsTable();
        }
        
        function filterDocs() {
            renderDocsTable();
        }
        
        function confirmDoc(docId) {
            ws.send(JSON.stringify({action: 'confirm_document', id: docId}));
            const doc = allDocs.find(d => d.id === docId);
            if (doc) { doc.pending = false; }
            renderDocsTable();
            updateStats();
            log('✅ Zapisano dokument', 'success');
        }
        
        function removeDoc(docId, isPending) {
            if (isPending) {
                ws.send(JSON.stringify({action: 'reject_document', id: docId}));
            }
            allDocs = allDocs.filter(d => d.id !== docId);
            renderDocsTable();
            updateStats();
        }
        
        function updateStats() {
            const pending = allDocs.filter(d => d.pending).length;
            const saved = allDocs.filter(d => !d.pending).length;
            const invoices = allDocs.filter(d => d.type === 'invoice' || d.type === 'faktura').length;
            const receipts = allDocs.filter(d => d.type === 'receipt' || d.type === 'paragon').length;
            const totalAmount = allDocs.reduce((sum, d) => sum + (parseFloat(d.amount) || 0), 0);
            
            document.getElementById('total-docs').textContent = allDocs.length;
            document.getElementById('total-invoices').textContent = invoices;
            document.getElementById('total-receipts').textContent = receipts;
            document.getElementById('total-amount').textContent = totalAmount.toFixed(0) + ' zł';
            document.getElementById('pending-count-stat').textContent = pending;
        }

        function updateStatus(status) {
            const dot = document.getElementById('status-dot');
            const text = document.getElementById('status-text');

            dot.className = 'status-dot';
            if (status === 'active') {
                text.textContent = 'Skanowanie aktywne';
            } else if (status === 'paused') {
                dot.classList.add('paused');
                text.textContent = 'Wstrzymane';
            } else if (status === 'error') {
                dot.classList.add('error');
                text.textContent = 'Błąd połączenia';
            }
        }

        function toggleScanning() {
            scanning = !scanning;
            ws.send(JSON.stringify({ action: 'toggle', scanning: scanning }));

            const icon = document.getElementById('scan-btn-icon');
            const text = document.getElementById('scan-btn-text');

            if (scanning) {
                icon.textContent = '⏸️';
                text.textContent = 'Pauza';
                updateStatus('active');
            } else {
                icon.textContent = '▶️';
                text.textContent = 'Wznów';
                updateStatus('paused');
            }
        }

        function captureNow() {
            ws.send(JSON.stringify({ action: 'capture' }));
            log('Wymuszono skan...', 'info');
        }

        function exportCSV() {
            window.open('/export/csv', '_blank');
            log('Eksportowanie CSV...', 'info');
        }

        function log(message, level = 'info') {
            const content = document.getElementById('log-content');
            const time = new Date().toLocaleTimeString();
            const entry = document.createElement('div');
            entry.className = `log-entry ${level}`;
            entry.textContent = `[${time}] ${message}`;
            content.appendChild(entry);
            content.scrollTop = content.scrollHeight;
        }

        function clearLog() {
            document.getElementById('log-content').innerHTML = '';
        }

        // Settings handlers (only if elements exist)
        const intervalSlider = document.getElementById('interval-slider');
        if (intervalSlider) {
            intervalSlider.addEventListener('input', (e) => {
                const val = e.target.value;
                document.getElementById('interval-value').textContent = val + 's';
                ws.send(JSON.stringify({ action: 'set_interval', interval: parseFloat(val) }));
            });
        }

        const confSlider = document.getElementById('confidence-slider');
        if (confSlider) {
            confSlider.addEventListener('input', (e) => {
                const val = e.target.value;
                document.getElementById('confidence-value').textContent = Math.round(val * 100) + '%';
                ws.send(JSON.stringify({ action: 'set_confidence', confidence: parseFloat(val) }));
            });
        }

        const autoArchive = document.getElementById('auto-archive');
        if (autoArchive) {
            autoArchive.addEventListener('change', (e) => {
                ws.send(JSON.stringify({ action: 'set_auto_archive', enabled: e.target.checked }));
            });
        }

        // Start
        connect();
    </script>
    
    <!-- Modal: Pending Documents -->
    <div id="pending-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;align-items:center;justify-content:center;">
        <div style="background:#1e293b;border-radius:12px;padding:20px;max-width:800px;width:90%;max-height:80vh;overflow-y:auto;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                <h2 style="margin:0;">📋 Dokumenty do potwierdzenia</h2>
                <button onclick="closePendingModal()" style="background:none;border:none;color:white;font-size:24px;cursor:pointer;">×</button>
            </div>
            <div id="pending-list" style="display:flex;flex-direction:column;gap:10px;"></div>
            <div style="display:flex;gap:10px;margin-top:15px;justify-content:flex-end;">
                <button onclick="confirmAllDocs()" style="background:#22c55e;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;">✓ Potwierdź wszystkie</button>
                <button onclick="rejectAllDocs()" style="background:#ef4444;color:white;border:none;padding:10px 20px;border-radius:6px;cursor:pointer;">✗ Odrzuć wszystkie</button>
            </div>
        </div>
    </div>
    
    <!-- Modal: Documents List with OCR Data -->
    <div id="docs-modal" style="display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;align-items:center;justify-content:center;">
        <div style="background:#1e293b;border-radius:12px;padding:20px;max-width:1000px;width:95%;max-height:85vh;overflow-y:auto;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px;">
                <h2 style="margin:0;">📄 Zarchiwizowane dokumenty</h2>
                <button onclick="closeDocsModal()" style="background:none;border:none;color:white;font-size:24px;cursor:pointer;">×</button>
            </div>
            <table style="width:100%;border-collapse:collapse;">
                <thead>
                    <tr style="background:#334155;">
                        <th style="padding:10px;text-align:left;border-bottom:1px solid #475569;">ID</th>
                        <th style="padding:10px;text-align:left;border-bottom:1px solid #475569;">Typ</th>
                        <th style="padding:10px;text-align:left;border-bottom:1px solid #475569;">Data</th>
                        <th style="padding:10px;text-align:left;border-bottom:1px solid #475569;">Kwota</th>
                        <th style="padding:10px;text-align:left;border-bottom:1px solid #475569;">NIP</th>
                        <th style="padding:10px;text-align:left;border-bottom:1px solid #475569;">Akcje</th>
                    </tr>
                </thead>
                <tbody id="docs-table-body"></tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""


def load_env_config() -> Dict[str, Any]:
    """Load all configuration from .env file."""
    config = {
        # Camera settings
        "default_url": None,
        "rtsp_user": None,
        "rtsp_password": None,
        "default_camera": 0,
        "cameras": {},
        "cameras_list": [],
        # Scanner settings
        "scanner_fps": 2,
        "scanner_min_confidence": 0.25,
        "scanner_confirm_threshold": 0.60,
        "scanner_auto_save_threshold": 0.85,
        "scanner_cooldown_sec": 2,
        "scanner_use_llm_confirm": True,
        "scanner_jpeg_quality": 90,
    }
    
    env_vars = {}
    
    # Try to load from .env files
    env_files = [
        Path.cwd() / ".env",
        Path.home() / ".streamware" / ".env",
    ]
    
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            env_vars[key] = value
            except Exception:
                pass
    
    # Override with environment variables
    scanner_keys = [
        "SQ_DEFAULT_URL", "SQ_RTSP_USER", "SQ_RTSP_PASS", "SQ_CAMERAS", "SQ_DEFAULT_CAMERA",
        "SQ_SCANNER_FPS", "SQ_SCANNER_MIN_CONFIDENCE", "SQ_SCANNER_CONFIRM_THRESHOLD",
        "SQ_SCANNER_AUTO_SAVE_THRESHOLD", "SQ_SCANNER_COOLDOWN_SEC", "SQ_SCANNER_USE_LLM_CONFIRM",
        "SQ_SCANNER_JPEG_QUALITY"
    ]
    for key in scanner_keys:
        if key in os.environ:
            env_vars[key] = os.environ[key]
    
    # Parse camera config
    config["default_url"] = env_vars.get("SQ_DEFAULT_URL")
    config["rtsp_user"] = env_vars.get("SQ_RTSP_USER")
    config["rtsp_password"] = env_vars.get("SQ_RTSP_PASS")
    
    # Parse cameras list
    cameras_str = env_vars.get("SQ_CAMERAS", "")
    if cameras_str:
        for item in cameras_str.split(","):
            item = item.strip()
            if "|" in item:
                name, url = item.split("|", 1)
                config["cameras"][name.strip()] = url.strip()
                config["cameras_list"].append((name.strip(), url.strip()))
            elif item:
                name = f"camera_{len(config['cameras_list'])}"
                config["cameras"][name] = item
                config["cameras_list"].append((name, item))
    
    # Default camera
    default_cam = env_vars.get("SQ_DEFAULT_CAMERA", "0")
    if default_cam.isdigit():
        idx = int(default_cam)
        if config["cameras_list"] and idx < len(config["cameras_list"]):
            config["default_camera"] = config["cameras_list"][idx][0]
        else:
            config["default_camera"] = idx
    else:
        config["default_camera"] = default_cam
    
    # Parse scanner settings
    if "SQ_SCANNER_FPS" in env_vars:
        try:
            config["scanner_fps"] = int(env_vars["SQ_SCANNER_FPS"])
        except ValueError:
            pass
    
    if "SQ_SCANNER_MIN_CONFIDENCE" in env_vars:
        try:
            config["scanner_min_confidence"] = float(env_vars["SQ_SCANNER_MIN_CONFIDENCE"])
        except ValueError:
            pass
    
    if "SQ_SCANNER_CONFIRM_THRESHOLD" in env_vars:
        try:
            config["scanner_confirm_threshold"] = float(env_vars["SQ_SCANNER_CONFIRM_THRESHOLD"])
        except ValueError:
            pass
    
    if "SQ_SCANNER_AUTO_SAVE_THRESHOLD" in env_vars:
        try:
            config["scanner_auto_save_threshold"] = float(env_vars["SQ_SCANNER_AUTO_SAVE_THRESHOLD"])
        except ValueError:
            pass
    
    if "SQ_SCANNER_COOLDOWN_SEC" in env_vars:
        try:
            config["scanner_cooldown_sec"] = int(env_vars["SQ_SCANNER_COOLDOWN_SEC"])
        except ValueError:
            pass
    
    if "SQ_SCANNER_USE_LLM_CONFIRM" in env_vars:
        config["scanner_use_llm_confirm"] = env_vars["SQ_SCANNER_USE_LLM_CONFIRM"].lower() in ("true", "1", "yes")
    
    if "SQ_SCANNER_JPEG_QUALITY" in env_vars:
        try:
            config["scanner_jpeg_quality"] = int(env_vars["SQ_SCANNER_JPEG_QUALITY"])
        except ValueError:
            pass
    
    return config


def load_camera_config_from_env() -> Dict[str, Any]:
    """Load camera configuration from .env file (backward compatibility)."""
    return load_env_config()


def list_available_cameras(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List all available cameras from config."""
    cameras = []
    
    # Add cameras from SQ_CAMERAS
    for name, url in config.get("cameras_list", []):
        cameras.append({
            "name": name,
            "url": url,
            "source": "SQ_CAMERAS",
        })
    
    # Add default URL if not already in list
    default_url = config.get("default_url")
    if default_url:
        urls_in_list = [c["url"] for c in cameras]
        if default_url not in urls_in_list:
            cameras.insert(0, {
                "name": "default",
                "url": default_url,
                "source": "SQ_DEFAULT_URL",
            })
    
    return cameras


class AccountingWebService:
    """Web service for live screen preview with auto-archiving."""

    def __init__(self, project_name: str = "web_archive", port: int = 8080, 
                 open_browser: bool = True, source: str = "screen", 
                 camera_device: int = 0, rtsp_url: str = None, low_latency: bool = True,
                 doc_types: List[str] = None, detect_mode: str = "auto"):
        self.project_name = project_name
        self.port = port
        self.open_browser = open_browser
        self.source = source  # "screen", "camera", or "rtsp"
        self.camera_device = camera_device
        self.rtsp_url = rtsp_url
        self.low_latency = low_latency
        self.scanning = True
        
        # Document type specialization
        self.doc_types = doc_types or ['receipt', 'invoice', 'document']  # All by default
        self.detect_mode = detect_mode  # 'fast', 'accurate', 'auto'
        
        # Load config from .env FIRST
        self.env_config = load_env_config()
        
        # Apply scanner settings from .env
        fps = self.env_config.get("scanner_fps", 2)
        self.interval = 1.0 / fps if fps > 0 else 0.5
        self.min_confidence = self.env_config.get("scanner_min_confidence", 0.25)
        self.confirm_threshold = self.env_config.get("scanner_confirm_threshold", 0.60)
        self.auto_save_threshold = self.env_config.get("scanner_auto_save_threshold", 0.85)
        self.cooldown_sec = self.env_config.get("scanner_cooldown_sec", 2)
        self.use_llm_confirm = self.env_config.get("scanner_use_llm_confirm", True)
        self.jpeg_quality = self.env_config.get("scanner_jpeg_quality", 90)
        
        # Adjust settings based on detect_mode
        if detect_mode == 'fast':
            self.use_yolo = False  # Skip YOLO for speed
            self.interval = 1.0  # 1 FPS
        elif detect_mode == 'accurate':
            self.use_yolo = HAS_YOLO
            self.min_confidence = 0.20  # Lower threshold, more detections
        else:
            self.use_yolo = HAS_YOLO
        
        self.yolo_manager: Optional[YOLOModelManager] = None
        self.document_detector: Optional[DocumentDetector] = None
        self.auto_archive = True
        self.last_hash: Optional[str] = None
        self.clients: List[web.WebSocketResponse] = []
        self.temp_dir = Path(tempfile.mkdtemp())
        self.capture_method: Optional[str] = None
        self.diagnostic_info: Dict[str, Any] = {}
        self.camera_cap: Optional[Any] = None
        self.latest_frame: Optional[bytes] = None
        self.frame_thread: Optional[threading.Thread] = None
        self.frame_thread_running = False
        self.document_detected = False
        self.last_document_frame: Optional[bytes] = None
        self.last_detection_result: Optional[Dict] = None  # Store detection result for confirmation
        self.pending_documents: List[Dict] = []  # Documents waiting for user confirmation
        self.detection_cooldown = 0
        self.available_cameras = list_available_cameras(self.env_config)
        
        # Use RTSP from .env if not provided and source is camera
        if self.source == "camera" and not self.rtsp_url:
            # Try to get camera from config
            default_cam = self.env_config.get("default_camera")
            
            # First try cameras list
            if self.env_config.get("cameras"):
                if isinstance(default_cam, str) and default_cam in self.env_config["cameras"]:
                    self.rtsp_url = self.env_config["cameras"][default_cam]
                    self.source = "rtsp"
                    print(f"📷 Używam kamery '{default_cam}' z SQ_CAMERAS: {self._mask_rtsp_url(self.rtsp_url)}")
                elif self.env_config["cameras_list"]:
                    # Use first camera
                    name, url = self.env_config["cameras_list"][0]
                    self.rtsp_url = url
                    self.source = "rtsp"
                    print(f"📷 Używam kamery '{name}' z SQ_CAMERAS: {self._mask_rtsp_url(self.rtsp_url)}")
            
            # Fallback to SQ_DEFAULT_URL
            if not self.rtsp_url and self.env_config.get("default_url"):
                self.rtsp_url = self.env_config["default_url"]
                self.source = "rtsp"
                print(f"📷 Używam kamery z SQ_DEFAULT_URL: {self._mask_rtsp_url(self.rtsp_url)}")

        # Import accounting components
        from .components.accounting import (
            AccountingProjectManager, InteractiveScanner,
            DocumentAnalyzer, get_best_ocr_engine
        )

        self.manager = AccountingProjectManager()
        self.project = self.manager.get_project(project_name) or self.manager.create_project(project_name)
        self.ocr_engine = get_best_ocr_engine()
        self.scanner = InteractiveScanner(self.manager, project_name)

    def _mask_rtsp_url(self, url: str) -> str:
        """Mask password in RTSP URL for display."""
        if not url:
            return ""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)

    def run_diagnostics(self, check_cameras: bool = None) -> Dict[str, Any]:
        """Run diagnostics to check available capture methods."""
        # Check cameras if source is camera/rtsp or explicitly requested
        if check_cameras is None:
            check_cameras = (self.source in ("camera", "rtsp"))

        results = {
            "source": self.source,
            "screen_methods": [],
            "camera_available": False,
            "camera_devices": [],
            "rtsp_url": self._mask_rtsp_url(self.rtsp_url) if self.rtsp_url else None,
            "rtsp_working": False,
            "selected_camera": None,
            "recommended": None,
            "errors": [],
            "env_config": {
                "default_url": self._mask_rtsp_url(self.env_config.get("default_url")) if self.env_config.get("default_url") else None,
                "default_camera": self.env_config.get("default_camera", 0),
                "cameras_count": len(self.env_config.get("cameras_list", [])),
            },
            "available_cameras": [
                {"name": c["name"], "url": self._mask_rtsp_url(c["url"]), "source": c["source"]}
                for c in self.available_cameras
            ],
        }

        # Check screen capture methods
        screen_tools = [
            ("grim", ["grim", "--help"], "Wayland native (recommended for Wayland)"),
            ("gnome-screenshot", ["gnome-screenshot", "--version"], "GNOME (X11/Wayland)"),
            ("spectacle", ["spectacle", "--version"], "KDE"),
            ("scrot", ["scrot", "--version"], "X11"),
            ("ffmpeg", ["ffmpeg", "-version"], "FFmpeg x11grab"),
        ]

        for name, cmd, desc in screen_tools:
            try:
                result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
                if result.returncode == 0 or name == "grim":  # grim --help returns non-zero
                    results["screen_methods"].append({"name": name, "desc": desc, "available": True})
                else:
                    results["screen_methods"].append({"name": name, "desc": desc, "available": False})
            except (FileNotFoundError, subprocess.TimeoutExpired):
                results["screen_methods"].append({"name": name, "desc": desc, "available": False})

        # Check camera devices only if needed
        if check_cameras and HAS_CV2:
            # Check /dev/video* devices first (faster, no OpenCV warnings)
            video_devices = list(Path("/dev").glob("video*"))
            results["video_devices"] = [str(d) for d in video_devices]
            
            # Only try OpenCV if we found video devices
            for dev in video_devices:
                try:
                    idx = int(str(dev).replace("/dev/video", ""))
                    cap = cv2.VideoCapture(idx)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            h, w = frame.shape[:2]
                            results["camera_devices"].append({
                                "index": idx,
                                "resolution": f"{w}x{h}",
                                "path": str(dev),
                                "working": True
                            })
                            results["camera_available"] = True
                        cap.release()
                except Exception:
                    pass
            
            # Check RTSP if configured
            if self.rtsp_url:
                try:
                    cap = cv2.VideoCapture(self.rtsp_url)
                    if cap.isOpened():
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            h, w = frame.shape[:2]
                            results["rtsp_working"] = True
                            results["rtsp_resolution"] = f"{w}x{h}"
                            results["camera_available"] = True
                        cap.release()
                    else:
                        results["errors"].append(f"Nie można połączyć z RTSP: {self._mask_rtsp_url(self.rtsp_url)}")
                except Exception as e:
                    results["errors"].append(f"Błąd RTSP: {e}")
            
            # Determine selected camera
            if self.source == "rtsp" and self.rtsp_url:
                results["selected_camera"] = f"RTSP: {self._mask_rtsp_url(self.rtsp_url)}"
            elif self.source == "camera":
                results["selected_camera"] = f"Lokalna kamera: /dev/video{self.camera_device}"
                
        elif check_cameras:
            # Just check /dev/video* without OpenCV
            video_devices = list(Path("/dev").glob("video*"))
            results["video_devices"] = [str(d) for d in video_devices]

        # Check environment
        results["display"] = os.environ.get("DISPLAY")
        results["wayland_display"] = os.environ.get("WAYLAND_DISPLAY")
        results["xdg_session_type"] = os.environ.get("XDG_SESSION_TYPE")

        # Determine recommended method
        is_wayland = results["xdg_session_type"] == "wayland" or results["wayland_display"]
        
        if self.source == "camera":
            if results["camera_available"]:
                results["recommended"] = f"camera (device {self.camera_device})"
            else:
                results["errors"].append("Brak dostępnej kamery! Użyj --source screen")
        else:
            if is_wayland:
                grim_available = any(m["name"] == "grim" and m["available"] for m in results["screen_methods"])
                if grim_available:
                    results["recommended"] = "grim (Wayland)"
                else:
                    # Check if any screen method works
                    any_available = any(m["available"] for m in results["screen_methods"])
                    if any_available:
                        results["recommended"] = "ffmpeg/scrot (fallback)"
                    else:
                        results["errors"].append("Brak narzędzi do przechwytywania ekranu!")

        self.diagnostic_info = results
        return results

    def print_diagnostics(self, results: Dict[str, Any]):
        """Print diagnostic results."""
        print("\n🔍 Diagnostyka systemu przechwytywania:")
        print("-" * 50)
        
        # Environment
        print(f"   Środowisko: {results.get('xdg_session_type', 'unknown')}")
        print(f"   DISPLAY: {results.get('display', 'nie ustawione')}")
        print(f"   WAYLAND_DISPLAY: {results.get('wayland_display', 'nie ustawione')}")
        
        # Screen methods
        print(f"\n   📺 Metody przechwytywania ekranu:")
        for method in results.get("screen_methods", []):
            status = "✅" if method["available"] else "❌"
            print(f"      {status} {method['name']} - {method['desc']}")
        
        # Camera
        print(f"\n   📷 Kamery lokalne:")
        if results.get("camera_devices"):
            for cam in results["camera_devices"]:
                status = "✅" if cam.get("working") else "⚠️"
                print(f"      {status} {cam['path']} ({cam['resolution']})")
        else:
            print("      ❌ Brak dostępnych kamer lokalnych")
        
        if results.get("video_devices"):
            print(f"      Urządzenia /dev/video*: {', '.join(results['video_devices'])}")
        
        # RTSP / Cameras from .env
        print(f"\n   🌐 Kamery RTSP/IP (z .env):")
        available_cams = results.get("available_cameras", [])
        if available_cams:
            for i, cam in enumerate(available_cams):
                is_selected = results.get("rtsp_url") and cam["url"] == results.get("rtsp_url")
                marker = "🎯" if is_selected else "  "
                print(f"      {marker} [{i}] {cam['name']}: {cam['url']} ({cam['source']})")
        else:
            env_url = results.get("env_config", {}).get("default_url")
            if env_url:
                print(f"      📋 SQ_DEFAULT_URL: {env_url}")
            else:
                print("      ❌ Brak skonfigurowanych kamer")
                print("      💡 Dodaj do .env:")
                print("         SQ_DEFAULT_URL=rtsp://user:pass@192.168.1.100:554/stream")
                print("         # Lub lista kamer:")
                print("         SQ_CAMERAS=front|rtsp://...,back|rtsp://...")
        
        # Current RTSP status
        if results.get("rtsp_url"):
            status = "✅" if results.get("rtsp_working") else "❌"
            resolution = results.get("rtsp_resolution", "nieznana")
            print(f"\n   📡 Aktywna kamera RTSP:")
            print(f"      {status} {results['rtsp_url']} ({resolution})")
        
        # Selected camera
        if results.get("selected_camera"):
            print(f"\n   🎯 Wybrana kamera: {results['selected_camera']}")
        
        # Recommendation
        print(f"\n   💡 Zalecane: {results.get('recommended', 'brak')}")
        
        # Errors
        if results.get("errors"):
            print(f"\n   ⚠️  Problemy:")
            for err in results["errors"]:
                print(f"      - {err}")
        
        print("-" * 50)

    def detect_document_fast(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Document detection using specialized methods based on doc_types.
        Priority order depends on what we're looking for:
        - receipt: Receipt detector first (shape + text lines)
        - invoice: Invoice detector first (A4 format)
        - document: General edge detection
        """
        t_start = time.time()
        
        result = {
            "detected": False,
            "confidence": 0.0,
            "bbox": None,
            "area_ratio": 0.0,
            "method": None,
            "class_name": None,
            "document_type": None,
            "timing": {},
            "features": [],
        }
        
        if frame is None:
            return result
        
        h, w = frame.shape[:2]
        frame_area = h * w
        
        # Initialize document detector
        if self.document_detector is None:
            self.document_detector = get_document_detector()
        
        # Determine detection order based on doc_types
        detect_receipt = 'receipt' in self.doc_types or 'paragon' in self.doc_types
        detect_invoice = 'invoice' in self.doc_types or 'faktura' in self.doc_types
        detect_general = 'document' in self.doc_types or len(self.doc_types) == 0
        
        # SPECIALIZED DETECTION: Receipt mode
        if detect_receipt:
            t_r = time.time()
            receipt_result = self.document_detector.detect_receipt_features(frame)
            result["timing"]["receipt"] = (time.time() - t_r) * 1000
            
            if receipt_result["is_receipt"] and receipt_result["confidence"] > 0.35:
                result["detected"] = True
                result["confidence"] = receipt_result["confidence"]
                result["bbox"] = receipt_result.get("bbox")
                result["method"] = "receipt_detector"
                result["document_type"] = "paragon"
                result["features"] = receipt_result.get("features", [])
                if result["bbox"]:
                    bx, by, bw, bh = result["bbox"]
                    result["area_ratio"] = (bw * bh) / frame_area
                result["timing"]["total"] = (time.time() - t_start) * 1000
                return result
        
        # SPECIALIZED DETECTION: Invoice mode
        if detect_invoice:
            t_i = time.time()
            invoice_result = self.document_detector.detect_invoice_features(frame)
            result["timing"]["invoice"] = (time.time() - t_i) * 1000
            
            if invoice_result["is_invoice"] and invoice_result["confidence"] > 0.35:
                result["detected"] = True
                result["confidence"] = invoice_result["confidence"]
                result["bbox"] = invoice_result.get("bbox")
                result["method"] = "invoice_detector"
                result["document_type"] = "faktura"
                result["features"] = invoice_result.get("features", [])
                if result["bbox"]:
                    bx, by, bw, bh = result["bbox"]
                    result["area_ratio"] = (bw * bh) / frame_area
                result["timing"]["total"] = (time.time() - t_start) * 1000
                return result
        
        # GENERAL DETECTION: OpenCV edge detection
        t1 = time.time()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)
        
        kernel = np.ones((5, 5), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=3)
        edges = cv2.erode(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        result["timing"]["opencv"] = (time.time() - t1) * 1000
        
        best_score = 0
        best_result = None
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < frame_area * 0.03 or area > frame_area * 0.98:
                continue
            
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) >= 4 and len(approx) <= 8:
                x, y, bw, bh = cv2.boundingRect(contour)
                rect_area = bw * bh
                area_ratio = area / frame_area
                rectangularity = area / rect_area if rect_area > 0 else 0
                aspect_ratio = max(bw, bh) / min(bw, bh) if min(bw, bh) > 0 else 0
                
                aspect_score = 1.0 if 1.0 <= aspect_ratio <= 3.0 else max(0, 1 - abs(aspect_ratio - 2.0) / 2)
                area_score = 1.0 if 0.1 <= area_ratio <= 0.8 else 0.5
                score = (rectangularity * 0.3 + aspect_score * 0.3 + area_score * 0.4)
                
                if score > best_score:
                    best_score = score
                    best_result = {"bbox": (x, y, bw, bh), "area_ratio": area_ratio}
        
        # Edge density check
        edge_density = np.sum(edges > 0) / frame_area
        if edge_density > 0.04 and best_score < 0.3:
            best_score = max(best_score, 0.4)
            if best_result is None:
                best_result = {"bbox": (0, 0, w, h), "area_ratio": 1.0}
        
        if best_score > 0.3 and best_result:
            result["detected"] = True
            result["confidence"] = best_score
            result["bbox"] = best_result["bbox"]
            result["area_ratio"] = best_result["area_ratio"]
            result["method"] = "opencv"
            result["document_type"] = "dokument"
            result["timing"]["total"] = (time.time() - t_start) * 1000
            return result
        
        # YOLO detection (slower but accurate)
        if self.use_yolo:
            t3 = time.time()
            if self.yolo_manager is None:
                self.yolo_manager = get_yolo_manager()
            
            yolo_result = self.yolo_manager.detect_any(frame, conf_threshold=0.25)
            result["timing"]["yolo"] = (time.time() - t3) * 1000
            
            if yolo_result["detected"]:
                result["detected"] = True
                result["confidence"] = yolo_result["confidence"]
                result["bbox"] = yolo_result["bbox"]
                result["method"] = "yolo"
                result["class_name"] = yolo_result["class_name"]
                
                if yolo_result["bbox"]:
                    bx, by, bw, bh = yolo_result["bbox"]
                    result["area_ratio"] = (bw * bh) / frame_area
                result["timing"]["total"] = (time.time() - t_start) * 1000
                return result
            
            # Check all YOLO detections for document-like objects
            for det in yolo_result.get("all_detections", []):
                bbox = det["bbox"]
                x1, y1, x2, y2 = bbox
                det_w, det_h = x2 - x1, y2 - y1
                det_area = det_w * det_h
                area_ratio = det_area / frame_area
                
                aspect = max(det_w, det_h) / min(det_w, det_h) if min(det_w, det_h) > 0 else 0
                if 1.0 <= aspect <= 3.0 and area_ratio > 0.05:
                    result["detected"] = True
                    result["confidence"] = det["confidence"]
                    result["bbox"] = (int(x1), int(y1), int(det_w), int(det_h))
                    result["method"] = "yolo"
                    result["class_name"] = det["class_name"]
                    result["area_ratio"] = area_ratio
                    result["timing"]["total"] = (time.time() - t_start) * 1000
                    return result
        
        # Skip DocTR for speed - it's too slow (~200-500ms)
        # Only use it for final OCR analysis, not detection
        
        result["timing"]["total"] = (time.time() - t_start) * 1000
        return result

    def _create_thumbnail(self, image_bytes: bytes, max_size: int = 120) -> Optional[bytes]:
        """Create a thumbnail from image bytes."""
        if not HAS_CV2 or not image_bytes:
            return None
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                return None
            
            h, w = img.shape[:2]
            scale = max_size / max(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            thumb = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
            _, jpeg = cv2.imencode('.jpg', thumb, [cv2.IMWRITE_JPEG_QUALITY, 60])
            return jpeg.tobytes()
        except Exception:
            return None

    def capture(self) -> Optional[bytes]:
        """Capture from configured source (screen, camera, or rtsp)."""
        if self.source == "rtsp" and self.rtsp_url:
            return self.capture_rtsp()
        elif self.source == "camera":
            return self.capture_camera(self.camera_device)
        else:
            return self.capture_screen()

    def _start_frame_thread(self):
        """Start background thread for continuous frame grabbing (low latency)."""
        if self.frame_thread_running:
            return
        
        if not self.rtsp_url:
            return
        
        self.frame_thread_running = True
        
        # Try PyAV first (fastest, ~100ms latency after connection)
        if HAS_PYAV:
            def grab_frames_pyav():
                """Grab frames using PyAV (FFmpeg bindings) - lowest latency with document detection."""
                try:
                    print(f"   📡 Łączenie z RTSP (PyAV)...")
                    container = av.open(self.rtsp_url, options={
                        'rtsp_transport': 'tcp',
                        'fflags': 'nobuffer',
                        'flags': 'low_delay',
                        'max_delay': '500000',  # 0.5s max delay
                    }, timeout=10.0)
                    
                    stream = container.streams.video[0]
                    stream.thread_type = 'AUTO'  # Enable multi-threaded decoding
                    print(f"   ✅ Połączono: {stream.width}x{stream.height} @ {stream.average_rate} fps")
                    
                    frame_count = 0
                    for frame in container.decode(video=0):
                        if not self.frame_thread_running:
                            break
                        try:
                            # Convert to numpy array
                            img = frame.to_ndarray(format='bgr24')
                            
                            # Document detection based on FPS from .env
                            frame_count += 1
                            detection_interval = max(1, int(10 / self.env_config.get("scanner_fps", 2)))
                            if frame_count % detection_interval == 0:
                                detection = self.detect_document_fast(img)
                                self.document_detected = detection["detected"]
                                self.last_detection_result = detection
                                
                                # Log timing info
                                timing = detection.get("timing", {})
                                total_ms = timing.get("total", 0)
                                if total_ms > 100:
                                    print(f"   ⏱️ Detekcja: {total_ms:.0f}ms (opencv: {timing.get('opencv_edge', 0):.0f}ms, receipt: {timing.get('receipt_detect', 0):.0f}ms, yolo: {timing.get('yolo', 0):.0f}ms)")
                                
                                if detection["detected"] and detection["confidence"] >= self.min_confidence:
                                    if self.detection_cooldown <= 0:
                                        _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                                        doc_type = detection.get('document_type') or detection.get('class_name') or 'dokument'
                                        
                                        # Hierarchical decision based on confidence
                                        if detection["confidence"] >= self.auto_save_threshold:
                                            # High confidence - auto save
                                            self.last_document_frame = jpeg.tobytes()
                                            print(f"   📸 Auto-zapis: {doc_type} (pewność: {detection['confidence']:.0%}, metoda: {detection.get('method')}, {total_ms:.0f}ms)")
                                        elif detection["confidence"] >= self.confirm_threshold:
                                            # Medium confidence - add to pending for confirmation
                                            self.pending_documents.append({
                                                "frame": jpeg.tobytes(),
                                                "detection": detection,
                                                "timestamp": time.time(),
                                                "doc_type": doc_type,
                                            })
                                            print(f"   🔍 Do potwierdzenia: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                        else:
                                            # Low confidence - just notify
                                            print(f"   👁️ Możliwy dokument: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                        
                                        self.detection_cooldown = int(self.cooldown_sec * 10)
                                
                                if self.detection_cooldown > 0:
                                    self.detection_cooldown -= 1
                            
                            # Encode to JPEG for live preview
                            _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                            self.latest_frame = jpeg.tobytes()
                        except Exception:
                            pass
                    
                    container.close()
                except Exception as e:
                    print(f"   ⚠️ PyAV error: {e}")
                    self.frame_thread_running = False
            
            self.frame_thread = threading.Thread(target=grab_frames_pyav, daemon=True)
            self.frame_thread.start()
            print(f"   🎥 Uruchomiono PyAV low-latency z detekcją dokumentów")
            return
        
        # Fallback to OpenCV with FFMPEG
        if not HAS_CV2:
            print(f"   ❌ Brak PyAV ani OpenCV")
            self.frame_thread_running = False
            return
        
        # Set FFMPEG options for low latency BEFORE creating capture
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|buffer_size;65536|max_delay;0|fflags;nobuffer+discardcorrupt|flags;low_delay|analyzeduration;0|probesize;32"
        
        self.camera_cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        
        if not self.camera_cap.isOpened():
            print(f"   ❌ Nie można otworzyć strumienia RTSP")
            self.frame_thread_running = False
            return
        
        # Set minimal buffer
        self.camera_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        
        frame_count = [0]  # Use list to allow modification in nested function
        
        def grab_frames_opencv():
            """Continuously grab frames using OpenCV with document detection."""
            while self.frame_thread_running and self.camera_cap and self.camera_cap.isOpened():
                try:
                    ret, frame = self.camera_cap.read()
                    if ret and frame is not None:
                        # Document detection based on FPS from .env
                        frame_count[0] += 1
                        detection_interval = max(1, int(10 / self.env_config.get("scanner_fps", 2)))
                        if frame_count[0] % detection_interval == 0:
                            detection = self.detect_document_fast(frame)
                            self.document_detected = detection["detected"]
                            self.last_detection_result = detection
                            
                            # Log timing info
                            timing = detection.get("timing", {})
                            total_ms = timing.get("total", 0)
                            if total_ms > 100:
                                print(f"   ⏱️ Detekcja: {total_ms:.0f}ms")
                            
                            if detection["detected"] and detection["confidence"] >= self.min_confidence:
                                if self.detection_cooldown <= 0:
                                    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                                    doc_type = detection.get('document_type') or detection.get('class_name') or 'dokument'
                                    
                                    if detection["confidence"] >= self.auto_save_threshold:
                                        self.last_document_frame = jpeg.tobytes()
                                        print(f"   📸 Auto-zapis: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                    elif detection["confidence"] >= self.confirm_threshold:
                                        self.pending_documents.append({
                                            "frame": jpeg.tobytes(),
                                            "detection": detection,
                                            "timestamp": time.time(),
                                            "doc_type": doc_type,
                                        })
                                        print(f"   🔍 Do potwierdzenia: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                    else:
                                        print(f"   👁️ Możliwy dokument: {doc_type} (pewność: {detection['confidence']:.0%}, {total_ms:.0f}ms)")
                                    
                                    self.detection_cooldown = int(self.cooldown_sec * 10)
                            
                            if self.detection_cooldown > 0:
                                self.detection_cooldown -= 1
                        
                        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                        self.latest_frame = jpeg.tobytes()
                except Exception:
                    pass
                time.sleep(0.01)
        
        self.frame_thread = threading.Thread(target=grab_frames_opencv, daemon=True)
        self.frame_thread.start()
        print(f"   🎥 Uruchomiono OpenCV low-latency z detekcją dokumentów")

    def _stop_frame_thread(self):
        """Stop the frame grabbing thread."""
        self.frame_thread_running = False
        if self.frame_thread:
            self.frame_thread.join(timeout=1.0)
            self.frame_thread = None
        if self.camera_cap:
            self.camera_cap.release()
            self.camera_cap = None
        self.latest_frame = None

    def capture_rtsp(self) -> Optional[bytes]:
        """Capture from RTSP camera stream with low latency."""
        if not HAS_CV2 or not self.rtsp_url:
            return None

        # Start frame thread if not running
        if not self.frame_thread_running:
            self._start_frame_thread()
            # Wait a bit for first frame
            time.sleep(0.1)
        
        # Return the latest frame (grabbed by background thread)
        return self.latest_frame

    def capture_screen(self) -> Optional[bytes]:
        """Capture screen and return as JPEG bytes."""
        # Method 1: Try grim (Wayland native - best for Wayland)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            result = subprocess.run(
                ["grim", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 2: Try gnome-screenshot with dbus (works better on Wayland)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            result = subprocess.run(
                ["gnome-screenshot", "-f", str(output_path), "--display=:0"],
                capture_output=True, timeout=5,
                env={**os.environ, "XDG_SESSION_TYPE": "x11"}
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 3: Try spectacle (KDE)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            result = subprocess.run(
                ["spectacle", "-b", "-n", "-o", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 4: Try scrot (X11)
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.png"
            result = subprocess.run(
                ["scrot", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                return self._convert_to_jpeg(output_path)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # Method 5: Try PIL ImageGrab (may work on some systems)
        if HAS_PIL:
            try:
                screenshot = ImageGrab.grab()
                if screenshot:
                    buffer = io.BytesIO()
                    screenshot.save(buffer, format='JPEG', quality=70)
                    return buffer.getvalue()
            except Exception:
                pass

        # Method 6: Try ffmpeg with x11grab
        try:
            output_path = self.temp_dir / f"screen_{int(time.time() * 1000)}.jpg"
            display = os.environ.get("DISPLAY", ":0")
            result = subprocess.run(
                ["ffmpeg", "-y", "-f", "x11grab", "-video_size", "1920x1080",
                 "-i", display, "-vframes", "1", "-q:v", "2", str(output_path)],
                capture_output=True, timeout=5
            )
            if output_path.exists() and output_path.stat().st_size > 0:
                with open(output_path, 'rb') as f:
                    data = f.read()
                output_path.unlink()
                return data
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        return None

    def _convert_to_jpeg(self, image_path: Path) -> Optional[bytes]:
        """Convert image file to JPEG bytes."""
        try:
            with open(image_path, 'rb') as f:
                data = f.read()
            image_path.unlink()

            if HAS_CV2:
                nparr = np.frombuffer(data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    _, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    return jpeg.tobytes()
            return data
        except Exception:
            return None

    def capture_camera(self, device: int = 0) -> Optional[bytes]:
        """Capture from camera and return as JPEG bytes."""
        if not HAS_CV2:
            return None

        try:
            cap = cv2.VideoCapture(device)
            if not cap.isOpened():
                return None

            ret, frame = cap.read()
            cap.release()

            if ret and frame is not None:
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                return jpeg.tobytes()
        except Exception:
            pass

        return None

    def analyze_frame(self, image_bytes: bytes) -> Dict[str, Any]:
        """Analyze frame for document detection."""
        result = {
            "detected": False,
            "doc_type": None,
            "confidence": 0.0,
        }

        try:
            # Save to temp file for OCR
            temp_path = self.temp_dir / "current_frame.jpg"
            with open(temp_path, 'wb') as f:
                f.write(image_bytes)

            # Quick OCR to detect document
            text, confidence, _ = self.ocr_engine.extract_text(temp_path, lang="pol")

            if text and len(text) > 50:  # Minimum text length
                from .components.accounting import DocumentAnalyzer

                doc_type = DocumentAnalyzer.classify_document(text)

                if doc_type != "other" and confidence >= self.min_confidence:
                    result["detected"] = True
                    result["doc_type"] = doc_type
                    result["confidence"] = confidence
                    result["text"] = text[:200]  # Preview

        except Exception as e:
            print(f"Analysis error: {e}")

        return result

    async def broadcast(self, message: Dict):
        """Send message to all connected clients."""
        data = json.dumps(message, default=str)
        for ws in self.clients[:]:
            try:
                await ws.send_str(data)
            except Exception:
                self.clients.remove(ws)

    async def scan_loop(self):
        """Main scanning loop with real-time document detection."""
        frame_sent_count = 0
        while True:
            if self.scanning and self.clients:
                try:
                    # Get latest frame from background thread
                    image_bytes = self.capture()

                    if image_bytes:
                        frame_sent_count += 1
                        if frame_sent_count <= 3:
                            print(f"   📡 Wysyłam ramkę #{frame_sent_count} do {len(self.clients)} klientów ({len(image_bytes)} bytes)")
                        # Get detection info
                        detection = self.last_detection_result or {}
                        
                        # Send frame with real-time detection status
                        await self.broadcast({
                            "type": "frame",
                            "image": base64.b64encode(image_bytes).decode(),
                            "document_in_view": self.document_detected,
                            "confidence": detection.get("confidence", 0),
                            "doc_type": detection.get("document_type") or detection.get("class_name"),
                            "method": detection.get("method"),
                            "pending_count": len(self.pending_documents),
                        })
                        
                        # Send new pending documents to browser
                        while self.pending_documents:
                            pending_doc = self.pending_documents.pop(0)
                            # Create thumbnail (smaller version)
                            thumbnail = self._create_thumbnail(pending_doc["frame"], max_size=120)
                            doc_id = int(time.time() * 1000) % 100000
                            
                            await self.broadcast({
                                "type": "pending_document",
                                "document": {
                                    "id": doc_id,
                                    "doc_type": pending_doc["doc_type"],
                                    "type": pending_doc["doc_type"],
                                    "confidence": pending_doc["detection"]["confidence"],
                                    "thumbnail": base64.b64encode(thumbnail).decode() if thumbnail else None,
                                    "pending": True,
                                    "timestamp": pending_doc["timestamp"],
                                }
                            })
                            
                            # Store for confirmation
                            self._pending_by_id = getattr(self, '_pending_by_id', {})
                            self._pending_by_id[doc_id] = pending_doc
                        
                        # If document was captured (by background thread), process it
                        if self.last_document_frame and self.auto_archive:
                            doc_frame = self.last_document_frame
                            self.last_document_frame = None  # Clear to prevent re-processing
                            
                            # Full OCR analysis on captured document
                            analysis = self.analyze_frame(doc_frame)
                            
                            if analysis["detected"]:
                                await self.broadcast({
                                    "type": "log",
                                    "message": f"📄 Wykryto dokument: {analysis['doc_type']} ({analysis['confidence']:.0%})",
                                    "level": "success"
                                })
                                
                                # Archive the document
                                await self.archive_document(doc_frame, analysis)

                except Exception as e:
                    await self.broadcast({
                        "type": "log",
                        "message": f"Błąd: {e}",
                        "level": "error"
                    })

            await asyncio.sleep(self.interval)

    async def archive_document(self, image_bytes: bytes, analysis: Dict):
        """Archive detected document."""
        try:
            # Save image
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_type = analysis.get("doc_type", "other")
            filename = f"{timestamp}_{doc_type}.jpg"
            file_path = self.temp_dir / filename

            with open(file_path, 'wb') as f:
                f.write(image_bytes)

            # Process document
            doc_info = self.scanner.process_document(file_path, auto_crop=True)

            # Notify clients
            await self.broadcast({
                "type": "document",
                "document": {
                    "id": doc_info.id,
                    "type": doc_info.type,
                    "amount": doc_info.extracted_data.get("amounts", {}).get("gross") or
                             doc_info.extracted_data.get("total_amount"),
                    "date": doc_info.scan_date.strftime("%H:%M:%S"),
                }
            })

            # Send updated summary
            summary = self.manager.get_summary(self.project_name)
            await self.broadcast({
                "type": "summary",
                "summary": summary
            })

        except Exception as e:
            await self.broadcast({
                "type": "log",
                "message": f"Błąd archiwizacji: {e}",
                "level": "error"
            })

    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.clients.append(ws)

        # Send initial config
        await ws.send_str(json.dumps({
            "type": "config",
            "project": self.project_name
        }))

        # Send current summary
        summary = self.manager.get_summary(self.project_name)
        await ws.send_str(json.dumps({
            "type": "summary",
            "summary": summary
        }))

        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self.handle_command(data, ws)
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            self.clients.remove(ws)

        return ws

    async def handle_command(self, data: Dict, ws):
        """Handle commands from client."""
        action = data.get("action")

        if action == "toggle":
            self.scanning = data.get("scanning", True)

        elif action == "capture":
            # Force immediate capture
            image_bytes = self.capture()
            if image_bytes:
                analysis = self.analyze_frame(image_bytes)
                if analysis["detected"]:
                    await self.archive_document(image_bytes, analysis)
                else:
                    await ws.send_str(json.dumps({
                        "type": "log",
                        "message": "Nie wykryto dokumentu na ekranie",
                        "level": "warning"
                    }))

        elif action == "set_interval":
            self.interval = max(0.5, min(10, data.get("interval", 1.0)))

        elif action == "set_confidence":
            self.min_confidence = max(0.1, min(0.95, data.get("confidence", 0.5)))

        elif action == "set_auto_archive":
            self.auto_archive = data.get("enabled", True)
        
        elif action == "get_pending":
            # Send list of pending documents for confirmation
            pending_list = []
            for i, doc in enumerate(self.pending_documents[-10:]):  # Last 10
                pending_list.append({
                    "id": i,
                    "doc_type": doc["doc_type"],
                    "confidence": doc["detection"]["confidence"],
                    "timestamp": doc["timestamp"],
                    "image": base64.b64encode(doc["frame"]).decode(),
                })
            await ws.send_str(json.dumps({
                "type": "pending_documents",
                "documents": pending_list,
                "count": len(self.pending_documents)
            }))
        
        elif action == "confirm_document":
            # Confirm and save a pending document
            doc_id = data.get("id", 0)
            pending_by_id = getattr(self, '_pending_by_id', {})
            if doc_id in pending_by_id:
                doc = pending_by_id.pop(doc_id)
                analysis = doc["detection"]
                analysis["detected"] = True
                analysis["doc_type"] = doc["doc_type"]
                await self.archive_document(doc["frame"], analysis)
                await ws.send_str(json.dumps({
                    "type": "log",
                    "message": f"✅ Zapisano: {doc['doc_type']}",
                    "level": "success"
                }))
        
        elif action == "reject_document":
            # Reject a pending document
            doc_id = data.get("id", 0)
            pending_by_id = getattr(self, '_pending_by_id', {})
            if doc_id in pending_by_id:
                doc = pending_by_id.pop(doc_id)
                await ws.send_str(json.dumps({
                    "type": "log",
                    "message": f"❌ Odrzucono: {doc['doc_type']}",
                    "level": "warning"
                }))
        
        elif action == "confirm_all":
            # Confirm all pending documents
            count = len(self.pending_documents)
            for doc in self.pending_documents:
                analysis = doc["detection"]
                analysis["detected"] = True
                await self.archive_document(doc["frame"], analysis)
            self.pending_documents.clear()
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"✅ Potwierdzono {count} dokumentów",
                "level": "success"
            }))
        
        elif action == "reject_all":
            # Reject all pending documents
            count = len(self.pending_documents)
            self.pending_documents.clear()
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"❌ Odrzucono {count} dokumentów",
                "level": "warning"
            }))
        
        elif action == "get_documents":
            # Get list of archived documents with OCR data
            docs = self.manager.get_documents(self.project_name)
            await ws.send_str(json.dumps({
                "type": "documents_list",
                "documents": docs[:50]  # Last 50
            }))
        
        elif action == "get_ocr_data":
            # Get OCR data for specific document
            doc_id = data.get("doc_id")
            doc = self.manager.get_document(self.project_name, doc_id)
            if doc:
                await ws.send_str(json.dumps({
                    "type": "document_detail",
                    "document": doc
                }))
        
        elif action == "get_settings":
            # Send current scanner settings
            await ws.send_str(json.dumps({
                "type": "settings",
                "fps": 1.0 / self.interval if self.interval > 0 else 2,
                "min_confidence": self.min_confidence,
                "confirm_threshold": self.confirm_threshold,
                "auto_save_threshold": self.auto_save_threshold,
                "cooldown_sec": self.cooldown_sec,
                "use_llm_confirm": self.use_llm_confirm,
                "auto_archive": self.auto_archive,
            }))

    async def handle_index(self, request):
        """Serve main HTML page."""
        return web.Response(text=HTML_TEMPLATE, content_type='text/html')

    async def handle_export_csv(self, request):
        """Export documents to CSV."""
        csv_path = self.manager.export_to_csv(self.project_name)

        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()

        return web.Response(
            text=content,
            content_type='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename="{self.project_name}.csv"'
            }
        )

    def run(self):
        """Start the web server."""
        if not HAS_AIOHTTP:
            print("❌ Wymagany pakiet: pip install aiohttp")
            return

        app = web.Application()
        app.router.add_get('/', self.handle_index)
        app.router.add_get('/ws', self.handle_websocket)
        app.router.add_get('/export/csv', self.handle_export_csv)

        # Start scan loop in background
        async def start_background_tasks(app):
            app['scan_task'] = asyncio.create_task(self.scan_loop())

        async def cleanup_background_tasks(app):
            app['scan_task'].cancel()
            try:
                await app['scan_task']
            except asyncio.CancelledError:
                pass
            # Stop frame thread and cleanup RTSP capture
            self._stop_frame_thread()
            # Cleanup temp files
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            print("\n✅ Usługa zakończona poprawnie.")

        app.on_startup.append(start_background_tasks)
        app.on_cleanup.append(cleanup_background_tasks)

        # Run diagnostics first
        diag = self.run_diagnostics()
        self.print_diagnostics(diag)

        # Check for critical errors
        if diag.get("errors"):
            print("\n⚠️  Wykryto problemy. Usługa może nie działać poprawnie.")
            print("   Spróbuj zainstalować brakujące narzędzia lub zmień źródło.\n")

        print(f"\n📄 Streamware Accounting Web Service")
        print(f"   Projekt: {self.project_name}")
        print(f"   Źródło: {self.source}")
        print(f"   URL: http://localhost:{self.port}")
        print(f"   Ctrl+C aby zakończyć\n")

        # Open browser if requested
        if self.open_browser:
            import webbrowser
            webbrowser.open(f"http://localhost:{self.port}")

        web.run_app(app, host='0.0.0.0', port=self.port, print=None)


def find_free_port(start_port: int = 8088, max_attempts: int = 10) -> int:
    """Find a free port starting from start_port."""
    import socket
    for i in range(max_attempts):
        port = start_port + i
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            continue
    return start_port + max_attempts


def run_opencv_preview(source: str = "screen", camera_device: int = 0):
    """
    Run OpenCV window preview without browser.
    Alternative for users who prefer native window over browser.
    """
    if not HAS_CV2:
        print("❌ OpenCV nie jest zainstalowany. Zainstaluj: pip install opencv-python")
        return

    print("\n🎥 Podgląd na żywo (OpenCV)")
    print("-" * 40)
    print(f"   Źródło: {source}")
    if source == "camera":
        print(f"   Kamera: /dev/video{camera_device}")
    print(f"\n   Klawisze:")
    print(f"   [SPACE] - Zrób zrzut i analizuj")
    print(f"   [S] - Zapisz bieżącą klatkę")
    print(f"   [Q/ESC] - Zakończ")
    print("-" * 40)

    # Create temp service for capture methods
    service = AccountingWebService(
        project_name="preview", 
        port=9999,  # Not used
        open_browser=False,
        source=source,
        camera_device=camera_device
    )

    # Run diagnostics
    diag = service.run_diagnostics()
    service.print_diagnostics(diag)

    if source == "camera":
        if not diag.get("camera_available"):
            print("\n❌ Brak dostępnej kamery!")
            print("   Użyj: sq accounting preview --source screen")
            return

        # Use OpenCV VideoCapture for live camera feed
        cap = cv2.VideoCapture(camera_device)
        if not cap.isOpened():
            print(f"❌ Nie można otworzyć kamery {camera_device}")
            return

        print(f"\n✅ Kamera {camera_device} otwarta")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                print("❌ Błąd odczytu z kamery")
                break

            # Show frame
            cv2.imshow("Streamware Accounting Preview (Q=quit, SPACE=capture)", frame)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord('q'), 27):  # Q or ESC
                break
            elif key == ord(' '):  # SPACE - capture and analyze
                print("\n📸 Analiza klatki...")
                _, jpeg = cv2.imencode('.jpg', frame)
                analysis = service.analyze_frame(jpeg.tobytes())
                if analysis["detected"]:
                    print(f"   ✅ Wykryto: {analysis['doc_type']} ({analysis['confidence']:.0%})")
                else:
                    print("   ❌ Nie wykryto dokumentu")
            elif key == ord('s'):  # S - save frame
                filename = f"/tmp/scan_{int(time.time())}.jpg"
                cv2.imwrite(filename, frame)
                print(f"   💾 Zapisano: {filename}")

        cap.release()
        cv2.destroyAllWindows()

    else:  # screen
        print("\n📺 Podgląd ekranu (odświeżanie co 1s)")
        print("   Naciśnij Q lub ESC aby zakończyć\n")

        while True:
            image_bytes = service.capture_screen()
            if image_bytes:
                # Convert to OpenCV format
                nparr = np.frombuffer(image_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Resize for display
                    h, w = frame.shape[:2]
                    max_width = 1280
                    if w > max_width:
                        scale = max_width / w
                        frame = cv2.resize(frame, (int(w * scale), int(h * scale)))

                    cv2.imshow("Streamware Accounting Preview (Q=quit, SPACE=capture)", frame)

            key = cv2.waitKey(1000) & 0xFF  # 1 second refresh
            if key in (ord('q'), 27):
                break
            elif key == ord(' '):
                if image_bytes:
                    print("\n📸 Analiza klatki...")
                    analysis = service.analyze_frame(image_bytes)
                    if analysis["detected"]:
                        print(f"   ✅ Wykryto: {analysis['doc_type']} ({analysis['confidence']:.0%})")
                    else:
                        print("   ❌ Nie wykryto dokumentu")

        cv2.destroyAllWindows()

    print("\n✅ Podgląd zakończony")


def run_accounting_web(project: str = "web_archive", port: int = 8088, open_browser: bool = True,
                       source: str = "screen", camera_device: int = 0, rtsp_url: str = None,
                       low_latency: bool = True, doc_types: List[str] = None, detect_mode: str = "auto"):
    """Start accounting web service.
    
    Args:
        doc_types: List of document types to detect ['receipt', 'invoice', 'document']
        detect_mode: Detection mode - 'fast', 'accurate', or 'auto'
    """
    # Find free port if default is busy
    actual_port = find_free_port(port)
    if actual_port != port:
        print(f"⚠️  Port {port} zajęty, używam {actual_port}")

    # Show detection mode
    if doc_types:
        print(f"🎯 Tryb wykrywania: {', '.join(doc_types)} ({detect_mode})")
    
    service = AccountingWebService(
        project_name=project, 
        port=actual_port, 
        open_browser=open_browser,
        source=source,
        camera_device=camera_device,
        rtsp_url=rtsp_url,
        low_latency=low_latency,
        doc_types=doc_types,
        detect_mode=detect_mode
    )
    service.run()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Accounting Web Service")
    parser.add_argument("--project", "-p", default="web_archive", help="Project name")
    parser.add_argument("--port", type=int, default=8080, help="Port number")

    args = parser.parse_args()
    run_accounting_web(args.project, args.port)
