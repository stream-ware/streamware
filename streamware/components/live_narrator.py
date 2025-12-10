"""
Live Narrator Component - Real-time stream description with TTS

Features:
1. Continuous stream analysis with AI
2. Text-to-speech output for descriptions
3. Configurable triggers ("alert when person appears")
4. Advanced motion detection with edge tracking
5. Preprocessed frames for better AI analysis
6. History tracking of descriptions

URI Examples:
    live://narrator?source=rtsp://camera/live&tts=true
    live://watch?source=rtsp://camera/live&trigger=person
    live://describe?source=rtsp://camera/live&interval=5

Related:
    - streamware/components/motion_diff.py
    - streamware/components/stream.py
"""

import subprocess
import tempfile
import logging
import time
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import base64
import json
from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError
from ..config import config

logger = logging.getLogger(__name__)


class FrameAnalyzer:
    """
    Advanced frame analysis with motion detection, edge tracking, and preprocessing.
    Processes frames before sending to LLM for better accuracy.
    """
    
    def __init__(self, threshold: int = 25, min_area: int = 500):
        self.threshold = threshold
        self.min_area = min_area
        self._prev_frame = None
        self._prev_gray = None
        self._motion_history = []
    
    def analyze(self, frame_path: Path) -> Tuple[Dict, Optional[Path]]:
        """Analyze frame for motion and objects.

        Performance optimisation:
        - Motion / edge detection works on a downscaled (~30%) frame
        - Annotations are drawn on the original resolution image
        Returns analysis dict and path to annotated frame.
        """
        try:
            from PIL import Image, ImageDraw, ImageFilter, ImageOps
        except ImportError:
            return {"error": "PIL not installed"}, None
        
        img = Image.open(frame_path)

        # Downscale for faster numerical analysis (configurable via SQ_FRAME_SCALE)
        from ..config import config
        scale_factor = float(config.get("SQ_FRAME_SCALE", "0.3"))
        try:
            if img.width > 0 and img.height > 0:
                small_size = (
                    max(1, int(img.width * scale_factor)),
                    max(1, int(img.height * scale_factor)),
                )
                gray_small = img.resize(small_size, Image.BILINEAR).convert('L')
            else:
                gray_small = img.convert('L')
        except Exception:
            # Fallback: no downscaling
            gray_small = img.convert('L')
        
        analysis = {
            "has_motion": False,
            "motion_percent": 0.0,
            "motion_regions": [],
            "edge_objects": [],
            "likely_person": False,
            "person_confidence": 0.0,
        }
        
        # Motion detection (on downscaled frames)
        if self._prev_gray is not None:
            motion_data = self._detect_motion(gray_small, self._prev_gray)
            analysis.update(motion_data)
        
        # Edge detection for object boundaries (also on downscaled frame)
        edge_data = self._detect_edges(gray_small)
        analysis["edge_objects"] = edge_data.get("objects", [])
        
        # Analyze if motion pattern suggests person
        if analysis["has_motion"]:
            person_analysis = self._analyze_for_person(analysis, img.size)
            analysis.update(person_analysis)
        
        # Rescale motion regions back to original coordinates for annotation
        try:
            if analysis.get("motion_regions"):
                scale_x = img.width / float(gray_small.width)
                scale_y = img.height / float(gray_small.height)
                for region in analysis["motion_regions"]:
                    region["x"] = int(region["x"] * scale_x)
                    region["y"] = int(region["y"] * scale_y)
                    region["w"] = int(region["w"] * scale_x)
                    region["h"] = int(region["h"] * scale_y)
        except Exception as e:
            logger.debug(f"Failed to rescale motion regions: {e}")

        # Create annotated frame on original-resolution image
        annotated_path = self._create_annotated_frame(frame_path, img, analysis)
        
        # Store downscaled grayscale for next iteration
        self._prev_gray = gray_small
        self._prev_frame = frame_path
        
        return analysis, annotated_path
    
    def _detect_motion(self, current: 'Image', previous: 'Image') -> Dict:
        """Detect motion between frames"""
        try:
            from PIL import ImageChops
            
            # Resize if needed
            if current.size != previous.size:
                previous = previous.resize(current.size)
            
            # Compute difference
            diff = ImageChops.difference(current, previous)
            
            # Get histogram
            histogram = diff.histogram()
            
            # Count changed pixels above threshold
            changed_pixels = sum(histogram[self.threshold:])
            total_pixels = sum(histogram)
            motion_percent = (changed_pixels / total_pixels * 100) if total_pixels > 0 else 0
            
            has_motion = motion_percent > 0.5
            
            # Find motion regions
            regions = []
            if has_motion:
                regions = self._find_motion_regions(diff)
            
            return {
                "has_motion": has_motion,
                "motion_percent": round(motion_percent, 2),
                "motion_regions": regions,
            }
        except Exception as e:
            logger.debug(f"Motion detection error: {e}")
            return {"has_motion": False, "motion_percent": 0, "motion_regions": []}
    
    def _find_motion_regions(self, diff_img: 'Image') -> List[Dict]:
        """Find regions with significant motion"""
        regions = []
        width, height = diff_img.size
        grid_size = 8
        cell_w = width // grid_size
        cell_h = height // grid_size
        
        for gy in range(grid_size):
            for gx in range(grid_size):
                x1, y1 = gx * cell_w, gy * cell_h
                x2, y2 = x1 + cell_w, y1 + cell_h
                
                cell = diff_img.crop((x1, y1, x2, y2))
                hist = cell.histogram()
                changed = sum(hist[self.threshold:])
                total = sum(hist)
                
                if total > 0 and (changed / total) > 0.1:
                    regions.append({
                        "x": x1, "y": y1, "w": cell_w, "h": cell_h,
                        "intensity": round(changed / total, 2),
                        "position": self._get_position_name(gx, gy, grid_size)
                    })
        
        return regions
    
    def _detect_edges(self, gray: 'Image') -> Dict:
        """Detect edges to identify object boundaries"""
        try:
            # Apply edge detection filter
            edges = gray.filter(ImageFilter.FIND_EDGES)
            
            # Find vertical edges (often indicate standing people)
            objects = []
            width, height = edges.size
            
            # Scan for vertical edge patterns
            for x in range(0, width, width // 8):
                col_sum = 0
                for y in range(height):
                    pixel = edges.getpixel((min(x, width-1), y))
                    if pixel > 50:
                        col_sum += 1
                
                if col_sum > height * 0.3:  # Strong vertical edge
                    objects.append({
                        "type": "vertical_edge",
                        "x": x,
                        "strength": col_sum / height
                    })
            
            return {"objects": objects}
        except Exception as e:
            logger.debug(f"Edge detection error: {e}")
            return {"objects": []}
    
    def _analyze_for_person(self, analysis: Dict, img_size: Tuple[int, int]) -> Dict:
        """Analyze motion patterns to determine if person is present"""
        regions = analysis.get("motion_regions", [])
        motion_pct = analysis.get("motion_percent", 0)
        
        if not regions:
            return {"likely_person": False, "person_confidence": 0.0}
        
        # Heuristics for person detection:
        # 1. Motion in upper part (head/torso)
        # 2. Vertical motion pattern
        # 3. Medium-sized motion area (not tiny noise, not huge scene change)
        
        confidence = 0.0
        width, height = img_size
        
        # Check for motion in person-likely areas
        upper_motion = [r for r in regions if r["y"] < height * 0.6]
        if upper_motion:
            confidence += 0.3
        
        # Check motion intensity (person moves moderately)
        if 0.5 < motion_pct < 15:
            confidence += 0.2
        
        # Check for multiple adjacent regions (body shape)
        if 2 <= len(regions) <= 8:
            confidence += 0.2
        
        # Check for consistent motion area (not scattered)
        if regions:
            xs = [r["x"] for r in regions]
            ys = [r["y"] for r in regions]
            spread_x = (max(xs) - min(xs)) / width
            spread_y = (max(ys) - min(ys)) / height
            
            if 0.1 < spread_x < 0.5 and 0.1 < spread_y < 0.6:
                confidence += 0.3
        
        return {
            "likely_person": confidence > 0.5,
            "person_confidence": round(confidence, 2)
        }
    
    def _get_position_name(self, gx: int, gy: int, grid: int) -> str:
        """Convert grid position to human-readable location"""
        h_pos = "left" if gx < grid // 3 else ("right" if gx >= grid * 2 // 3 else "center")
        v_pos = "top" if gy < grid // 3 else ("bottom" if gy >= grid * 2 // 3 else "middle")
        return f"{v_pos}-{h_pos}"
    
    def _create_annotated_frame(self, original_path: Path, img: 'Image', analysis: Dict) -> Path:
        """Create annotated frame with motion regions highlighted"""
        try:
            from PIL import ImageDraw, ImageFont
            
            annotated = img.copy()
            draw = ImageDraw.Draw(annotated)
            
            # Draw motion regions
            for region in analysis.get("motion_regions", []):
                x, y, w, h = region["x"], region["y"], region["w"], region["h"]
                intensity = region.get("intensity", 0.5)
                
                # Color based on intensity (green to red)
                r = int(255 * intensity)
                g = int(255 * (1 - intensity))
                color = (r, g, 0, 128)
                
                draw.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=2)
            
            # Add analysis info overlay
            info_text = []
            if analysis.get("has_motion"):
                info_text.append(f"Motion: {analysis['motion_percent']:.1f}%")
            if analysis.get("likely_person"):
                info_text.append(f"Person likely ({analysis['person_confidence']:.0%})")
            
            if info_text:
                # Draw semi-transparent background
                text = " | ".join(info_text)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
                except:
                    font = ImageFont.load_default()
                
                bbox = draw.textbbox((10, 10), text, font=font)
                draw.rectangle([bbox[0]-5, bbox[1]-5, bbox[2]+5, bbox[3]+5], fill=(0, 0, 0, 180))
                draw.text((10, 10), text, fill=(255, 255, 0), font=font)
            
            # Save annotated frame
            annotated_path = original_path.parent / f"annotated_{original_path.name}"
            annotated.save(annotated_path, quality=90)
            
            return annotated_path
            
        except Exception as e:
            logger.debug(f"Annotation failed: {e}")
            return original_path


