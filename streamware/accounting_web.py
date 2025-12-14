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
from .archive_mixin import ArchiveMixin
from .duplicate_mixin import DuplicateMixin
from .web_mixin import WebMixin

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


class AccountingWebService(FrameCaptureMixin, ScannerDiagnosticsMixin, DetectionMixin, ArchiveMixin, DuplicateMixin, WebMixin):
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
        self.queued_broadcasts: List[Dict[str, Any]] = []
        
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
                            # _format_yaml_log is available via ArchiveMixin
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

                        while self.queued_broadcasts:
                            payload = self.queued_broadcasts.pop(0)
                            await self.broadcast(payload)
                        
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
