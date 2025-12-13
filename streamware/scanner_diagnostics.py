"""
Scanner Diagnostics Module

Diagnostics methods for checking capture methods and camera availability.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


class ScannerDiagnosticsMixin:
    """Mixin class providing diagnostics methods for AccountingWebService."""
    
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
