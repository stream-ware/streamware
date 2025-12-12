"""
Accounting Component for Streamware - Document Scanning, OCR, Invoice Processing

Moduł księgowy do skanowania dokumentów, analizy faktur i paragonów,
zarządzania projektami księgowymi.

Features:
    - OCR z wieloma silnikami (tesseract, easyocr, paddleocr, doctr)
    - Rozpoznawanie typu dokumentu (faktura, paragon, umowa)
    - Ekstrakcja danych z faktur (NIP, kwoty, daty)
    - Interaktywne skanowanie z kamery
    - Porównywanie jakości zrzutów
    - Zarządzanie projektami księgowymi
    - Zapis/odczyt danych do plików

Usage:
    sq accounting scan --source camera --project faktury_2024
    sq accounting analyze --file faktura.jpg --type invoice
    sq accounting summary --project paragony_grudzien
    sq accounting interactive --project faktury
"""

import base64
import csv
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterator

from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class DocumentInfo:
    """Information about a scanned document."""
    id: str
    type: str  # invoice, receipt, contract, other
    file_path: Path
    scan_date: datetime
    ocr_text: str
    ocr_engine: str
    confidence: float
    extracted_data: Dict = field(default_factory=dict)
    quality_score: float = 0.0
    thumbnail_path: Optional[Path] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "file_path": str(self.file_path),
            "scan_date": self.scan_date.isoformat(),
            "ocr_text": self.ocr_text,
            "ocr_engine": self.ocr_engine,
            "confidence": self.confidence,
            "extracted_data": self.extracted_data,
            "quality_score": self.quality_score,
            "thumbnail_path": str(self.thumbnail_path) if self.thumbnail_path else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DocumentInfo":
        return cls(
            id=data["id"],
            type=data["type"],
            file_path=Path(data["file_path"]),
            scan_date=datetime.fromisoformat(data["scan_date"]),
            ocr_text=data["ocr_text"],
            ocr_engine=data["ocr_engine"],
            confidence=data["confidence"],
            extracted_data=data.get("extracted_data", {}),
            quality_score=data.get("quality_score", 0.0),
            thumbnail_path=Path(data["thumbnail_path"]) if data.get("thumbnail_path") else None,
        )


@dataclass
class AccountingProject:
    """Accounting project with documents."""
    name: str
    path: Path
    created: datetime
    documents: List[DocumentInfo] = field(default_factory=list)
    settings: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "path": str(self.path),
            "created": self.created.isoformat(),
            "documents": [d.to_dict() for d in self.documents],
            "settings": self.settings,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AccountingProject":
        return cls(
            name=data["name"],
            path=Path(data["path"]),
            created=datetime.fromisoformat(data["created"]),
            documents=[DocumentInfo.from_dict(d) for d in data.get("documents", [])],
            settings=data.get("settings", {}),
        )


@dataclass
class InvoiceData:
    """Extracted invoice data."""
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    seller_name: Optional[str] = None
    seller_nip: Optional[str] = None
    seller_address: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_nip: Optional[str] = None
    buyer_address: Optional[str] = None
    net_amount: Optional[float] = None
    vat_amount: Optional[float] = None
    gross_amount: Optional[float] = None
    currency: str = "PLN"
    items: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "invoice_number": self.invoice_number,
            "invoice_date": self.invoice_date,
            "due_date": self.due_date,
            "seller": {
                "name": self.seller_name,
                "nip": self.seller_nip,
                "address": self.seller_address,
            },
            "buyer": {
                "name": self.buyer_name,
                "nip": self.buyer_nip,
                "address": self.buyer_address,
            },
            "amounts": {
                "net": self.net_amount,
                "vat": self.vat_amount,
                "gross": self.gross_amount,
                "currency": self.currency,
            },
            "items": self.items,
        }


@dataclass
class ReceiptData:
    """Extracted receipt data."""
    store_name: Optional[str] = None
    store_address: Optional[str] = None
    store_nip: Optional[str] = None
    receipt_date: Optional[str] = None
    receipt_time: Optional[str] = None
    receipt_number: Optional[str] = None
    total_amount: Optional[float] = None
    payment_method: Optional[str] = None
    items: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "store": {
                "name": self.store_name,
                "address": self.store_address,
                "nip": self.store_nip,
            },
            "receipt_date": self.receipt_date,
            "receipt_time": self.receipt_time,
            "receipt_number": self.receipt_number,
            "total_amount": self.total_amount,
            "payment_method": self.payment_method,
            "items": self.items,
        }


# ============================================================================
# OCR Engines
# ============================================================================

class OCREngine:
    """Base OCR engine interface."""
    
    name = "base"
    
    def extract_text(self, image_path: Path, lang: str = "pol") -> Tuple[str, float, List[Dict]]:
        """Extract text from image. Returns (text, confidence, boxes)."""
        raise NotImplementedError
    
    @staticmethod
    def is_available() -> bool:
        """Check if engine is available."""
        return False