@dataclass
class Trigger:
    """Trigger condition for alerts"""
    condition: str  # Text description of what to watch for
    action: str = "speak"  # speak, alert, webhook, record
    webhook_url: Optional[str] = None
    cooldown: float = 30.0  # Minimum seconds between triggers
    last_triggered: float = 0.0


@dataclass
class NarrationEntry:
    """Single narration entry"""
    timestamp: datetime
    frame_num: int
    description: str
    image_base64: str = ""  # Original frame in base64
    annotated_base64: str = ""  # Frame with motion annotations (what LLM sees)
    analysis_data: Dict = field(default_factory=dict)  # Motion/edge analysis data
    triggered: bool = False
    trigger_matches: List[str] = field(default_factory=list)


@register("live")
@register("narrator")
class LiveNarratorComponent(Component):
    """
    Real-time stream narration with TTS and triggers.
    
    Operations:
        - narrator: Full narration with TTS
        - watch: Watch for specific triggers only
        - describe: Describe current frame (single shot)
        - history: Get narration history
    
    URI Examples:
        live://narrator?source=rtsp://camera/live&tts=true
        live://watch?source=rtsp://camera/live&trigger=person appears
        live://describe?source=rtsp://camera/live
    
    Triggers:
        Comma-separated conditions to watch for:
        trigger=person appears,someone enters,package delivered
        
        When triggered, the system will:
        - Speak the alert (if tts=true)
        - Send webhook (if webhook_url set)
        - Log to history
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "narrator"
        self.source = uri.get_param("source", uri.get_param("url", ""))
        
        def str_to_bool(val, default=False):
            """Convert string/bool to bool safely"""
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes")
            return default
        
        # TTS settings (use config defaults, can be overridden via URI)
        self.tts_enabled = str_to_bool(uri.get_param("tts", "false"))
        self.tts_engine = uri.get_param("tts_engine", config.get("SQ_TTS_ENGINE", "auto"))
        self.tts_voice = uri.get_param("tts_voice", config.get("SQ_TTS_VOICE", ""))
        self.tts_rate = int(uri.get_param("tts_rate", config.get("SQ_TTS_RATE", "150")))
        
        # Get defaults from config
        default_model = config.get("SQ_MODEL", "llava:7b")
        default_duration = config.get("SQ_STREAM_DURATION", "60")
        
        # Descriptive parameters (analysis, motion, frames)
        from ..presets import get_descriptive_preset, ANALYSIS_PRESETS, MOTION_PRESETS, FRAME_PRESETS
        
        analysis = uri.get_param("analysis", "normal")
        motion = uri.get_param("motion", "significant")
        frames_mode = uri.get_param("frames_mode", "changed")
        focus_param = uri.get_param("focus", config.get("SQ_STREAM_FOCUS", ""))
        
        # Get combined preset from descriptive params
        preset = get_descriptive_preset(
            analysis=analysis,
            motion=motion,
            frames=frames_mode,
            focus=focus_param or "general"
        )
        
        # Store descriptive params for output
        self.analysis_mode = analysis
        self.motion_mode = motion
        self.frames_mode = frames_mode
        
        # Analysis settings (use preset or explicit values)
        self.interval = float(uri.get_param("interval", str(preset["interval"])))
        self.duration = int(uri.get_param("duration", default_duration))
        self.model = uri.get_param("model", default_model)
        self.focus = preset["focus"] if preset["focus"] != "general" else focus_param
        
        # Mode: full (describe everything), diff (only changes), track (track focus object)
        self.mode = uri.get_param("mode", config.get("SQ_STREAM_MODE", "full"))
        
        # Diff settings (use preset or explicit values)
        self.use_diff = str_to_bool(uri.get_param("diff", "true"), True)
        self.diff_threshold = int(uri.get_param("threshold", str(preset["threshold"])))
        self.min_change = float(uri.get_param("min_change", str(preset["min_change"])))
        self.edge_detect = preset.get("edge_detect", False)
        self.ai_detail = preset.get("ai_detail", "normal")
        
        # LLM settings from config
        self.ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        self.llm_timeout = int(config.get("SQ_LLM_TIMEOUT", "30"))
        
        # Previous description for diff mode
        self._prev_description = ""
        
        # Triggers
        trigger_str = uri.get_param("trigger", "")
        self.triggers = self._parse_triggers(trigger_str)
        self.webhook_url = uri.get_param("webhook_url", "")
        
        # Language
        self.language = uri.get_param("lang", "en")
        
        # Quiet mode - suppress live output
        self.quiet = str_to_bool(uri.get_param("quiet", "false"))
        
        # Advanced analysis
        self.use_advanced = str_to_bool(uri.get_param("advanced", "true"), True)
        self._frame_analyzer = FrameAnalyzer(threshold=self.diff_threshold)
        
        # Optional directory to persist captured frames
        self.frames_dir = uri.get_param("frames_dir", "")
        self._frames_output_dir: Optional[Path] = None
        
        # State
        self._temp_dir = None
        self._prev_frame = None
        self._history: List[NarrationEntry] = []
        self._running = False
        self._tts_queue = []
        self._last_description = ""
        self._last_analysis = {}
    
    def _parse_triggers(self, trigger_str: str) -> List[Trigger]:
        """Parse trigger conditions from string"""
        if not trigger_str:
            return []
        
        triggers = []
        for condition in trigger_str.split(","):
            condition = condition.strip()
            if condition:
                triggers.append(Trigger(condition=condition))
        return triggers
    
    def process(self, data: Any) -> Dict:
        """Process live narration"""
        if not self.source:
            raise ComponentError("Source URL is required for live narration (source param is empty)")
            
        self._temp_dir = Path(tempfile.mkdtemp())
        self._running = True

        # Prepare output directory for persisted frames (if configured)
        if self.frames_dir:
            try:
                out_dir = Path(self.frames_dir).expanduser()
                out_dir.mkdir(parents=True, exist_ok=True)
                self._frames_output_dir = out_dir
            except Exception as e:
                logger.warning(f"Failed to create frames_dir '{self.frames_dir}': {e}")
                self._frames_output_dir = None
        else:
            self._frames_output_dir = None
        
        try:
            if self.operation == "narrator":
                return self._run_narrator()
            elif self.operation == "watch":
                return self._run_watch()
            elif self.operation == "describe":
                return self._describe_single()
            elif self.operation == "history":
                return self._get_history()
            else:
                raise ComponentError(f"Unknown operation: {self.operation}")
        finally:
            self._running = False
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def _run_narrator(self) -> Dict:
        """Run continuous narration with TTS and advanced analysis"""
        start_time = time.time()
        frame_num = 0
        
        while time.time() - start_time < self.duration and self._running:
            frame_num += 1
            frame_path = self._capture_frame(frame_num)
            
            if not frame_path or not frame_path.exists():
                time.sleep(self.interval)
                continue
            
            # Advanced frame analysis (motion, edges, person detection)
            frame_analysis = {}
            annotated_frame = frame_path
            
            if self.use_advanced:
                frame_analysis, annotated_frame = self._frame_analyzer.analyze(frame_path)
                self._last_analysis = frame_analysis
                
                motion_pct = frame_analysis.get("motion_percent", 0)
                has_motion = frame_analysis.get("has_motion", True)
                
                # Skip LLM completely if no motion detected (save API calls)
                if frame_num > 1 and not has_motion:
                    if not self.quiet:
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"⚪ [{ts}] No motion (skipping LLM)")
                    self._prev_frame = frame_path
                    time.sleep(self.interval)
                    continue
                
                # Very low motion - respond without LLM call
                if motion_pct < 0.5 and frame_num > 1:
                    description = "No significant motion"
                    self._prev_frame = frame_path
                    if not self.quiet:
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"⚪ [{ts}] {description}")
                    time.sleep(self.interval)
                    continue
            else:
                # Fallback to simple diff
                if self.use_diff and self._prev_frame:
                    change_pct = self._compute_change(frame_path)
                    if change_pct < self.min_change:
                        self._prev_frame = frame_path
                        time.sleep(self.interval)
                        continue
            
            # Get AI description with analysis context (only when motion detected)
            description = self._describe_frame_advanced(
                annotated_frame or frame_path, 
                frame_analysis
            )
            
            # Check for duplicates
            if description and description != self._last_description:
                self._last_description = description
                
                # Check triggers
                triggered, matches = self._check_triggers(description)
                
                # Encode BOTH original and annotated frames for report
                original_base64 = ""
                annotated_base64 = ""
                try:
                    with open(frame_path, "rb") as f:
                        original_base64 = base64.b64encode(f.read()).decode()
                    if annotated_frame and annotated_frame != frame_path:
                        with open(annotated_frame, "rb") as f:
                            annotated_base64 = base64.b64encode(f.read()).decode()
                except Exception:
                    pass
                
                # Create entry with analysis data
                entry = NarrationEntry(
                    timestamp=datetime.now(),
                    frame_num=frame_num,
                    description=description,
                    image_base64=original_base64,
                    annotated_base64=annotated_base64,
                    analysis_data=frame_analysis,
                    triggered=triggered,
                    trigger_matches=matches
                )
                self._history.append(entry)
                
                # Output (only if not quiet)
                if not self.quiet:
                    ts = entry.timestamp.strftime("%H:%M:%S")
                    analysis_info = ""
                    if frame_analysis:
                        motion = frame_analysis.get("motion_percent", 0)
                        person_conf = frame_analysis.get("person_confidence", 0)
                        analysis_info = f" [motion:{motion:.1f}% person:{person_conf:.0%}]"
                    
                    if triggered:
                        print(f"🔴 [{ts}]{analysis_info} TRIGGER: {', '.join(matches)}")
                        print(f"   {description[:200]}...")
                    else:
                        print(f"📝 [{ts}]{analysis_info} {description[:120]}...")
                
                # Speak (TTS works even in quiet mode)
                if self.tts_enabled:
                    if triggered:
                        self._speak(f"Alert! {matches[0]}")
                    else:
                        self._speak(description[:200])
                
                # Webhook
                if triggered and self.webhook_url:
                    self._send_webhook(entry)
            
            self._prev_frame = frame_path
            time.sleep(self.interval)
        
        # Summary
        triggered_count = sum(1 for e in self._history if e.triggered)
        
        return {
            "success": True,
            "operation": "narrator",
            # Configuration
            "config": {
                "source": self.source,
                "model": self.model,
                "mode": self.mode,
                "focus": self.focus or "general",
                # Descriptive parameters
                "analysis": self.analysis_mode,
                "motion": self.motion_mode,
                "frames": self.frames_mode,
                "ai_detail": self.ai_detail,
                # Derived numeric values
                "interval": self.interval,
                "duration": self.duration,
                "threshold": self.diff_threshold,
                "min_change": self.min_change,
                "edge_detect": self.edge_detect,
                # Other
                "tts_enabled": self.tts_enabled,
                "advanced_analysis": self.use_advanced,
            },
            # Last frame analysis
            "last_analysis": self._last_analysis,
            # Results
            "frames_analyzed": frame_num,
            "descriptions": len(self._history),
            "triggers_fired": triggered_count,
            "triggers": [t.condition for t in self.triggers],
            # History with images
            "history": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "frame": e.frame_num,
                    "description": e.description,
                    "image_base64": e.image_base64,  # Original frame
                    "annotated_base64": e.annotated_base64,  # What LLM saw (with motion boxes)
                    "analysis": e.analysis_data,  # Motion/edge detection results
                    "triggered": e.triggered,
                    "matches": e.trigger_matches
                }
                for e in self._history
            ]
        }
    
    def _run_watch(self) -> Dict:
        """Watch for specific triggers only (no continuous narration)"""
        if not self.triggers:
            return {"error": "No triggers defined. Use trigger=condition1,condition2"}
        
        print(f"\n👁️ Watching for triggers...")
        print(f"   Conditions: {[t.condition for t in self.triggers]}")
        print()
        
        start_time = time.time()
        frame_num = 0
        alerts = []
        
        while time.time() - start_time < self.duration and self._running:
            frame_num += 1
            frame_path = self._capture_frame(frame_num)
            
            if not frame_path or not frame_path.exists():
                time.sleep(self.interval)
                continue
            
            # Quick change check
            if self.use_diff and self._prev_frame:
                change_pct = self._compute_change(frame_path)
                if change_pct < self.min_change:
                    self._prev_frame = frame_path
                    time.sleep(self.interval)
                    continue
            
            # Optional advanced analysis for region-based cropping
            analysis: Dict = {}
            if self.use_advanced:
                try:
                    analysis, _ = self._frame_analyzer.analyze(frame_path)
                    self._last_analysis = analysis
                except Exception as e:  # pragma: no cover - best effort
                    logger.debug(f"Frame analysis in watch mode failed: {e}")
                    analysis = {}

            # Ask LLM about triggers specifically, using cropped frame if possible
            description = self._check_triggers_with_llm(frame_path, analysis)
            
            if description:
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"🔴 [{ts}] ALERT: {description[:150]}...")
                
                alerts.append({
                    "timestamp": ts,
                    "frame": frame_num,
                    "description": description
                })
                
                if self.tts_enabled:
                    self._speak(f"Alert! {description[:100]}")
            
            self._prev_frame = frame_path
            time.sleep(self.interval)
        
        return {
            "success": True,
            "operation": "watch",
            "triggers": [t.condition for t in self.triggers],
            "frames_checked": frame_num,
            "alerts": alerts
        }
    
    def _describe_single(self) -> Dict:
        """Describe single frame"""
        frame_path = self._capture_frame(0)
        
        if not frame_path or not frame_path.exists():
            return {"error": "Failed to capture frame"}
        
        description = self._describe_frame(frame_path)
        
        if self.tts_enabled and description:
            self._speak(description[:300])
        
        return {
            "success": True,
            "operation": "describe",
            "description": description,
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_history(self) -> Dict:
        """Get narration history"""
        return {
            "success": True,
            "operation": "history",
            "count": len(self._history),
            "history": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "frame": e.frame_num,
                    "description": e.description,
                    "triggered": e.triggered
                }
                for e in self._history
            ]
        }
    
    def _capture_frame(self, frame_num: int) -> Optional[Path]:
        """Capture frame from source"""
        output_path = self._temp_dir / f"frame_{frame_num:05d}.jpg"
        
        try:
            if self.source.startswith("rtsp://"):
                cmd = [
                    "ffmpeg", "-y", "-rtsp_transport", "tcp",
                    "-i", self.source,
                    "-frames:v", "1",
                    "-q:v", "2",
                    str(output_path)
                ]
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.source,
                    "-frames:v", "1",
                    str(output_path)
                ]
            
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)

            # Optionally persist a copy of the frame to user-specified directory
            if self._frames_output_dir:
                try:
                    dest_path = self._frames_output_dir / output_path.name
                    # Simple copy without introducing new imports
                    with open(output_path, "rb") as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                except Exception as copy_err:
                    logger.debug(f"Failed to save frame copy to {self._frames_output_dir}: {copy_err}")

            return output_path
        except Exception as e:
            logger.warning(f"Frame capture failed: {e}")
            return None
    
    def _compute_change(self, current_frame: Path) -> float:
        """Compute change percentage between frames"""
        try:
            from PIL import Image, ImageChops
            
            img1 = Image.open(self._prev_frame).convert('L')
            img2 = Image.open(current_frame).convert('L')
            
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)
            
            diff = ImageChops.difference(img1, img2)
            
            # Try numpy first, fallback to PIL
            try:
                import numpy as np
                diff_array = np.array(diff)
                diff_binary = (diff_array > self.diff_threshold).astype(np.uint8)
                change_pct = (np.sum(diff_binary) / diff_binary.size) * 100
            except ImportError:
                # Fallback without numpy - use PIL histogram
                histogram = diff.histogram()
                # Sum pixels above threshold
                changed_pixels = sum(histogram[self.diff_threshold:])
                total_pixels = sum(histogram)
                change_pct = (changed_pixels / total_pixels) * 100 if total_pixels > 0 else 0
            
            return change_pct
            
        except Exception as e:
            logger.debug(f"Change computation: {e}")
            return 100  # Assume change on error

    def _crop_to_motion_regions(self, frame_path: Path, analysis: Dict) -> Path:
        """Return cropped frame focusing on motion regions, or original frame if none.

        Uses motion_regions from FrameAnalyzer (in original image coordinates) to
        compute a bounding box with small margin. This reduces the area sent to
        the vision LLM and focuses it on where changes occurred.
        """
        regions = analysis.get("motion_regions") or []
        if not regions:
            return frame_path

        try:
            from PIL import Image
        except ImportError:
            return frame_path

        try:
            img = Image.open(frame_path)
            width, height = img.size

            xs: List[int] = []
            ys: List[int] = []
            xe: List[int] = []
            ye: List[int] = []

            for region in regions:
                x = max(0, int(region.get("x", 0)))
                y = max(0, int(region.get("y", 0)))
                w = max(0, int(region.get("w", 0)))
                h = max(0, int(region.get("h", 0)))
                if w <= 0 or h <= 0:
                    continue
                xs.append(x)
                ys.append(y)
                xe.append(x + w)
                ye.append(y + h)

            if not xs:
                return frame_path

            margin = 20
            x1 = max(0, min(xs) - margin)
            y1 = max(0, min(ys) - margin)
            x2 = min(width, max(xe) + margin)
            y2 = min(height, max(ye) + margin)

            if x2 <= x1 or y2 <= y1:
                return frame_path

            cropped = img.crop((x1, y1, x2, y2))

            # Save cropped frame into component temp directory so it is cleaned up
            if not self._temp_dir:
                return frame_path
            crop_path = self._temp_dir / f"crop_{frame_path.name}"
            cropped.save(crop_path, quality=90)
            return crop_path

        except Exception as e:
            logger.debug(f"Motion crop failed: {e}")
            return frame_path
    
    def _describe_frame(self, frame_path: Path, prev_frame_path: Path = None) -> str:
        """Get AI description of frame based on mode"""
        try:
            import requests
            
            # Optimize image before sending to LLM
            from ..image_optimize import prepare_image_for_llm_base64
            image_data = prepare_image_for_llm_base64(frame_path, preset="balanced")
            
            # Build prompt based on mode
            if self.mode == "diff" and self._prev_description:
                # Diff mode - describe only changes
                prompt = self._build_diff_prompt()
            elif self.mode == "track" and self.focus:
                # Track mode - focus on specific object
                prompt = self._build_track_prompt()
            else:
                # Full mode - describe everything
                prompt = self._build_full_prompt()

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=self.llm_timeout
            )
            
            if response.ok:
                desc = response.json().get("response", "").strip()
                self._prev_description = desc
                return desc
            return ""
            
        except Exception as e:
            logger.warning(f"Description failed: {e}")
            return ""
    
    def _describe_frame_advanced(self, frame_path: Path, analysis: Dict) -> str:
        """Get AI description with preprocessed analysis context"""
        try:
            from ..llm_client import get_client
            
            # Crop to motion regions if available to focus LLM on changes
            crop_path = self._crop_to_motion_regions(frame_path, analysis or {})
            
            # Build context-aware prompt
            prompt = self._build_advanced_prompt(analysis)
            
            # Use centralized LLM client
            client = get_client()
            result = client.analyze_image(crop_path, prompt, model=self.model)
            
            if result.get("success"):
                desc = result.get("response", "").strip()
                self._prev_description = desc
                return desc
            return ""
            
        except Exception as e:
            logger.warning(f"Advanced description failed: {e}")
            return self._describe_frame(frame_path)  # Fallback
    
    def _build_advanced_prompt(self, analysis: Dict) -> str:
        """Build prompt with motion/edge analysis context"""
        
        # Base context from analysis
        context_parts = []
        
        motion_pct = analysis.get("motion_percent", 0)
        has_motion = analysis.get("has_motion", False)
        regions = analysis.get("motion_regions", [])
        likely_person = analysis.get("likely_person", False)
        person_conf = analysis.get("person_confidence", 0)
        
        if has_motion:
            context_parts.append(f"Motion detected: {motion_pct:.1f}% of frame changed")
            
            # Describe motion locations
            if regions:
                positions = list(set(r.get("position", "") for r in regions))
                context_parts.append(f"Motion areas: {', '.join(positions)}")
        
        if likely_person:
            context_parts.append(f"Pre-analysis suggests person present ({person_conf:.0%} confidence)")
        
        context = "\n".join(context_parts) if context_parts else "No pre-analysis data"
        
        # Build mode-specific prompt with context
        if self.mode == "track" and self.focus:
            focus_obj = self.focus.lower()
            prev_info = f'\nPrevious: "{self._prev_description[:60]}"' if self._prev_description else ""
            
            if focus_obj in ("person", "people", "human"):
                return f"""ANALYSIS CONTEXT:
{context}

