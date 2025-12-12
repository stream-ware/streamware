"""
Document Detectors Module

Provides specialized visual detection for different document types.
Uses computer vision to detect receipts, invoices, and general documents.
"""

import numpy as np
from typing import Dict, Any, Optional, List

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from .scanner_config import get_config, get_detection_thresholds


class BaseDetector:
    """Base class for document detectors."""
    
    def __init__(self):
        self.config = get_config()
        self.thresholds = get_detection_thresholds()
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect document in frame. Override in subclasses."""
        raise NotImplementedError


class ReceiptDetector(BaseDetector):
    """Specialized receipt/paragon detector."""
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect receipt-specific features:
        1. Tall narrow shape (thermal receipt)
        2. Text line patterns (horizontal lines)
        3. White/bright paper background
        """
        result = {
            "detected": False,
            "confidence": 0.0,
            "document_type": "paragon",
            "features": [],
            "bbox": None,
        }
        
        if frame is None or not HAS_CV2:
            return result
        
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Adaptive threshold for paper detection
        thresh_adaptive = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Simple threshold
        _, thresh_simple = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        
        # Combine thresholds
        thresh = cv2.bitwise_or(thresh_adaptive, thresh_simple)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        best_score = 0
        best_bbox = None
        best_features = []
        
        area_min = self.thresholds["receipt_area_min"]
        aspect_min = self.thresholds["receipt_aspect_ratio_min"]
        brightness_min = self.thresholds["receipt_brightness_min"]
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < (h * w * area_min):
                continue
            
            x, y, cw, ch = cv2.boundingRect(contour)
            aspect = ch / cw if cw > 0 else 0
            area_ratio = area / (h * w)
            
            score = 0
            features = []
            
            # Feature 1: Tall narrow shape
            if aspect > 1.5:
                score += 0.4
                features.append("tall_narrow")
            elif aspect > aspect_min:
                score += 0.2
                features.append("vertical")
            
            # Feature 2: Large area coverage
            if area_ratio > 0.15:
                score += 0.2
                features.append("large_area")
            
            # Feature 3: Text lines detection
            roi = gray[y:y+ch, x:x+cw]
            if roi.size > 0:
                sobel_h = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=3)
                h_lines = np.sum(np.abs(sobel_h) > 30) / roi.size
                if h_lines > 0.05:
                    score += 0.3
                    features.append("text_lines")
            
            # Feature 4: Bright paper
            if roi.size > 0:
                mean_brightness = np.mean(roi)
                if mean_brightness > brightness_min:
                    score += 0.1
                    features.append("bright_paper")
            
            if score > best_score:
                best_score = score
                best_bbox = (x, y, cw, ch)
                best_features = features
        
        if best_score > 0.3:
            result["detected"] = True
            result["confidence"] = min(1.0, best_score)
            result["bbox"] = best_bbox
            result["features"] = best_features
        
        return result