class TesseractOCR(OCREngine):
    """Tesseract OCR engine - best for printed documents."""
    
    name = "tesseract"
    
    def extract_text(self, image_path: Path, lang: str = "pol") -> Tuple[str, float, List[Dict]]:
        try:
            result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", lang, "--psm", "3"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                text = result.stdout.strip()
                confidence = 0.85 if text else 0.0
                return text, confidence, []
        except FileNotFoundError:
            logger.warning("Tesseract not found. Install: sudo apt install tesseract-ocr tesseract-ocr-pol")
        except Exception as e:
            logger.debug(f"Tesseract error: {e}")
        
        return "", 0.0, []
    
    @staticmethod
    def is_available() -> bool:
        try:
            subprocess.run(["tesseract", "--version"], capture_output=True, timeout=5)
            return True
        except:
            return False


class EasyOCR_Engine(OCREngine):
    """EasyOCR engine - good for mixed content, handwriting."""
    
    name = "easyocr"
    _reader = None
    
    def extract_text(self, image_path: Path, lang: str = "pol") -> Tuple[str, float, List[Dict]]:
        try:
            import easyocr
            
            lang_map = {"pol": "pl", "eng": "en", "deu": "de"}
            ocr_lang = lang_map.get(lang, lang)
            
            if EasyOCR_Engine._reader is None:
                EasyOCR_Engine._reader = easyocr.Reader([ocr_lang, "en"], gpu=False)
            
            results = EasyOCR_Engine._reader.readtext(str(image_path))
            
            if results:
                text = " ".join([r[1] for r in results])
                avg_conf = sum(r[2] for r in results) / len(results)
                boxes = [{"box": r[0], "text": r[1], "conf": r[2]} for r in results]
                return text, avg_conf, boxes
                
        except ImportError:
            logger.warning("EasyOCR not installed. Install: pip install easyocr")
        except Exception as e:
            logger.debug(f"EasyOCR error: {e}")
        
        return "", 0.0, []
    
    @staticmethod
    def is_available() -> bool:
        try:
            import easyocr
            return True
        except ImportError:
            return False


class PaddleOCR_Engine(OCREngine):
    """PaddleOCR engine - excellent for structured documents."""
    
    name = "paddleocr"
    _ocr = None
    
    def extract_text(self, image_path: Path, lang: str = "pol") -> Tuple[str, float, List[Dict]]:
        try:
            from paddleocr import PaddleOCR
            
            lang_map = {"pol": "pl", "eng": "en", "deu": "german"}
            ocr_lang = lang_map.get(lang, "en")
            
            if PaddleOCR_Engine._ocr is None:
                PaddleOCR_Engine._ocr = PaddleOCR(use_angle_cls=True, lang=ocr_lang, show_log=False)
            
            results = PaddleOCR_Engine._ocr.ocr(str(image_path), cls=True)
            
            if results and results[0]:
                texts = []
                confidences = []
                boxes = []
                
                for line in results[0]:
                    if line[1]:
                        texts.append(line[1][0])
                        confidences.append(line[1][1])
                        boxes.append({"box": line[0], "text": line[1][0], "conf": line[1][1]})
                
                text = " ".join(texts)
                avg_conf = sum(confidences) / len(confidences) if confidences else 0
                return text, avg_conf, boxes
                
        except ImportError:
            logger.warning("PaddleOCR not installed. Install: pip install paddleocr")
        except Exception as e:
            logger.debug(f"PaddleOCR error: {e}")
        
        return "", 0.0, []
    
    @staticmethod
    def is_available() -> bool:
        try:
            from paddleocr import PaddleOCR
            return True
        except ImportError:
            return False


class DocTROCR(OCREngine):
    """DocTR OCR engine - best for document layout understanding."""
    
    name = "doctr"
    _model = None
    
    def extract_text(self, image_path: Path, lang: str = "pol") -> Tuple[str, float, List[Dict]]:
        try:
            from doctr.io import DocumentFile
            from doctr.models import ocr_predictor
            
            if DocTROCR._model is None:
                DocTROCR._model = ocr_predictor(pretrained=True)
            
            doc = DocumentFile.from_images(str(image_path))
            result = DocTROCR._model(doc)
            
            texts = []
            confidences = []
            boxes = []
            
            for page in result.pages:
                for block in page.blocks:
                    for line in block.lines:
                        line_text = " ".join([word.value for word in line.words])
                        line_conf = sum(word.confidence for word in line.words) / len(line.words) if line.words else 0
                        texts.append(line_text)
                        confidences.append(line_conf)
            
            text = "\n".join(texts)
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            return text, avg_conf, boxes
            
        except ImportError:
            logger.warning("DocTR not installed. Install: pip install python-doctr")
        except Exception as e:
            logger.debug(f"DocTR error: {e}")
        
        return "", 0.0, []
    
    @staticmethod
    def is_available() -> bool:
        try:
            from doctr.models import ocr_predictor
            return True
        except ImportError:
            return False