IMAGE: This security camera frame has red rectangles marking areas where motion was detected.
{prev_info}

TASK: Based on the motion analysis and image, is there a PERSON in this frame?

If motion analysis shows "likely person" OR you see a person:
- Describe WHERE the person is (use the motion regions as hints)
- Describe WHAT they are doing
- Note if they are sitting, standing, walking

If no person is visible despite motion: describe what caused the motion.
If no motion: say "No movement detected"

Be specific and concise."""
            else:
                return f"""ANALYSIS: {context}{prev_info}

Looking for: {self.focus}
Describe if {self.focus} is present and its state."""

        elif self.mode == "diff":
            return f"""ANALYSIS CONTEXT:
{context}

Previous description: "{self._prev_description[:150]}"

Based on the motion analysis (red rectangles show changed areas):
- Describe ONLY what changed
- Focus on: {self.focus if self.focus else 'any changes'}
- If person moved, describe the movement
- Be very brief"""

        else:  # full mode
            return f"""ANALYSIS CONTEXT:
{context}

Describe what you see in this security camera image.
Red rectangles mark areas where motion was detected.

Include:
- Any people and what they're doing
- The location/room type  
- Any notable activity

Be concise (2-3 sentences)."""
    
    def _build_full_prompt(self) -> str:
        """Build prompt for full description mode"""
        from ..prompts import render_prompt
        return render_prompt("live_narrator_full", focus=self.focus or "general scene")

    def _build_diff_prompt(self) -> str:
        """Build prompt for diff mode - only describe changes"""
        from ..prompts import render_prompt
        prev = self._prev_description[:150] if self._prev_description else "none"
        return render_prompt("live_narrator_diff", focus=self.focus or "any", prev_description=prev)

    def _build_track_prompt(self) -> str:
        """Build prompt for tracking specific object (e.g., person)"""
        from ..prompts import render_prompt
        return render_prompt("live_narrator_track", focus=self.focus)
    
    def _check_triggers_with_llm(self, frame_path: Path, analysis: Optional[Dict] = None) -> Optional[str]:
        """Check if any triggers match using LLM.

        If motion analysis data is available, crop the frame to motion regions
        before sending to the vision model so it focuses on areas where
        something is happening.
        """
        try:
            import requests
            
            # If no analysis provided but advanced mode is enabled, compute it
            if analysis is None and self.use_advanced:
                try:
                    analysis, _ = self._frame_analyzer.analyze(frame_path)
                except Exception as e:  # pragma: no cover - best effort
                    logger.debug(f"Trigger analysis failed, using full frame: {e}")
                    analysis = {}

            crop_path = self._crop_to_motion_regions(frame_path, analysis or {})

            # Optimize image before sending to LLM (fast preset for trigger checks)
            from ..image_optimize import prepare_image_for_llm_base64
            image_data = prepare_image_for_llm_base64(crop_path, preset="fast")
            
            from ..prompts import render_prompt
            
            conditions = [t.condition for t in self.triggers]
            conditions_text = "\n".join(f"- {c}" for c in conditions)
            
            prompt = render_prompt("trigger_check", conditions=conditions_text)

            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=self.llm_timeout
            )
            
            if response.ok:
                result = response.json().get("response", "").strip()
                if result.upper().startswith("NO"):
                    return None
                return result
            return None
            
        except Exception as e:
            logger.warning(f"Trigger check failed: {e}")
            return None
    
    def _check_triggers(self, description: str) -> tuple[bool, List[str]]:
        """Check if description matches any triggers"""
        matches = []
        description_lower = description.lower()
        
        for trigger in self.triggers:
            # Simple keyword matching
            condition_words = trigger.condition.lower().split()
            if all(word in description_lower for word in condition_words):
                # Check cooldown
                if time.time() - trigger.last_triggered >= trigger.cooldown:
                    matches.append(trigger.condition)
                    trigger.last_triggered = time.time()
        
        return len(matches) > 0, matches
    
    def _speak(self, text: str):
        """Speak text using unified TTS module."""
        try:
            from ..tts import speak
            speak(text, engine=self.tts_engine, rate=self.tts_rate, voice=self.tts_voice)
        except Exception as e:
            logger.warning(f"TTS failed: {e}")
    
    def _send_webhook(self, entry: NarrationEntry):
        """Send webhook notification"""
        if not self.webhook_url:
            return
        
        try:
            import requests
            
            payload = {
                "timestamp": entry.timestamp.isoformat(),
                "description": entry.description,
                "triggers": entry.trigger_matches,
                "source": self.source
            }
            
            requests.post(self.webhook_url, json=payload, timeout=5)
            
        except Exception as e:
            logger.warning(f"Webhook failed: {e}")


# ============================================================================
# Helper Functions
# ============================================================================

def live_narrator(source: str, duration: int = 60, tts: bool = False, 
                  trigger: str = "", **kwargs) -> Dict:
    """
    Start live narration of video stream.
    
    Args:
        source: Video source (RTSP URL, file, etc.)
        duration: How long to run (seconds)
        tts: Enable text-to-speech
        trigger: Comma-separated trigger conditions
    
    Example:
        result = live_narrator("rtsp://camera/live", 120, tts=True,
                               trigger="person appears,door opens")
    """
    from ..core import flow
    
    params = f"source={source}&duration={duration}"
    params += f"&tts={'true' if tts else 'false'}"
    if trigger:
        params += f"&trigger={trigger}"
    
    for k, v in kwargs.items():
        params += f"&{k}={v}"
    
    return flow(f"live://narrator?{params}").run()


def watch_for(source: str, conditions: List[str], duration: int = 300,
              tts: bool = True) -> Dict:
    """
    Watch stream for specific conditions.
    
    Args:
        source: Video source
        conditions: List of conditions to watch for
        duration: How long to watch (seconds)
        tts: Speak alerts
    
    Example:
        result = watch_for("rtsp://camera/live",
                           ["person at door", "package delivered"],
                           duration=600, tts=True)
    """
    from ..core import flow
    
    trigger = ",".join(conditions)
    params = f"source={source}&trigger={trigger}&duration={duration}"
    params += f"&tts={'true' if tts else 'false'}"
    
    return flow(f"live://watch?{params}").run()


def describe_now(source: str, tts: bool = False) -> str:
    """
    Get immediate description of current frame.
    
    Example:
        description = describe_now("rtsp://camera/live", tts=True)
        print(description)
    """
    from ..core import flow
    
    result = flow(f"live://describe?source={source}&tts={'true' if tts else 'false'}").run()
    return result.get("description", "")
