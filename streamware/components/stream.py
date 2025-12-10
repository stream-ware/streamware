"""
Stream Component - Real-time video/audio stream analysis

Supported sources:
    - RTSP: Security cameras, IP cameras
    - HLS: Live streams, TV broadcasts
    - YouTube: Live streams and videos
    - Twitch: Live gaming streams
    - Screen: Desktop screen capture
    - Webcam: Local camera capture
    - HTTP: Direct video URLs

URI Examples:
    stream://rtsp?url=rtsp://camera/live&mode=diff
    stream://hls?url=https://stream.m3u8&mode=stream
    stream://youtube?url=https://youtube.com/watch?v=xxx&mode=full
    stream://screen?monitor=0&mode=diff
    stream://webcam?device=0&mode=stream

Related:
    - examples/media-processing/stream_analysis.py
    - docs/v2/guides/MEDIA_GUIDE.md
    - streamware/components/media.py
"""

import subprocess
import tempfile
import logging
import time
import os
from pathlib import Path
from typing import Any, Dict, Generator, Optional
from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError
from ..config import config

logger = logging.getLogger(__name__)


@register("stream")
@register("live")
class StreamComponent(Component):
    """
    Real-time stream analysis component.
    
    Supports multiple stream sources and analysis modes.
    
    Sources:
        - rtsp: RTSP streams (cameras)
        - hls: HLS/M3U8 streams
        - youtube: YouTube live/videos
        - twitch: Twitch streams
        - screen: Screen capture
        - webcam: Local webcam
        - http: Direct URLs
    
    Modes:
        - full: Periodic summary (every N seconds)
        - stream: Continuous frame analysis
        - diff: Track changes between frames
    
    URI Examples:
        stream://rtsp?url=rtsp://192.168.1.100/live&mode=diff&interval=5
        stream://youtube?url=https://youtube.com/watch?v=xxx&mode=stream
        stream://screen?monitor=0&mode=diff&interval=2
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    SOURCES = {
        "rtsp": {"protocol": "rtsp://", "requires": ["ffmpeg"]},
        "hls": {"protocol": "https://", "requires": ["ffmpeg"]},
        "youtube": {"protocol": "https://", "requires": ["yt-dlp", "ffmpeg"]},
        "twitch": {"protocol": "https://", "requires": ["streamlink", "ffmpeg"]},
        "screen": {"protocol": "local", "requires": ["ffmpeg"]},
        "webcam": {"protocol": "local", "requires": ["ffmpeg"]},
        "http": {"protocol": "http://", "requires": ["ffmpeg"]},
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.source = uri.operation or "rtsp"
        
        self.url = uri.get_param("url")
        self.mode = uri.get_param("mode", "diff")  # full, stream, diff
        self.interval = int(uri.get_param("interval", "5"))  # seconds between captures
        self.duration = int(uri.get_param("duration", "0"))  # 0 = infinite
        self.model = uri.get_param("model", "llava:13b")  # Use 13B for better accuracy
        self.prompt = uri.get_param("prompt", "")
        
        # Focus tracking - what to detect
        self.focus = uri.get_param("focus", "")  # person, animal, vehicle, face, motion, package, intrusion
        self.zone = uri.get_param("zone", "")  # x,y,w,h for detection zone
        self.sensitivity = uri.get_param("sensitivity", "medium")  # low, medium, high
        
        # Save frames for HTML reports
        save_param = uri.get_param("save_frames", "false")
        self.save_frames = str(save_param).lower() in ("true", "1", "yes")
        
        # Screen capture options
        self.monitor = uri.get_param("monitor", "0")
        self.region = uri.get_param("region")  # x,y,w,h
        
        # Webcam options
        self.device = uri.get_param("device", "0")
        
        # YouTube/Twitch options
        self.quality = uri.get_param("quality", "best")
        
        self._temp_dir = None
    
    def process(self, data: Any) -> Dict:
        """Process stream - capture and analyze frames"""
        if self.source not in self.SOURCES:
            raise ComponentError(f"Unknown source: {self.source}. Supported: {list(self.SOURCES.keys())}")
        
        # Setup temp directory
        self._temp_dir = Path(tempfile.mkdtemp())
        
        try:
            if self.source == "screen":
                return self._analyze_screen()
            elif self.source == "webcam":
                return self._analyze_webcam()
            elif self.source == "youtube":
                return self._analyze_youtube()
            elif self.source == "twitch":
                return self._analyze_twitch()
            else:
                return self._analyze_stream()
        finally:
            # Cleanup
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def stream(self, input_data: Any = None) -> Generator[Dict, None, None]:
        """Stream analysis - yields results continuously"""
        self._temp_dir = Path(tempfile.mkdtemp())
        
        try:
            frame_count = 0
            start_time = time.time()
            prev_description = None
            
            while True:
                # Check duration limit
                if self.duration > 0 and (time.time() - start_time) > self.duration:
                    break
                
                # Capture frame
                frame_path = self._capture_frame(frame_count)
                if not frame_path or not frame_path.exists():
                    time.sleep(1)
                    continue
                
                # Analyze frame
                result = self._analyze_frame(frame_path, frame_count, prev_description)
                
                if self.mode == "diff" and result.get("type") == "no_change":
                    # Skip if no changes
                    pass
                else:
                    yield result
                
                prev_description = result.get("description", result.get("changes", ""))
                frame_count += 1
                
                # Wait for next interval
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            yield {"type": "stopped", "frames_analyzed": frame_count}
        finally:
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def _capture_frame(self, frame_num: int) -> Optional[Path]:
        """Capture single frame from stream"""
        output_path = self._temp_dir / f"frame_{frame_num:05d}.jpg"
        
        try:
            if self.source == "screen":
                return self._capture_screen(output_path)
            elif self.source == "webcam":
                return self._capture_webcam(output_path)
            elif self.source == "youtube":
                return self._capture_youtube(output_path)
            elif self.source == "twitch":
                return self._capture_twitch(output_path)
            else:
                return self._capture_rtsp_hls(output_path)
        except Exception as e:
            logger.warning(f"Frame capture failed: {e}")
            return None
    
    def _capture_screen(self, output_path: Path) -> Path:
        """Capture screenshot"""
        # Try scrot first (Linux)
        try:
            subprocess.run(["scrot", str(output_path)], check=True, capture_output=True, timeout=5)
            return output_path
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Try ffmpeg x11grab (Linux)
        try:
            display = os.environ.get("DISPLAY", ":0")
            cmd = [
                "ffmpeg", "-y", "-f", "x11grab",
                "-video_size", "1920x1080",
                "-i", display,
                "-frames:v", "1",
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            return output_path
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # Try macOS screencapture
        try:
            subprocess.run(["screencapture", "-x", str(output_path)], check=True, capture_output=True, timeout=5)
            return output_path
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        raise ComponentError("No screen capture tool available. Install: scrot (Linux) or use macOS")
    
    def _capture_webcam(self, output_path: Path) -> Path:
        """Capture from webcam"""
        device = f"/dev/video{self.device}" if not self.device.startswith("/") else self.device
        
        # Linux v4l2
        try:
            cmd = [
                "ffmpeg", "-y", "-f", "v4l2",
                "-i", device,
                "-frames:v", "1",
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            return output_path
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        # macOS avfoundation
        try:
            cmd = [
                "ffmpeg", "-y", "-f", "avfoundation",
                "-i", self.device,
                "-frames:v", "1",
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            return output_path
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass
        
        raise ComponentError(f"Cannot capture from webcam: {device}")
    
    def _capture_youtube(self, output_path: Path) -> Path:
        """Capture frame from YouTube stream"""
        if not self.url:
            raise ComponentError("YouTube URL required")
        
        # Get stream URL with yt-dlp
        try:
            result = subprocess.run(
                ["yt-dlp", "-f", "best", "-g", self.url],
                capture_output=True, text=True, timeout=30
            )
            stream_url = result.stdout.strip()
        except FileNotFoundError:
            raise ComponentError("yt-dlp not installed. Install: pip install yt-dlp")
        
        if not stream_url:
            raise ComponentError(f"Cannot get YouTube stream URL: {self.url}")
        
        # Capture frame
        cmd = [
            "ffmpeg", "-y",
            "-i", stream_url,
            "-frames:v", "1",
            "-q:v", "2",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return output_path
    
    def _capture_twitch(self, output_path: Path) -> Path:
        """Capture frame from Twitch stream"""
        if not self.url:
            raise ComponentError("Twitch URL required")
        
        # Get stream URL with streamlink
        try:
            result = subprocess.run(
                ["streamlink", "--stream-url", self.url, self.quality],
                capture_output=True, text=True, timeout=30
            )
            stream_url = result.stdout.strip()
        except FileNotFoundError:
            raise ComponentError("streamlink not installed. Install: pip install streamlink")
        
        if not stream_url:
            raise ComponentError(f"Cannot get Twitch stream URL: {self.url}")
        
        # Capture frame
        cmd = [
            "ffmpeg", "-y",
            "-i", stream_url,
            "-frames:v", "1",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True, timeout=30)
        return output_path
    
    def _capture_rtsp_hls(self, output_path: Path) -> Path:
        """Capture frame from RTSP/HLS/HTTP stream"""
        if not self.url:
            raise ComponentError("Stream URL required")
        
        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",  # For RTSP
            "-i", self.url,
            "-frames:v", "1",
            "-q:v", "2",
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return output_path
        except subprocess.CalledProcessError as e:
            # Try without RTSP options for HLS/HTTP
            cmd = [
                "ffmpeg", "-y",
                "-i", self.url,
                "-frames:v", "1",
                str(output_path)
            ]
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return output_path
    
    def _analyze_frame(self, frame_path: Path, frame_num: int, prev_description: str = None) -> Dict:
        """Analyze frame with AI"""
        from ..prompts import render_prompt
        
        timestamp = time.strftime("%H:%M:%S")
        
        # Build focus-specific prompt
        focus_prompt = self._build_focus_prompt()
        sensitivity_guide = self._get_sensitivity_guide()
        
        if self.mode == "diff" and prev_description:
            # Diff mode - detect changes with focus
            prompt = render_prompt(
                "stream_diff",
                focus_prompt=focus_prompt,
                prev_description=prev_description[:400],
                sensitivity=self.sensitivity,
                sensitivity_guide=sensitivity_guide,
                custom_prompt=self.prompt or ""
            )
        elif self.mode == "stream":
            # Stream mode - detailed analysis
            prompt = render_prompt(
                "stream_full",
                focus_prompt=focus_prompt,
                custom_prompt=self.prompt or ""
            )
        else:
            # Full mode - general description with focus
            if self.focus:
                prompt = render_prompt(
                    "stream_focus",
                    focus=self.focus,
                    custom_prompt=self.prompt or ""
                )
            else:
                prompt = f"Describe what you see in this frame. {self.prompt}"
        
        # Call LLaVA for analysis
        description = self._call_llava(frame_path, prompt)
        
        result = {
            "frame": frame_num + 1,
            "timestamp": timestamp,
            "source": self.source,
            "mode": self.mode,
        }
        
        if self.mode == "diff":
            is_change = "no significant" not in description.lower()
            result["type"] = "change" if is_change else "no_change"
            result["changes"] = description
        else:
            result["description"] = description
        
        # Include base64 image for HTML reports
        if self.save_frames and frame_path.exists():
            import base64
            try:
                with open(frame_path, "rb") as f:
                    result["image_base64"] = base64.b64encode(f.read()).decode()
            except Exception:
                pass
        
        return result
    
    def _build_focus_prompt(self) -> str:
        """Build focus-specific detection prompt"""
        if not self.focus:
            return "Monitor for any significant activity or changes."
        
        focus_prompts = {
            "person": """FOCUS: PEOPLE DETECTION
