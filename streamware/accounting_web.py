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

# Import refactored modules
from .scanner_config import get_config, ScannerConfig, get_combined_config
from .document_classifier import get_classifier, DocumentClassifier
from .document_detectors import get_detector_manager, DocumentDetectorManager
from .web_templates import get_scanner_html_template
from .yolo_manager import get_yolo_manager, YOLOModelManager, HAS_YOLO
from .doctr_detector import get_document_detector, DocumentDetector, HAS_DOCTR
from .camera_utils import load_env_config, load_camera_config_from_env, list_available_cameras, find_free_port
from .frame_capture import FrameCaptureMixin
from .scanner_diagnostics import ScannerDiagnosticsMixin
from .detection_mixin import DetectionMixin

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

# Note: HAS_YOLO imported from yolo_manager, HAS_DOCTR from doctr_detector
# Note: load_env_config, list_available_cameras, find_free_port imported from camera_utils


class AccountingWebService(FrameCaptureMixin, ScannerDiagnosticsMixin, DetectionMixin):
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
        
        # Duplicate detection - keep best quality
        self.recent_documents: List[Dict] = []  # Recent docs for duplicate check
        self.duplicate_window_sec = 5.0  # Time window for duplicate detection
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

    def _compute_image_hash(self, image_bytes: bytes) -> str:
        """Compute perceptual hash for image similarity."""
        import hashlib
        if not HAS_CV2:
            return hashlib.md5(image_bytes).hexdigest()
        
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return hashlib.md5(image_bytes).hexdigest()
            
            # Resize to 8x8 and compute hash
            resized = cv2.resize(img, (8, 8), interpolation=cv2.INTER_AREA)
            mean = resized.mean()
            bits = (resized > mean).flatten()
            return ''.join(['1' if b else '0' for b in bits])
        except Exception:
            return hashlib.md5(image_bytes).hexdigest()
    
    def _compute_image_quality(self, image_bytes: bytes) -> float:
        """Compute image quality score based on sharpness and contrast."""
        if not HAS_CV2:
            return len(image_bytes) / 1000000  # Fallback: file size
        
        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return 0.0
            
            # Laplacian variance as sharpness metric
            laplacian = cv2.Laplacian(img, cv2.CV_64F)
            sharpness = laplacian.var()
            
            # Contrast (std of pixel values)
            contrast = img.std()
            
            # Combined score
            return sharpness * 0.01 + contrast * 0.1
        except Exception:
            return 0.0
    
    def _is_duplicate(self, image_bytes: bytes, doc_type: str) -> Tuple[bool, Optional[int]]:
        """Check if document is duplicate. Returns (is_dup, better_idx)."""
        import time
        now = time.time()
        
        # Clean old entries
        self.recent_documents = [
            d for d in self.recent_documents 
            if now - d["timestamp"] < self.duplicate_window_sec
        ]
        
        # Compute hash and quality
        new_hash = self._compute_image_hash(image_bytes)
        new_quality = self._compute_image_quality(image_bytes)
        
        # Check for similar documents
        for i, doc in enumerate(self.recent_documents):
            if doc["doc_type"] != doc_type:
                continue
            
            # Compare hashes (allow 10% difference for perceptual hash)
            if len(new_hash) == 64:  # Perceptual hash
                diff = sum(a != b for a, b in zip(new_hash, doc["hash"]))
                if diff <= 6:  # Similar images
                    if new_quality > doc["quality"]:
                        return True, i  # Duplicate, but new is better
                    else:
                        return True, None  # Duplicate, keep old
        
        # Not a duplicate - add to recent
        self.recent_documents.append({
            "hash": new_hash,
            "quality": new_quality,
            "doc_type": doc_type,
            "timestamp": now,
            "image_bytes": image_bytes,
        })
        
        return False, None

    def _mask_rtsp_url(self, url: str) -> str:
        """Mask password in RTSP URL for display."""
        if not url:
            return ""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:****@', url)
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
                        # Get detection info
                        detection = self.last_detection_result or {}
                        
                        # YAML diagnostic logging (every 10 frames)
                        if frame_sent_count % 10 == 1 and detection:
                            yaml_log = self._format_yaml_log({
                                "scan_frame": frame_sent_count,
                                "detection": {
                                    "detected": self.document_detected,
                                    "type": detection.get("document_type"),
                                    "confidence": round(detection.get("confidence", 0), 2),
                                    "method": detection.get("method"),
                                    "features": detection.get("features", []),
                                },
                                "clients": len(self.clients),
                            })
                            print(yaml_log)
                        
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

    async def _deep_analyze(self, ws):
        """Deep analysis with OCR + LLM (LLaVA-style vision analysis)."""
        import time
        t_start = time.time()
        
        await ws.send_str(json.dumps({
            "type": "log",
            "message": "🔬 Rozpoczynam głęboką analizę...",
            "level": "info"
        }))
        
        # Capture current frame
        image_bytes = self.capture()
        if not image_bytes:
            await ws.send_str(json.dumps({
                "type": "log",
                "message": "❌ Nie można pobrać klatki",
                "level": "error"
            }))
            return
        
        timing = {"capture": (time.time() - t_start) * 1000}
        
        # Step 1: OCR analysis
        t_ocr = time.time()
        temp_path = self.temp_dir / f"deep_analyze_{int(time.time() * 1000)}.jpg"
        with open(temp_path, 'wb') as f:
            f.write(image_bytes)
        
        ocr_text = ""
        ocr_confidence = 0.0
        try:
            ocr_text, ocr_confidence, _ = self.ocr_engine.extract_text(temp_path, lang="pol")
            timing["ocr"] = (time.time() - t_ocr) * 1000
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"📝 OCR: {len(ocr_text)} znaków ({timing['ocr']:.0f}ms)",
                "level": "info"
            }))
        except Exception as e:
            timing["ocr"] = (time.time() - t_ocr) * 1000
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"⚠️ OCR error: {e}",
                "level": "warning"
            }))
        
        # Step 2: LLM classification
        t_llm = time.time()
        classifier = get_classifier()
        llm_result = {}
        
        if len(ocr_text) > 50:
            # Use text-based classification
            llm_result = classifier.classify_document(ocr_text)
            timing["llm_text"] = (time.time() - t_llm) * 1000
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"🤖 LLM klasyfikacja: {llm_result.get('document_type', 'unknown')} ({timing['llm_text']:.0f}ms)",
                "level": "info"
            }))
        else:
            # Try vision LLM (LLaVA-style) if OCR failed
            await ws.send_str(json.dumps({
                "type": "log",
                "message": "👁️ OCR niewystarczający, próbuję analizy wizyjnej...",
                "level": "warning"
            }))
            llm_result = await self._vision_analyze(image_bytes, ws)
            timing["llm_vision"] = (time.time() - t_llm) * 1000
        
        timing["total"] = (time.time() - t_start) * 1000
        
        # Create document entry
        doc_type = llm_result.get("document_type", "other")
        confidence = llm_result.get("confidence", 0.5)
        
        thumbnail = self._create_thumbnail(image_bytes, max_size=120)
        doc_id = int(time.time() * 1000) % 100000
        
        # Log YAML summary
        yaml_log = self._format_yaml_log({
            "action": "deep_analyze",
            "timestamp": datetime.now().isoformat(),
            "timing_ms": timing,
            "ocr_length": len(ocr_text),
            "ocr_confidence": ocr_confidence,
            "llm_result": llm_result,
            "document_type": doc_type,
            "confidence": confidence,
        })
        print(yaml_log)
        
        # Create larger thumbnail for better visibility
        large_thumbnail = self._create_thumbnail(image_bytes, max_size=300)
        
        # Send result to browser - add as document (not pending) with full data
        await ws.send_str(json.dumps({
            "type": "document",
            "document": {
                "id": doc_id,
                "type": doc_type,
                "doc_type": doc_type,
                "confidence": confidence,
                "thumbnail": base64.b64encode(large_thumbnail).decode() if large_thumbnail else None,
                "image": base64.b64encode(image_bytes).decode() if image_bytes else None,
                "ocr_text": ocr_text[:2000] if ocr_text else "",
                "amount": llm_result.get("total_amount") or llm_result.get("gross_amount"),
                "nip": llm_result.get("nip") or llm_result.get("seller_nip"),
                "lang": llm_result.get("language"),
                "vendor": llm_result.get("vendor_name") or llm_result.get("vendor"),
                "summary": llm_result.get("summary") or llm_result.get("description"),
                "pending": False,
                "date": datetime.now().strftime("%H:%M:%S"),
                "timestamp": datetime.now().isoformat(),
            }
        }))
        
        # Store for confirmation
        self._pending_by_id = getattr(self, '_pending_by_id', {})
        self._pending_by_id[doc_id] = {
            "frame": image_bytes,
            "doc_type": doc_type,
            "detection": {"confidence": confidence},
            "ocr_text": ocr_text,
            "llm_result": llm_result,
            "timestamp": datetime.now().isoformat(),
        }
        
        await ws.send_str(json.dumps({
            "type": "log",
            "message": f"✅ Analiza zakończona: {doc_type} ({confidence:.0%}) w {timing['total']:.0f}ms",
            "level": "success"
        }))

    async def _vision_analyze(self, image_bytes: bytes, ws) -> dict:
        """Analyze image using vision LLM (LLaVA-style)."""
        try:
            import litellm
            
            # Encode image to base64
            img_b64 = base64.b64encode(image_bytes).decode()
            
            response = litellm.completion(
                model="gpt-4o-mini",  # or "ollama/llava" for local
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": """Analyze this image of a document. 
Respond in JSON:
{
    "document_type": "invoice|receipt|letter|form|id_document|other",
    "confidence": 0.0-1.0,
    "language": "pl|en|de|other",
    "description": "brief description",
    "visible_text": "key text visible",
    "total_amount": number or null,
    "currency": "PLN|EUR|USD|null"
}"""},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                    ]
                }],
                temperature=0.1,
            )
            
            content = response.choices[0].message.content
            # Try to parse JSON from response
            import re
            json_match = re.search(r'\{[^{}]+\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return {"document_type": "other", "confidence": 0.3, "description": content[:200]}
            
        except Exception as e:
            await ws.send_str(json.dumps({
                "type": "log",
                "message": f"⚠️ Vision LLM error: {e}",
                "level": "warning"
            }))
            return {"document_type": "other", "confidence": 0.2}

    def _format_yaml_log(self, data: dict) -> str:
        """Format data as YAML log output."""
        lines = ["---"]
        def _format(d, indent=0):
            result = []
            prefix = "  " * indent
            for k, v in d.items():
                if isinstance(v, dict):
                    result.append(f"{prefix}{k}:")
                    result.extend(_format(v, indent + 1))
                elif isinstance(v, list):
                    result.append(f"{prefix}{k}:")
                    for item in v:
                        if isinstance(item, dict):
                            result.append(f"{prefix}  -")
                            result.extend(_format(item, indent + 2))
                        else:
                            result.append(f"{prefix}  - {item}")
                else:
                    result.append(f"{prefix}{k}: {v}")
            return result
        lines.extend(_format(data))
        return "\n".join(lines)

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
        
        elif action == "analyze_deep":
            # Deep analysis with OCR + LLM
            await self._deep_analyze(ws)

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
        return web.Response(text=get_scanner_html_template(), content_type='text/html')

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


# Entry point functions moved to web_cli.py
# Import for backward compatibility
from .web_cli import run_opencv_preview, run_accounting_web
