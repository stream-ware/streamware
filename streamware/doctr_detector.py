"""
DocTR Document Detector Module

Advanced document detection using DocTR and LayoutParser.
Provides text region detection and document layout analysis.
"""

import numpy as np
from typing import Dict, Any, Optional, Tuple, List

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    from doctr.models import detection_predictor
    HAS_DOCTR = True
except ImportError:
    HAS_DOCTR = False
    detection_predictor = None

try:
    import layoutparser as lp
    HAS_LAYOUTPARSER = True
except ImportError:
    HAS_LAYOUTPARSER = False
    lp = None


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
        
        if frame is None or not HAS_CV2:
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
            except Exception:
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
            except Exception:
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
        
        if frame is None or not HAS_CV2:
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
            if area < (h * w * 0.05):  # At least 5% of frame
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
        
        if frame is None or not HAS_CV2:
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