- Count all people visible (even partial/obscured)
- Track positions: entering, leaving, stationary
- Actions: walking, running, sitting, standing, bending
- ALERT on: new person appearing, person leaving, unusual movement""",
            
            "animal": """FOCUS: ANIMAL DETECTION
- Detect: dogs, cats, birds, wildlife
- Track: movement direction, behavior (calm/agitated)
- ALERT on: animal entering frame, aggressive behavior""",
            
            "vehicle": """FOCUS: VEHICLE DETECTION
- Types: car, truck, motorcycle, bicycle
- Track: parked/moving, direction, speed (slow/fast)
- ALERT on: vehicle arriving, leaving, stopping unusually""",
            
            "face": """FOCUS: FACE DETECTION
- Count visible faces
- Orientation: facing camera, profile, back
- ALERT on: new face appearing, face turning toward camera""",
            
            "motion": """FOCUS: MOTION DETECTION
- Any movement in frame (ignore camera shake)
- Direction and speed of movement
- ALERT on: any significant motion""",
            
            "package": """FOCUS: PACKAGE/DELIVERY DETECTION
- Boxes, bags, parcels on ground
- Delivery person presence
- ALERT on: package placed, package removed, delivery activity""",
            
            "intrusion": """FOCUS: INTRUSION DETECTION
