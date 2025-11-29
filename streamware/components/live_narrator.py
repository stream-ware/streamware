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
        """
        Analyze frame for motion and objects.
        Returns analysis dict and path to annotated frame.
        """
        try:
            from PIL import Image, ImageDraw, ImageFilter, ImageOps
        except ImportError:
            return {"error": "PIL not installed"}, None
        
        img = Image.open(frame_path)
        gray = img.convert('L')
        
        analysis = {
            "has_motion": False,
            "motion_percent": 0.0,
            "motion_regions": [],
            "edge_objects": [],
            "likely_person": False,
            "person_confidence": 0.0,
        }
        
        # Motion detection
        if self._prev_gray is not None:
            motion_data = self._detect_motion(gray, self._prev_gray)
            analysis.update(motion_data)
        
        # Edge detection for object boundaries
        edge_data = self._detect_edges(gray)
        analysis["edge_objects"] = edge_data.get("objects", [])
        
        # Analyze if motion pattern suggests person
        if analysis["has_motion"]:
            person_analysis = self._analyze_for_person(analysis, img.size)
            analysis.update(person_analysis)
        
        # Create annotated frame
        annotated_path = self._create_annotated_frame(frame_path, img, analysis)
        
        # Store for next iteration
        self._prev_gray = gray
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
    image_base64: str = ""  # Frame image in base64
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
        
        # TTS settings
        self.tts_enabled = str_to_bool(uri.get_param("tts", "false"))
        self.tts_engine = uri.get_param("tts_engine", "espeak")
        self.tts_rate = int(uri.get_param("tts_rate", "150"))
        
        # Get defaults from config
        default_model = config.get("SQ_MODEL", "llava:7b")
        default_interval = config.get("SQ_STREAM_INTERVAL", "3")
        default_duration = config.get("SQ_STREAM_DURATION", "60")
        default_threshold = config.get("SQ_MOTION_THRESHOLD", "15")
        default_min_change = config.get("SQ_MIN_CHANGE", "0.5")
        default_sensitivity = config.get("SQ_SENSITIVITY", "medium")
        
        # Sensitivity preset (descriptive parameter)
        sensitivity = uri.get_param("sensitivity", default_sensitivity)
        sensitivity_presets = {
            "ultra":   {"threshold": 3,  "min_change": 0.1, "interval": 1},
            "high":    {"threshold": 8,  "min_change": 0.3, "interval": 2},
            "medium":  {"threshold": 15, "min_change": 0.5, "interval": 3},
            "low":     {"threshold": 25, "min_change": 1.0, "interval": 5},
            "minimal": {"threshold": 40, "min_change": 2.0, "interval": 10},
        }
        preset = sensitivity_presets.get(sensitivity, sensitivity_presets["medium"])
        
        # Analysis settings (use preset or explicit values)
        self.interval = float(uri.get_param("interval", str(preset["interval"])))
        self.duration = int(uri.get_param("duration", default_duration))
        self.model = uri.get_param("model", default_model)
        self.focus = uri.get_param("focus", config.get("SQ_STREAM_FOCUS", ""))
        self.sensitivity = sensitivity
        
        # Mode: full (describe everything), diff (only changes), track (track focus object)
        self.mode = uri.get_param("mode", config.get("SQ_STREAM_MODE", "full"))
        
        # Diff settings (use preset or explicit values)
        self.use_diff = str_to_bool(uri.get_param("diff", "true"), True)
        self.diff_threshold = int(uri.get_param("threshold", str(preset["threshold"])))
        self.min_change = float(uri.get_param("min_change", str(preset["min_change"])))
        
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
        self._temp_dir = Path(tempfile.mkdtemp())
        self._running = True
        
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
                
                # Skip if no motion and not first frame
                if frame_num > 1 and not frame_analysis.get("has_motion", True):
                    if not self.quiet:
                        print(f"   Frame {frame_num}: No motion detected")
                    self._prev_frame = frame_path
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
            
            # Get AI description with analysis context
            description = self._describe_frame_advanced(
                annotated_frame or frame_path, 
                frame_analysis
            )
            
            # Check for duplicates
            if description and description != self._last_description:
                self._last_description = description
                
                # Check triggers
                triggered, matches = self._check_triggers(description)
                
                # Encode annotated frame to base64 for report
                img_base64 = ""
                try:
                    img_to_encode = annotated_frame or frame_path
                    with open(img_to_encode, "rb") as f:
                        img_base64 = base64.b64encode(f.read()).decode()
                except Exception:
                    pass
                
                # Create entry with analysis data
                entry = NarrationEntry(
                    timestamp=datetime.now(),
                    frame_num=frame_num,
                    description=description,
                    image_base64=img_base64,
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
                "tts_enabled": self.tts_enabled,
                "tts_engine": self.tts_engine if self.tts_enabled else None,
                "interval": self.interval,
                "duration": self.duration,
                "diff_threshold": self.diff_threshold,
                "min_change": self.min_change,
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
                    "image_base64": e.image_base64,
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
            
            # Ask LLM about triggers specifically
            description = self._check_triggers_with_llm(frame_path)
            
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
    
    def _describe_frame(self, frame_path: Path, prev_frame_path: Path = None) -> str:
        """Get AI description of frame based on mode"""
        try:
            import requests
            
            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
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
            import requests
            
            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # Build context-aware prompt
            prompt = self._build_advanced_prompt(analysis)
            
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
        focus_text = f"Focus on: {self.focus}. " if self.focus else ""
        return f"""{focus_text}Describe what you see in this image concisely.
Include:
- People present and what they're doing
- Objects and their positions
- Any movement or activity
- Anything unusual or notable

Be specific and brief (2-3 sentences max)."""

    def _build_diff_prompt(self) -> str:
        """Build prompt for diff mode - only describe changes"""
        focus_text = f"Focus on changes related to: {self.focus}. " if self.focus else ""
        return f"""{focus_text}Previous scene: "{self._prev_description[:200]}"

Describe ONLY what has CHANGED since the previous description.
- If nothing changed, say "No changes"
- If person moved, describe the movement
- If new object appeared/disappeared, mention it
- Ignore minor lighting changes

Be very brief - only mention actual changes."""

    def _build_track_prompt(self) -> str:
        """Build prompt for tracking specific object (e.g., person)"""
        prev_info = f' Previous: "{self._prev_description[:60]}"' if self._prev_description else ""
        
        if self.focus.lower() in ("person", "people", "human"):
            return f"""Is there a person in this image? Look carefully at all areas including people sitting at desks.{prev_info}

If YES: Describe where the person is and what they are doing.
If NO: Say "No person visible"."""
        else:
            return f"""Is there {self.focus} in this image?{prev_info}

If YES: describe location and state.
If NO: say "No {self.focus} visible"."""
    
    def _check_triggers_with_llm(self, frame_path: Path) -> Optional[str]:
        """Check if any triggers match using LLM"""
        try:
            import requests
            
            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            conditions = [t.condition for t in self.triggers]
            conditions_text = "\n".join(f"- {c}" for c in conditions)
            
            prompt = f"""Look at this image and check if ANY of these conditions are met:

{conditions_text}

If YES to any condition:
- Say which condition(s) are met
- Briefly describe what you see that matches

If NO conditions are met:
- Reply with just: NO

Be accurate - only confirm if you're confident."""

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
        """Speak text using TTS"""
        try:
            # Clean text for TTS
            text = text.replace('"', '').replace("'", "")
            text = ' '.join(text.split())[:500]  # Limit length
            
            if self.tts_engine == "espeak":
                cmd = ["espeak", "-s", str(self.tts_rate), text]
            elif self.tts_engine == "pico":
                cmd = ["pico2wave", "-w", "/tmp/tts.wav", text]
                subprocess.run(cmd, capture_output=True, timeout=10)
                cmd = ["aplay", "/tmp/tts.wav"]
            elif self.tts_engine == "festival":
                cmd = ["festival", "--tts"]
                subprocess.run(cmd, input=text.encode(), capture_output=True, timeout=30)
                return
            else:
                # Fallback to espeak
                cmd = ["espeak", "-s", str(self.tts_rate), text]
            
            # Run async to not block
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
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