# OCR engine registry
OCR_ENGINES = {
    "tesseract": TesseractOCR,
    "easyocr": EasyOCR_Engine,
    "paddleocr": PaddleOCR_Engine,
    "doctr": DocTROCR,
}


def get_best_ocr_engine() -> OCREngine:
    """Get the best available OCR engine for documents."""
    priority = ["paddleocr", "doctr", "easyocr", "tesseract"]
    
    for engine_name in priority:
        engine_class = OCR_ENGINES.get(engine_name)
        if engine_class and engine_class.is_available():
            return engine_class()
    
    return TesseractOCR()


def get_available_engines() -> List[str]:
    """Get list of available OCR engines."""
    return [name for name, cls in OCR_ENGINES.items() if cls.is_available()]


# ============================================================================
# Document Analysis
# ============================================================================

class DocumentAnalyzer:
    """Analyze and classify documents."""
    
    DOCUMENT_PATTERNS = {
        "invoice": [
            r"faktura\s*(vat)?",
            r"invoice",
            r"nr\s*faktury",
            r"netto|brutto|vat",
            r"sprzedawca|nabywca",
            r"do\s*zap[łl]aty",
        ],
        "receipt": [
            r"paragon\s*(fiskalny)?",
            r"receipt",
            r"suma|razem|total",
            r"gotówka|karta|płatność",
            r"nr\s*kasy",
            r"sprzeda[żz]",
        ],
        "contract": [
            r"umowa",
            r"contract",
            r"strony\s*umowy",
            r"§\s*\d+",
            r"postanowienia",
        ],
    }
    
    NIP_PATTERN = r"\b\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}\b|\b\d{10}\b"
    AMOUNT_PATTERN = r"\b\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{2})?\s*(?:zł|PLN|EUR|USD)?\b"
    DATE_PATTERN = r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b"
    
    @classmethod
    def classify_document(cls, text: str) -> str:
        """Classify document type based on text content."""
        text_lower = text.lower()
        
        scores = {}
        for doc_type, patterns in cls.DOCUMENT_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, text_lower, re.IGNORECASE))
            scores[doc_type] = score
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        
        return "other"
    
    @classmethod
    def extract_invoice_data(cls, text: str) -> InvoiceData:
        """Extract data from invoice text."""
        data = InvoiceData()
        
        nips = re.findall(cls.NIP_PATTERN, text)
        if len(nips) >= 1:
            data.seller_nip = nips[0].replace("-", "").replace(" ", "")
        if len(nips) >= 2:
            data.buyer_nip = nips[1].replace("-", "").replace(" ", "")
        
        dates = re.findall(cls.DATE_PATTERN, text)
        if dates:
            data.invoice_date = dates[0]
            if len(dates) >= 2:
                data.due_date = dates[1]
        
        invoice_match = re.search(r"(?:faktura|invoice|nr)[:\s]*([A-Z0-9/\-]+)", text, re.IGNORECASE)
        if invoice_match:
            data.invoice_number = invoice_match.group(1).strip()
        
        amounts = re.findall(r"(\d{1,3}(?:[\s,]\d{3})*(?:[.,]\d{2}))", text)
        if amounts:
            parsed_amounts = []
            for a in amounts:
                try:
                    clean = a.replace(" ", "").replace(",", ".")
                    parsed_amounts.append(float(clean))
                except:
                    pass
            
            if parsed_amounts:
                data.gross_amount = max(parsed_amounts)
        
        return data
    
    @classmethod
    def extract_receipt_data(cls, text: str) -> ReceiptData:
        """Extract data from receipt text."""
        data = ReceiptData()
        
        nips = re.findall(cls.NIP_PATTERN, text)
        if nips:
            data.store_nip = nips[0].replace("-", "").replace(" ", "")
        
        dates = re.findall(cls.DATE_PATTERN, text)
        if dates:
            data.receipt_date = dates[0]
        
        time_match = re.search(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b", text)
        if time_match:
            data.receipt_time = time_match.group(1)
        
        total_patterns = [
            r"(?:suma|razem|total|do\s*zap[łl]aty)[:\s]*(\d{1,3}(?:[.,]\d{2})?)",
            r"(\d{1,3}(?:[.,]\d{2}))\s*(?:zł|PLN)",
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    data.total_amount = float(match.group(1).replace(",", "."))
                    break
                except:
                    pass
        
        return data


# ============================================================================
# Image Quality Assessment
# ============================================================================

class ImageQualityAssessor:
    """Assess image quality for OCR."""
    
    @staticmethod
    def calculate_quality_score(image_path: Path) -> float:
        """Calculate quality score (0-1) for an image."""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(str(image_path))
            if img is None:
                return 0.0
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 500, 1.0)
            
            brightness = np.mean(gray)
            brightness_score = 1.0 - abs(brightness - 127) / 127
            
            contrast = np.std(gray)
            contrast_score = min(contrast / 80, 1.0)
            
            height, width = gray.shape
            resolution_score = min((height * width) / (1920 * 1080), 1.0)
            
            quality_score = (
                sharpness_score * 0.4 +
                brightness_score * 0.2 +
                contrast_score * 0.2 +
                resolution_score * 0.2
            )
            
            return quality_score
            
        except ImportError:
            logger.warning("OpenCV not available for quality assessment")
            return 0.5
        except Exception as e:
            logger.debug(f"Quality assessment error: {e}")
            return 0.5
    
    @staticmethod
    def select_best_image(image_paths: List[Path]) -> Optional[Path]:
        """Select the best quality image from a list."""
        if not image_paths:
            return None
        
        scores = [(path, ImageQualityAssessor.calculate_quality_score(path)) for path in image_paths]
        scores.sort(key=lambda x: x[1], reverse=True)
        
        return scores[0][0]
    
    @staticmethod
    def preprocess_for_ocr(image_path: Path, output_path: Optional[Path] = None) -> Path:
        """Preprocess image for better OCR results."""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(str(image_path))
            if img is None:
                return image_path
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            if output_path is None:
                output_path = image_path.parent / f"{image_path.stem}_processed{image_path.suffix}"
            
            cv2.imwrite(str(output_path), binary)
            return output_path
            
        except ImportError:
            return image_path
        except Exception as e:
            logger.debug(f"Preprocessing error: {e}")
            return image_path


# ============================================================================
# Document Cropping
# ============================================================================

class DocumentCropper:
    """Detect and crop document from image."""
    
    @staticmethod
    def detect_document_edges(image_path: Path) -> Optional[List[Tuple[int, int]]]:
        """Detect document edges in image."""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(str(image_path))
            if img is None:
                return None
            
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            largest_contour = max(contours, key=cv2.contourArea)
            
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            if len(approx) == 4:
                return [(p[0][0], p[0][1]) for p in approx]
            
            return None
            
        except ImportError:
            return None
        except Exception as e:
            logger.debug(f"Edge detection error: {e}")
            return None
    
    @staticmethod
    def crop_document(image_path: Path, output_path: Optional[Path] = None) -> Path:
        """Crop document from image using perspective transform."""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(str(image_path))
            if img is None:
                return image_path
            
            edges = DocumentCropper.detect_document_edges(image_path)
            if edges is None or len(edges) != 4:
                return image_path
            
            pts = np.array(edges, dtype=np.float32)
            
            rect = np.zeros((4, 2), dtype=np.float32)
            s = pts.sum(axis=1)
            rect[0] = pts[np.argmin(s)]
            rect[2] = pts[np.argmax(s)]
            diff = np.diff(pts, axis=1)
            rect[1] = pts[np.argmin(diff)]
            rect[3] = pts[np.argmax(diff)]
            
            width = max(
                np.linalg.norm(rect[0] - rect[1]),
                np.linalg.norm(rect[2] - rect[3])
            )
            height = max(
                np.linalg.norm(rect[0] - rect[3]),
                np.linalg.norm(rect[1] - rect[2])
            )
            
            dst = np.array([
                [0, 0],
                [width - 1, 0],
                [width - 1, height - 1],
                [0, height - 1]
            ], dtype=np.float32)
            
            matrix = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(img, matrix, (int(width), int(height)))
            
            if output_path is None:
                output_path = image_path.parent / f"{image_path.stem}_cropped{image_path.suffix}"
            
            cv2.imwrite(str(output_path), warped)
            return output_path
            
        except ImportError:
            return image_path
        except Exception as e:
            logger.debug(f"Cropping error: {e}")
            return image_path


# ============================================================================
# Project Manager
# ============================================================================

class AccountingProjectManager:
    """Manage accounting projects and documents."""
    
    DEFAULT_BASE_PATH = Path.home() / ".streamware" / "accounting"
    
    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or self.DEFAULT_BASE_PATH
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.projects_file = self.base_path / "projects.json"
        self._load_projects()
    
    def _load_projects(self):
        """Load projects from disk."""
        self.projects: Dict[str, AccountingProject] = {}
        
        if self.projects_file.exists():
            try:
                with open(self.projects_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, proj_data in data.items():
                        self.projects[name] = AccountingProject.from_dict(proj_data)
            except Exception as e:
                logger.error(f"Error loading projects: {e}")
    
    def _save_projects(self):
        """Save projects to disk."""
        try:
            data = {name: proj.to_dict() for name, proj in self.projects.items()}
            with open(self.projects_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving projects: {e}")
    
    def create_project(self, name: str, settings: Optional[Dict] = None) -> AccountingProject:
        """Create a new accounting project."""
        if name in self.projects:
            return self.projects[name]
        
        project_path = self.base_path / name
        project_path.mkdir(parents=True, exist_ok=True)
        
        (project_path / "scans").mkdir(exist_ok=True)
        (project_path / "processed").mkdir(exist_ok=True)
        (project_path / "exports").mkdir(exist_ok=True)
        
        project = AccountingProject(
            name=name,
            path=project_path,
            created=datetime.now(),
            settings=settings or {},
        )
        
        self.projects[name] = project
        self._save_projects()
        
        return project
    
    def get_project(self, name: str) -> Optional[AccountingProject]:
        """Get project by name."""
        return self.projects.get(name)
    
    def list_projects(self) -> List[str]:
        """List all project names."""
        return list(self.projects.keys())
    
    def add_document(self, project_name: str, document: DocumentInfo) -> bool:
        """Add document to project."""
        project = self.get_project(project_name)
        if not project:
            return False
        
        project.documents.append(document)
        self._save_projects()
        return True
    
    def get_summary(self, project_name: str) -> Dict:
        """Get project summary with totals."""
        project = self.get_project(project_name)
        if not project:
            return {}
        
        summary = {
            "project_name": project_name,
            "total_documents": len(project.documents),
            "by_type": {},
            "total_amounts": {
                "invoices": 0.0,
                "receipts": 0.0,
            },
            "documents": [],
        }
        
        for doc in project.documents:
            doc_type = doc.type
            summary["by_type"][doc_type] = summary["by_type"].get(doc_type, 0) + 1
            
            if doc_type == "invoice" and doc.extracted_data:
                amount = doc.extracted_data.get("amounts", {}).get("gross", 0) or 0
                summary["total_amounts"]["invoices"] += amount
            elif doc_type == "receipt" and doc.extracted_data:
                amount = doc.extracted_data.get("total_amount", 0) or 0
                summary["total_amounts"]["receipts"] += amount
            
            summary["documents"].append({
                "id": doc.id,
                "type": doc.type,
                "date": doc.scan_date.isoformat(),
                "amount": doc.extracted_data.get("amounts", {}).get("gross") or doc.extracted_data.get("total_amount"),
            })
        
        return summary
    
    def export_to_csv(self, project_name: str, output_path: Optional[Path] = None) -> Path:
        """Export project documents to CSV."""
        project = self.get_project(project_name)
        if not project:
            raise ComponentError(f"Project not found: {project_name}")
        
        if output_path is None:
            output_path = project.path / "exports" / f"{project_name}_{datetime.now().strftime('%Y%m%d')}.csv"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Typ", "Data skanu", "Numer", "Data dokumentu",
                "NIP sprzedawcy", "Kwota netto", "VAT", "Kwota brutto"
            ])
            
            for doc in project.documents:
                data = doc.extracted_data
                
                if doc.type == "invoice":
                    writer.writerow([
                        doc.id,
                        "Faktura",
                        doc.scan_date.strftime("%Y-%m-%d"),
                        data.get("invoice_number", ""),
                        data.get("invoice_date", ""),
                        data.get("seller", {}).get("nip", ""),
                        data.get("amounts", {}).get("net", ""),
                        data.get("amounts", {}).get("vat", ""),
                        data.get("amounts", {}).get("gross", ""),
                    ])
                elif doc.type == "receipt":
                    writer.writerow([
                        doc.id,
                        "Paragon",
                        doc.scan_date.strftime("%Y-%m-%d"),
                        data.get("receipt_number", ""),
                        data.get("receipt_date", ""),
                        data.get("store", {}).get("nip", ""),
                        "",
                        "",
                        data.get("total_amount", ""),
                    ])
        
        return output_path


# ============================================================================
# Interactive Scanner
# ============================================================================

class InteractiveScanner:
    """Interactive document scanning with camera."""
    
    def __init__(self, project_manager: AccountingProjectManager, project_name: str):
        self.manager = project_manager
        self.project_name = project_name
        self.project = project_manager.get_project(project_name) or project_manager.create_project(project_name)
        self.ocr_engine = get_best_ocr_engine()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.capture_count = 0
    
    def capture_from_camera(self, device: str = "/dev/video0") -> Optional[Path]:
        """Capture image from camera."""
        self.capture_count += 1
        output_path = self.temp_dir / f"capture_{self.capture_count:04d}.jpg"
        
        try:
            cmd = [
                "ffmpeg", "-y",
                "-f", "v4l2",
                "-i", device,
                "-vframes", "1",
                "-q:v", "2",
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if output_path.exists():
                return output_path
                
        except Exception as e:
            logger.debug(f"Camera capture error: {e}")
        
        return None
    
    def capture_from_screen(self) -> Optional[Path]:
        """Capture screenshot."""
        self.capture_count += 1
        output_path = self.temp_dir / f"screen_{self.capture_count:04d}.png"
        
        try:
            tools = [
                ["gnome-screenshot", "-f", str(output_path)],
                ["scrot", str(output_path)],
                ["import", "-window", "root", str(output_path)],
            ]
            
            for cmd in tools:
                try:
                    subprocess.run(cmd, capture_output=True, timeout=5)
                    if output_path.exists():
                        return output_path
                except FileNotFoundError:
                    continue
                    
        except Exception as e:
            logger.debug(f"Screen capture error: {e}")
        
        return None
    
    def capture_multiple_and_select_best(self, source: str = "camera", count: int = 3) -> Optional[Path]:
        """Capture multiple images and select the best quality one."""
        captures = []
        
        for i in range(count):
            if source == "camera":
                path = self.capture_from_camera()
            else:
                path = self.capture_from_screen()
            
            if path:
                captures.append(path)
            
            time.sleep(0.5)
        
        if not captures:
            return None
        
        return ImageQualityAssessor.select_best_image(captures)
    
    def process_document(self, image_path: Path, auto_crop: bool = True) -> DocumentInfo:
        """Process a captured document image."""
        doc_id = hashlib.md5(f"{image_path}{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        processed_path = image_path
        if auto_crop:
            processed_path = DocumentCropper.crop_document(image_path)
        
        processed_path = ImageQualityAssessor.preprocess_for_ocr(processed_path)
        
        text, confidence, boxes = self.ocr_engine.extract_text(processed_path, lang="pol")
        
        doc_type = DocumentAnalyzer.classify_document(text)
        
        if doc_type == "invoice":
            extracted_data = DocumentAnalyzer.extract_invoice_data(text).to_dict()
        elif doc_type == "receipt":
            extracted_data = DocumentAnalyzer.extract_receipt_data(text).to_dict()
        else:
            extracted_data = {}
        
        final_path = self.project.path / "scans" / f"{doc_id}_{doc_type}.jpg"
        shutil.copy(processed_path, final_path)
        
        quality_score = ImageQualityAssessor.calculate_quality_score(final_path)
        
        doc_info = DocumentInfo(
            id=doc_id,
            type=doc_type,
            file_path=final_path,
            scan_date=datetime.now(),
            ocr_text=text,
            ocr_engine=self.ocr_engine.name,
            confidence=confidence,
            extracted_data=extracted_data,
            quality_score=quality_score,
        )
        
        self.manager.add_document(self.project_name, doc_info)
        
        return doc_info
    
    def run_interactive_session(self, source: str = "camera", tts_enabled: bool = False):
        """Run interactive scanning session."""
        print(f"\n📋 Interaktywne skanowanie dokumentów")
        print(f"   Projekt: {self.project_name}")
        print(f"   Źródło: {source}")
        print(f"   OCR: {self.ocr_engine.name}")
        print(f"\nKomendy:")
        print("   [Enter] - Zeskanuj dokument")
        print("   [q] - Zakończ")
        print("   [s] - Pokaż podsumowanie")
        print("   [e] - Eksportuj do CSV")
        print("-" * 40)
        
        while True:
            try:
                cmd = input("\n🔍 Pokaż dokument i naciśnij Enter (q=koniec): ").strip().lower()
                
                if cmd == "q":
                    break
                elif cmd == "s":
                    summary = self.manager.get_summary(self.project_name)
                    print(f"\n📊 Podsumowanie projektu: {self.project_name}")
                    print(f"   Dokumenty: {summary.get('total_documents', 0)}")
                    print(f"   Faktury: {summary.get('by_type', {}).get('invoice', 0)}")
                    print(f"   Paragony: {summary.get('by_type', {}).get('receipt', 0)}")
                    print(f"   Suma faktur: {summary.get('total_amounts', {}).get('invoices', 0):.2f} PLN")
                    print(f"   Suma paragonów: {summary.get('total_amounts', {}).get('receipts', 0):.2f} PLN")
                    continue
                elif cmd == "e":
                    csv_path = self.manager.export_to_csv(self.project_name)
                    print(f"   ✅ Eksportowano do: {csv_path}")
                    continue
                
                print("   📸 Robię zdjęcie...")
                
                image_path = self.capture_multiple_and_select_best(source, count=3)
                
                if not image_path:
                    print("   ❌ Nie udało się zrobić zdjęcia")
                    continue
                
                print("   🔄 Przetwarzam dokument...")
                
                doc_info = self.process_document(image_path)
                
                print(f"\n   ✅ Dokument zeskanowany!")
                print(f"   📄 Typ: {doc_info.type}")
                print(f"   🎯 Pewność OCR: {doc_info.confidence:.0%}")
                print(f"   📊 Jakość obrazu: {doc_info.quality_score:.0%}")
                
                if doc_info.type == "invoice":
                    data = doc_info.extracted_data
                    print(f"   📝 Numer: {data.get('invoice_number', 'N/A')}")
                    print(f"   📅 Data: {data.get('invoice_date', 'N/A')}")
                    print(f"   💰 Kwota: {data.get('amounts', {}).get('gross', 'N/A')} PLN")
                elif doc_info.type == "receipt":
                    data = doc_info.extracted_data
                    print(f"   🏪 Sklep: {data.get('store', {}).get('name', 'N/A')}")
                    print(f"   📅 Data: {data.get('receipt_date', 'N/A')}")
                    print(f"   💰 Suma: {data.get('total_amount', 'N/A')} PLN")
                
                if tts_enabled:
                    self._speak_result(doc_info)
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"   ❌ Błąd: {e}")
        
        print(f"\n📋 Sesja zakończona. Zeskanowano {len(self.project.documents)} dokumentów.")
    
    def _speak_result(self, doc_info: DocumentInfo):
        """Speak scanning result using TTS."""
        try:
            from ..tts_worker_process import get_tts_worker
            
            worker = get_tts_worker(engine="pico", lang="pl")
            
            if doc_info.type == "invoice":
                amount = doc_info.extracted_data.get("amounts", {}).get("gross", "nieznana")
                text = f"Zeskanowano fakturę na kwotę {amount} złotych"
            elif doc_info.type == "receipt":
                amount = doc_info.extracted_data.get("total_amount", "nieznana")
                text = f"Zeskanowano paragon na kwotę {amount} złotych"
            else:
                text = f"Zeskanowano dokument typu {doc_info.type}"
            
            worker.speak(text, voice="pl")
        except Exception as e:
            logger.debug(f"TTS error: {e}")


# ============================================================================
# Main Component
# ============================================================================

@register("accounting")
class AccountingComponent(Component):
    """
    Accounting Component - Document Scanning and Invoice Processing
    
    Operations:
    - scan: Scan document from camera/screen
    - analyze: Analyze document image
    - interactive: Interactive scanning session
    - summary: Get project summary
    - export: Export to CSV
    - list: List projects
    - create: Create new project
    
    URI Examples:
        accounting://scan?source=camera&project=faktury_2024
        accounting://analyze?file=/path/to/invoice.jpg&type=invoice
        accounting://interactive?project=paragony&source=camera
        accounting://summary?project=faktury_2024
        accounting://export?project=faktury_2024&format=csv
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "scan"
        
        self.project_name = uri.get_param("project", "default")
        self.source = uri.get_param("source", "camera")
        self.file_path = uri.get_param("file")
        self.doc_type = uri.get_param("type")
        self.ocr_engine_name = uri.get_param("ocr_engine", "auto")
        self.lang = uri.get_param("lang", "pol")
        
        # Parse boolean params safely
        crop_val = uri.get_param("crop", "true")
        self.auto_crop = crop_val if isinstance(crop_val, bool) else str(crop_val).lower() == "true"
        tts_val = uri.get_param("tts", "false")
        self.tts_enabled = tts_val if isinstance(tts_val, bool) else str(tts_val).lower() == "true"
        
        self.export_format = uri.get_param("format", "csv")
        
        self.manager = AccountingProjectManager()
        
        if self.ocr_engine_name == "auto":
            self.ocr_engine = get_best_ocr_engine()
        else:
            engine_class = OCR_ENGINES.get(self.ocr_engine_name)
            self.ocr_engine = engine_class() if engine_class else get_best_ocr_engine()
    
    def process(self, data: Any) -> Dict:
        """Process accounting operation."""
        operations = {
            "scan": self._scan,
            "analyze": self._analyze,
            "interactive": self._interactive,
            "summary": self._summary,
            "export": self._export,
            "list": self._list_projects,
            "create": self._create_project,
            "engines": self._list_engines,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _scan(self, data: Any) -> Dict:
        """Scan document from source."""
        scanner = InteractiveScanner(self.manager, self.project_name)
        
        if self.source == "camera":
            image_path = scanner.capture_multiple_and_select_best("camera")
        elif self.source == "screen":
            image_path = scanner.capture_multiple_and_select_best("screen")
        elif self.file_path:
            image_path = Path(self.file_path)
        else:
            raise ComponentError("No source specified")
        
        if not image_path or not image_path.exists():
            raise ComponentError("Failed to capture/find image")
        
        doc_info = scanner.process_document(image_path, auto_crop=self.auto_crop)
        
        return {
            "success": True,
            "document": doc_info.to_dict(),
        }
    
    def _analyze(self, data: Any) -> Dict:
        """Analyze document image."""
        if not self.file_path:
            raise ComponentError("File path required")
        
        image_path = Path(self.file_path)
        if not image_path.exists():
            raise ComponentError(f"File not found: {image_path}")
        
        if self.auto_crop:
            image_path = DocumentCropper.crop_document(image_path)
        
        processed_path = ImageQualityAssessor.preprocess_for_ocr(image_path)
        
        text, confidence, boxes = self.ocr_engine.extract_text(processed_path, lang=self.lang)
        
        doc_type = self.doc_type or DocumentAnalyzer.classify_document(text)
        
        if doc_type == "invoice":
            extracted_data = DocumentAnalyzer.extract_invoice_data(text).to_dict()
        elif doc_type == "receipt":
            extracted_data = DocumentAnalyzer.extract_receipt_data(text).to_dict()
        else:
            extracted_data = {}
        
        quality_score = ImageQualityAssessor.calculate_quality_score(image_path)
        
        return {
            "success": True,
            "document_type": doc_type,
            "ocr_engine": self.ocr_engine.name,
            "ocr_text": text,
            "confidence": confidence,
            "quality_score": quality_score,
            "extracted_data": extracted_data,
        }
    
    def _interactive(self, data: Any) -> Dict:
        """Run interactive scanning session."""
        scanner = InteractiveScanner(self.manager, self.project_name)
        scanner.run_interactive_session(source=self.source, tts_enabled=self.tts_enabled)
        
        return self.manager.get_summary(self.project_name)
    
    def _summary(self, data: Any) -> Dict:
        """Get project summary."""
        return self.manager.get_summary(self.project_name)
    
    def _export(self, data: Any) -> Dict:
        """Export project to file."""
        if self.export_format == "csv":
            output_path = self.manager.export_to_csv(self.project_name)
            return {
                "success": True,
                "format": "csv",
                "path": str(output_path),
            }
        else:
            project = self.manager.get_project(self.project_name)
            if not project:
                raise ComponentError(f"Project not found: {self.project_name}")
            
            output_path = project.path / "exports" / f"{self.project_name}_{datetime.now().strftime('%Y%m%d')}.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(project.to_dict(), f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "format": "json",
                "path": str(output_path),
            }
    
    def _list_projects(self, data: Any) -> Dict:
        """List all projects."""
        projects = []
        for name in self.manager.list_projects():
            project = self.manager.get_project(name)
            if project:
                projects.append({
                    "name": name,
                    "documents": len(project.documents),
                    "created": project.created.isoformat(),
                })
        
        return {
            "projects": projects,
        }
    
    def _create_project(self, data: Any) -> Dict:
        """Create new project."""
        project = self.manager.create_project(self.project_name)
        return {
            "success": True,
            "project": {
                "name": project.name,
                "path": str(project.path),
                "created": project.created.isoformat(),
            },
        }
    
    def _list_engines(self, data: Any) -> Dict:
        """List available OCR engines."""
        engines = []
        for name, cls in OCR_ENGINES.items():
            engines.append({
                "name": name,
                "available": cls.is_available(),
                "description": cls.__doc__ or "",
            })
        
        return {
            "engines": engines,
            "recommended": get_best_ocr_engine().name,
        }


# ============================================================================
# Helper Functions
# ============================================================================

def scan_document(
    source: str = "camera",
    project: str = "default",
    ocr_engine: str = "auto",
    lang: str = "pol",
) -> Dict:
    """Quick function to scan a document."""
    from ..core import flow
    uri = f"accounting://scan?source={source}&project={project}&ocr_engine={ocr_engine}&lang={lang}"
    return flow(uri).run()


def analyze_document(
    file_path: str,
    doc_type: Optional[str] = None,
    ocr_engine: str = "auto",
    lang: str = "pol",
) -> Dict:
    """Quick function to analyze a document."""
    from ..core import flow
    uri = f"accounting://analyze?file={file_path}&ocr_engine={ocr_engine}&lang={lang}"
    if doc_type:
        uri += f"&type={doc_type}"
    return flow(uri).run()


def get_project_summary(project: str) -> Dict:
    """Quick function to get project summary."""
    from ..core import flow
    return flow(f"accounting://summary?project={project}").run()


def export_project(project: str, format: str = "csv") -> Dict:
    """Quick function to export project."""
    from ..core import flow
    return flow(f"accounting://export?project={project}&format={format}").run()


def interactive_scan(project: str, source: str = "camera", tts: bool = False) -> Dict:
    """Quick function to start interactive scanning."""
    from ..core import flow
    uri = f"accounting://interactive?project={project}&source={source}"
    if tts:
        uri += "&tts=true"
    return flow(uri).run()


def list_ocr_engines() -> Dict:
    """Quick function to list OCR engines."""
    from ..core import flow
    return flow("accounting://engines").run()


def create_project(name: str) -> Dict:
    """Quick function to create a project."""
    from ..core import flow
    return flow(f"accounting://create?project={name}").run()


def list_projects() -> Dict:
    """Quick function to list projects."""
    from ..core import flow
    return flow("accounting://list").run()