- Unauthorized entry attempts
- Doors/windows opening
- Suspicious behavior (looking around, testing locks)
- ALERT on: any unauthorized access attempt"""
        }
        
        # Support multiple focus types
        focuses = [f.strip() for f in self.focus.split(",")]
        prompts = []
        for f in focuses:
            if f in focus_prompts:
                prompts.append(focus_prompts[f])
            else:
                prompts.append(f"FOCUS: Detect and track {f}")
        
        return "\n".join(prompts)
    
    def _get_sensitivity_guide(self) -> str:
        """Get sensitivity-specific detection rules"""
        guides = {
            "low": """- IGNORE: lighting changes, shadows, small movements
- IGNORE: minor position shifts of stationary people
- ALERT ONLY: new person/vehicle appearing, someone leaving
- Threshold: Major changes only""",
            
            "medium": """- IGNORE: lighting changes, camera shake
- REPORT: significant movement, position changes
- ALERT: new arrivals, departures, notable actions
- Threshold: Moderate changes""",
            
            "high": """- REPORT: any movement or position change
- REPORT: even small changes in scene
- ALERT: any activity
- Threshold: All changes"""
        }
        return guides.get(self.sensitivity, guides["medium"])
    
    def _focus_target(self) -> str:
        """Get human-readable focus target"""
        if not self.focus:
            return "significant change"
        
        focuses = [f.strip() for f in self.focus.split(",")]
        if len(focuses) == 1:
            return f"{focuses[0]} activity"
        return f"activity ({', '.join(focuses)})"
    
    def _call_llava(self, image_path: Path, prompt: str) -> str:
        """Call LLaVA for image analysis with optimized image"""
        try:
            import requests
            
            # Optimize image before sending to LLM
            from ..image_optimize import prepare_image_for_llm_base64
            
            # Use "fast" preset for real-time analysis, "balanced" for quality
            preset = "fast" if self.sensitivity == "low" else "balanced"
            image_data = prepare_image_for_llm_base64(image_path, preset=preset)
            
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            timeout = int(config.get("SQ_LLM_TIMEOUT", "60"))
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=timeout
            )
            
            if response.ok:
                return response.json().get("response", "")
            else:
                return f"Analysis failed: {response.status_code}"
                
        except Exception as e:
            return f"Could not analyze: {e}"
    
    def _analyze_screen(self) -> Dict:
        """Analyze screen capture"""
        return self._run_analysis("screen capture")
    
    def _analyze_webcam(self) -> Dict:
        """Analyze webcam stream"""
        return self._run_analysis("webcam")
    
    def _analyze_youtube(self) -> Dict:
        """Analyze YouTube stream"""
        return self._run_analysis(f"YouTube: {self.url}")
    
    def _analyze_twitch(self) -> Dict:
        """Analyze Twitch stream"""
        return self._run_analysis(f"Twitch: {self.url}")
    
    def _analyze_stream(self) -> Dict:
        """Analyze RTSP/HLS/HTTP stream"""
        return self._run_analysis(f"stream: {self.url}")
    
    def _run_analysis(self, source_name: str) -> Dict:
        """Run analysis for specified number of frames"""
        frames = []
        prev_description = None
        
        # Capture and analyze frames
        num_frames = max(1, self.duration // self.interval) if self.duration > 0 else 5
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                result = self._analyze_frame(frame_path, i, prev_description)
                frames.append(result)
                prev_description = result.get("description", result.get("changes", ""))
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        # Build summary
        if self.mode == "diff":
            changes = [f for f in frames if f.get("type") == "change"]
            return {
                "success": True,
                "source": source_name,
                "mode": self.mode,
                "timeline": frames,
                "significant_changes": len(changes),
                "frames_analyzed": len(frames)
            }
        else:
            return {
                "success": True,
                "source": source_name,
                "mode": self.mode,
                "frames": frames,
                "frames_analyzed": len(frames)
            }


# Quick helper functions
def analyze_stream(url: str, mode: str = "diff", interval: int = 5, duration: int = 30) -> Dict:
    """Quick stream analysis"""
    from ..core import flow
    return flow(f"stream://rtsp?url={url}&mode={mode}&interval={interval}&duration={duration}").run()


def analyze_screen(mode: str = "diff", interval: int = 2, duration: int = 10) -> Dict:
    """Quick screen analysis"""
    from ..core import flow
    return flow(f"stream://screen?mode={mode}&interval={interval}&duration={duration}").run()


def analyze_youtube(url: str, mode: str = "stream", duration: int = 30) -> Dict:
    """Quick YouTube analysis"""
    from ..core import flow
    return flow(f"stream://youtube?url={url}&mode={mode}&duration={duration}").run()


def watch_screen(mode: str = "diff", interval: int = 2):
    """Watch screen continuously (generator)"""
    from ..core import flow
    f = flow(f"stream://screen?mode={mode}&interval={interval}")
    return f.stream()
