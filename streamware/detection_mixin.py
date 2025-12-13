"""
Detection Mixin Module

Document detection methods for AccountingWebService.
"""

import time
from typing import Dict, Any, Optional, List

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    cv2 = None
    np = None

from .doctr_detector import get_document_detector
from .yolo_manager import get_yolo_manager


class DetectionMixin:
    """Mixin class providing detection methods for AccountingWebService."""
    
    def detect_document_fast(self, frame) -> Dict[str, Any]:
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
        
        if frame is None or not HAS_CV2:
            return result
        
        h, w = frame.shape[:2]
        frame_area = h * w
        
        # Initialize document detector
        if self.document_detector is None:
            self.document_detector = get_document_detector()
        
        # Determine detection order based on doc_types
        detect_receipt = 'receipt' in self.doc_types or 'paragon' in self.doc_types
        detect_invoice = 'invoice' in self.doc_types or 'faktura' in self.doc_types
        
        # SPECIALIZED DETECTION: Receipt mode
        if detect_receipt:
            t_r = time.time()
            receipt_result = self.document_detector.detect_receipt_features(frame)
            result["timing"]["receipt"] = (time.time() - t_r) * 1000
            
            if receipt_result["is_receipt"] and receipt_result["confidence"] > 0.55:
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
            
            if invoice_result["is_invoice"] and invoice_result["confidence"] > 0.55:
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
        
        result["timing"]["total"] = (time.time() - t_start) * 1000
        return result
