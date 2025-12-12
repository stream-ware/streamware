"""
Scanner Configuration Module

Loads all scanner-related configuration from .env file.
Provides centralized configuration management for document detection.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv


def load_env_files() -> None:
    """Load .env files from current directory and parent directories."""
    # Try multiple locations
    env_paths = [
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
        Path(__file__).parent / ".env",
        Path(__file__).parent.parent / ".env",
    ]
    
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break


def get_scanner_config() -> Dict[str, Any]:
    """Load scanner configuration from environment variables."""
    load_env_files()
    
    return {
        # FPS and timing
        "fps": float(os.getenv("SQ_SCANNER_FPS", "2")),
        "cooldown_sec": float(os.getenv("SQ_SCANNER_COOLDOWN_SEC", "2")),
        
        # Confidence thresholds
        "min_confidence": float(os.getenv("SQ_SCANNER_MIN_CONFIDENCE", "0.25")),
        "confirm_threshold": float(os.getenv("SQ_SCANNER_CONFIRM_THRESHOLD", "0.60")),
        "auto_save_threshold": float(os.getenv("SQ_SCANNER_AUTO_SAVE_THRESHOLD", "0.85")),
        
        # Detection settings
        "use_llm_confirm": os.getenv("SQ_SCANNER_USE_LLM_CONFIRM", "true").lower() == "true",
        "use_yolo": os.getenv("SQ_SCANNER_USE_YOLO", "true").lower() == "true",
        "use_doctr": os.getenv("SQ_SCANNER_USE_DOCTR", "true").lower() == "true",
        
        # Image quality
        "jpeg_quality": int(os.getenv("SQ_SCANNER_JPEG_QUALITY", "90")),
        "thumbnail_size": int(os.getenv("SQ_SCANNER_THUMBNAIL_SIZE", "120")),
        
        # LLM settings
        "llm_model": os.getenv("SQ_SCANNER_LLM_MODEL", os.getenv("SQ_AI_MODEL", "gpt-4o-mini")),
        "llm_temperature": float(os.getenv("SQ_SCANNER_LLM_TEMPERATURE", "0.1")),
        
        # Document types to detect
        "detect_receipts": os.getenv("SQ_SCANNER_DETECT_RECEIPTS", "true").lower() == "true",
        "detect_invoices": os.getenv("SQ_SCANNER_DETECT_INVOICES", "true").lower() == "true",
        "detect_documents": os.getenv("SQ_SCANNER_DETECT_DOCUMENTS", "true").lower() == "true",
    }


def get_camera_config() -> Dict[str, Any]:
    """Load camera configuration from environment variables."""
    load_env_files()
    
    config = {
        "default_url": os.getenv("SQ_DEFAULT_URL"),
        "rtsp_user": os.getenv("SQ_RTSP_USER"),
        "rtsp_pass": os.getenv("SQ_RTSP_PASS"),
        "rtsp_port": os.getenv("SQ_RTSP_PORT", "554"),
        "cameras": [],
        "default_camera": os.getenv("SQ_DEFAULT_CAMERA"),
    }
    
    # Parse SQ_CAMERAS (format: name|url,name|url,...)
    cameras_str = os.getenv("SQ_CAMERAS", "")
    if cameras_str:
        for cam in cameras_str.split(","):
            cam = cam.strip()
            if "|" in cam:
                name, url = cam.split("|", 1)
                config["cameras"].append({"name": name.strip(), "url": url.strip()})
            elif cam:
                config["cameras"].append({"name": f"camera_{len(config['cameras'])}", "url": cam})
    
    return config


def get_detection_thresholds() -> Dict[str, float]:
    """Get detection thresholds from environment."""
    load_env_files()
    
    return {
        # Receipt detection thresholds
        "receipt_aspect_ratio_min": float(os.getenv("SQ_RECEIPT_ASPECT_MIN", "1.2")),
        "receipt_aspect_ratio_max": float(os.getenv("SQ_RECEIPT_ASPECT_MAX", "4.0")),
        "receipt_area_min": float(os.getenv("SQ_RECEIPT_AREA_MIN", "0.05")),
        "receipt_brightness_min": float(os.getenv("SQ_RECEIPT_BRIGHTNESS_MIN", "150")),
        
        # Invoice detection thresholds
        "invoice_aspect_ratio_min": float(os.getenv("SQ_INVOICE_ASPECT_MIN", "1.2")),
        "invoice_aspect_ratio_max": float(os.getenv("SQ_INVOICE_ASPECT_MAX", "1.6")),
        "invoice_area_min": float(os.getenv("SQ_INVOICE_AREA_MIN", "0.1")),
        
        # General document thresholds
        "edge_density_min": float(os.getenv("SQ_EDGE_DENSITY_MIN", "0.04")),
        "contour_area_min": float(os.getenv("SQ_CONTOUR_AREA_MIN", "0.03")),
        "contour_area_max": float(os.getenv("SQ_CONTOUR_AREA_MAX", "0.98")),
    }


def get_ocr_config() -> Dict[str, Any]:
    """Get OCR configuration from environment."""
    load_env_files()
    
    return {
        "engine": os.getenv("SQ_OCR_ENGINE", "tesseract"),
        "language": os.getenv("SQ_OCR_LANGUAGE", "pol+eng"),
        "dpi": int(os.getenv("SQ_OCR_DPI", "300")),
        "timeout": int(os.getenv("SQ_OCR_TIMEOUT", "30")),
    }


class ScannerConfig:
    """Centralized scanner configuration class."""
    
    def __init__(self):
        self.scanner = get_scanner_config()
        self.camera = get_camera_config()
        self.thresholds = get_detection_thresholds()
        self.ocr = get_ocr_config()
    
    def reload(self):
        """Reload configuration from environment."""
        self.__init__()
    
    @property
    def fps(self) -> float:
        return self.scanner["fps"]
    
    @property
    def min_confidence(self) -> float:
        return self.scanner["min_confidence"]
    
    @property
    def confirm_threshold(self) -> float:
        return self.scanner["confirm_threshold"]
    
    @property
    def auto_save_threshold(self) -> float:
        return self.scanner["auto_save_threshold"]
    
    @property
    def use_llm(self) -> bool:
        return self.scanner["use_llm_confirm"]
    
    @property
    def llm_model(self) -> str:
        return self.scanner["llm_model"]


# Global config instance
_config: Optional[ScannerConfig] = None

def get_config() -> ScannerConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = ScannerConfig()
    return _config


def get_combined_config() -> Dict[str, Any]:
    """Get combined scanner and camera config as flat dict (for backward compatibility)."""
    load_env_files()
    
    scanner = get_scanner_config()
    camera = get_camera_config()
    
    # Build cameras_list and cameras dict
    cameras_dict = {}
    cameras_list = []
    for cam in camera.get("cameras", []):
        name = cam.get("name", f"camera_{len(cameras_list)}")
        url = cam.get("url", "")
        cameras_dict[name] = url
        cameras_list.append((name, url))
    
    return {
        # Camera settings
        "default_url": camera.get("default_url"),
        "rtsp_user": camera.get("rtsp_user"),
        "rtsp_password": camera.get("rtsp_pass"),
        "default_camera": camera.get("default_camera", 0),
        "cameras": cameras_dict,
        "cameras_list": cameras_list,
        # Scanner settings
        "scanner_fps": scanner.get("fps", 2),
        "scanner_min_confidence": scanner.get("min_confidence", 0.25),
        "scanner_confirm_threshold": scanner.get("confirm_threshold", 0.60),
        "scanner_auto_save_threshold": scanner.get("auto_save_threshold", 0.80),
        "scanner_cooldown_sec": scanner.get("cooldown_sec", 2),
        "scanner_use_llm_confirm": scanner.get("use_llm_confirm", True),
        "scanner_jpeg_quality": scanner.get("jpeg_quality", 90),
    }