class InvoiceDetector(BaseDetector):
    """Specialized invoice/faktura detector."""
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Detect invoice-specific features:
        1. A4/Letter aspect ratio (~1.41)
        2. Rectangular shape (4 corners)
        3. Structured content layout
        """
        result = {
            "detected": False,
            "confidence": 0.0,
            "document_type": "faktura",
            "features": [],
            "bbox": None,
        }
        
        if frame is None or not HAS_CV2:
            return result
        
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        aspect_min = self.thresholds["invoice_aspect_ratio_min"]
        aspect_max = self.thresholds["invoice_aspect_ratio_max"]
        area_min = self.thresholds["invoice_area_min"]
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < (h * w * area_min):
                continue
            
            x, y, cw, ch = cv2.boundingRect(contour)
            aspect = ch / cw if cw > 0 else 0
            
            score = 0
            features = []
            
            # Feature 1: A4 aspect ratio
            if aspect_min <= aspect <= aspect_max:
                score += 0.4
                features.append("a4_format")
            elif 0.7 <= aspect <= 0.85:
                score += 0.3
                features.append("a4_landscape")
            
            # Feature 2: Rectangular shape
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                score += 0.2
                features.append("rectangular")
            
            # Feature 3: Structured content
            roi = gray[y:y+ch, x:x+cw]
            if roi.size > 0:
                edges = cv2.Canny(roi, 50, 150)
                edge_density = np.sum(edges > 0) / roi.size
                if 0.03 < edge_density < 0.2:
                    score += 0.2
                    features.append("structured_content")
            
            if score > 0.4:
                result["detected"] = True
                result["confidence"] = min(1.0, score)
                result["bbox"] = (x, y, cw, ch)
                result["features"] = features
                break
        
        return result


class GeneralDocumentDetector(BaseDetector):
    """General document detector using edge detection."""
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect any rectangular document using edge detection."""
        result = {
            "detected": False,
            "confidence": 0.0,
            "document_type": "dokument",
            "features": [],
            "bbox": None,
        }
        
        if frame is None or not HAS_CV2:
            return result
        
        h, w = frame.shape[:2]
        frame_area = h * w
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 30, 100)
        
        kernel = np.ones((5, 5), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=3)
        edges = cv2.erode(edges, kernel, iterations=1)
        
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        area_min = self.thresholds["contour_area_min"]
        area_max = self.thresholds["contour_area_max"]
        
        best_score = 0
        best_bbox = None
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < frame_area * area_min or area > frame_area * area_max:
                continue
            
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if 4 <= len(approx) <= 8:
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
                    best_bbox = (x, y, bw, bh)
        
        # Edge density check
        edge_density = np.sum(edges > 0) / frame_area
        edge_min = self.thresholds["edge_density_min"]
        
        if edge_density > edge_min and best_score < 0.3:
            best_score = max(best_score, 0.4)
            if best_bbox is None:
                best_bbox = (0, 0, w, h)
        
        if best_score > 0.3 and best_bbox:
            result["detected"] = True
            result["confidence"] = best_score
            result["bbox"] = best_bbox
        
        return result


class DocumentDetectorManager:
    """Manages multiple document detectors."""
    
    def __init__(self, doc_types: List[str] = None):
        self.doc_types = doc_types or ["receipt", "invoice", "document"]
        
        self.receipt_detector = ReceiptDetector()
        self.invoice_detector = InvoiceDetector()
        self.general_detector = GeneralDocumentDetector()
    
    def detect(self, frame: np.ndarray) -> Dict[str, Any]:
        """Detect document using appropriate detector based on doc_types."""
        import time
        t_start = time.time()
        
        result = {
            "detected": False,
            "confidence": 0.0,
            "bbox": None,
            "document_type": None,
            "method": None,
            "features": [],
            "timing": {},
        }
        
        if frame is None:
            return result
        
        # Try receipt detection first if enabled
        if "receipt" in self.doc_types or "paragon" in self.doc_types:
            t = time.time()
            r = self.receipt_detector.detect(frame)
            result["timing"]["receipt"] = (time.time() - t) * 1000
            
            if r["detected"] and r["confidence"] > 0.55:
                result.update(r)
                result["method"] = "receipt_detector"
                result["timing"]["total"] = (time.time() - t_start) * 1000
                return result
        
        # Try invoice detection if enabled
        if "invoice" in self.doc_types or "faktura" in self.doc_types:
            t = time.time()
            r = self.invoice_detector.detect(frame)
            result["timing"]["invoice"] = (time.time() - t) * 1000
            
            if r["detected"] and r["confidence"] > 0.55:
                result.update(r)
                result["method"] = "invoice_detector"
                result["timing"]["total"] = (time.time() - t_start) * 1000
                return result
        
        # Fall back to general detection
        t = time.time()
        r = self.general_detector.detect(frame)
        result["timing"]["general"] = (time.time() - t) * 1000
        
        if r["detected"]:
            result.update(r)
            result["method"] = "general_detector"
        
        result["timing"]["total"] = (time.time() - t_start) * 1000
        return result


# Global detector manager
_detector_manager: Optional[DocumentDetectorManager] = None

def get_detector_manager(doc_types: List[str] = None) -> DocumentDetectorManager:
    """Get global detector manager instance."""
    global _detector_manager
    if _detector_manager is None or doc_types:
        _detector_manager = DocumentDetectorManager(doc_types)
    return _detector_manager
