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
            result["timing"]["receipt_detect"] = result["timing"]["receipt"]
            
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
            result["timing"]["invoice_detect"] = result["timing"]["invoice"]
            
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
        result["timing"]["opencv_edge"] = result["timing"]["opencv"]
        
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
            t_v = time.time()
            validation = self._validate_opencv_candidate(frame, best_result["bbox"])
            result["timing"]["opencv_validate"] = (time.time() - t_v) * 1000
            result["features"].extend(validation.get("features", []))

            if validation.get("valid"):
                result["detected"] = True
                validation_score = float(validation.get("score", 0.0))
                result["confidence"] = min(1.0, best_score * 0.7 + validation_score * 0.3)
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

    def _validate_opencv_candidate(self, frame, bbox) -> Dict[str, Any]:
        if frame is None or not HAS_CV2 or bbox is None:
            return {"valid": False, "score": 0.0, "features": ["val:skip"]}

        h, w = frame.shape[:2]
        try:
            x, y, bw, bh = bbox
            x = max(0, min(int(x), w - 1))
            y = max(0, min(int(y), h - 1))
            bw = max(1, min(int(bw), w - x))
            bh = max(1, min(int(bh), h - y))
        except Exception:
            return {"valid": False, "score": 0.0, "features": ["val:bbox_err"]}

        roi = frame[y:y + bh, x:x + bw]
        if roi.size == 0:
            return {"valid": False, "score": 0.0, "features": ["val:empty"]}

        margin = int(min(bw, bh) * 0.06)
        if 2 * margin < bw and 2 * margin < bh and margin > 0:
            roi = roi[margin:bh - margin, margin:bw - margin]
            if roi.size == 0:
                return {"valid": False, "score": 0.0, "features": ["val:inner_empty"]}

        max_dim = 520
        rh, rw = roi.shape[:2]
        scale = float(max_dim) / float(max(rh, rw))
        if scale < 1.0:
            roi = cv2.resize(roi, (max(1, int(rw * scale)), max(1, int(rh * scale))), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 60, 180)
        edge_density = float(np.sum(edges > 0)) / float(edges.size)

        b = max(2, int(min(edges.shape[:2]) * 0.07))
        border_mask = np.zeros(edges.shape[:2], dtype=np.uint8)
        border_mask[:b, :] = 1
        border_mask[-b:, :] = 1
        border_mask[:, :b] = 1
        border_mask[:, -b:] = 1

        border_edges = int(np.sum((edges > 0) & (border_mask == 1)))
        inner_edges = int(np.sum((edges > 0) & (border_mask == 0)))
        border_to_inner = float(border_edges) / float(inner_edges + 1)

        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 5
        )
        inv = cv2.bitwise_not(binary)
        inv = cv2.morphologyEx(inv, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)

        text_pixel_ratio = float(np.sum(inv > 0)) / float(inv.size)

        try:
            n_labels, _, stats, _ = cv2.connectedComponentsWithStats(inv, connectivity=8)
            small_cc = 0
            for i in range(1, int(n_labels)):
                area = int(stats[i, cv2.CC_STAT_AREA])
                if 12 <= area <= 900:
                    small_cc += 1
            small_cc_density = float(small_cc) / (float(inv.size) / 10000.0 + 1e-6)
        except Exception:
            small_cc = 0
            small_cc_density = 0.0

        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mean_s = float(np.mean(hsv[:, :, 1]))
        mean_v = float(np.mean(hsv[:, :, 2]))

        score = 0.0

        if edge_density >= 0.012:
            score += 0.22
        elif edge_density >= 0.007:
            score += 0.12

        if text_pixel_ratio >= 0.018:
            score += 0.33
        elif text_pixel_ratio >= 0.010:
            score += 0.20
        elif text_pixel_ratio >= 0.006:
            score += 0.12

        if small_cc_density >= 6.0:
            score += 0.25
        elif small_cc_density >= 3.0:
            score += 0.15

        if mean_s <= 95:
            score += 0.10
        if mean_v >= 105:
            score += 0.10

        if border_to_inner >= 6.0 and edge_density < 0.012:
            score -= 0.22
        if mean_s >= 150:
            score -= 0.20

        score = max(0.0, min(1.0, score))
        valid = score >= 0.45

        features = [
            f"val:{'ok' if valid else 'reject'}",
            f"val_s:{mean_s:.0f}",
            f"val_v:{mean_v:.0f}",
            f"val_ed:{edge_density:.3f}",
            f"val_txt:{text_pixel_ratio:.3f}",
            f"val_cc:{small_cc}",
            f"val_bi:{border_to_inner:.1f}",
        ]

        return {"valid": valid, "score": score, "features": features}
