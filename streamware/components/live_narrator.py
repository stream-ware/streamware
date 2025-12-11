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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import base64
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
                except Exception:
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
        
        # Intent for smart detection pipeline
        import urllib.parse
        intent_raw = uri.get_param("intent", "")
        self.intent = urllib.parse.unquote(intent_raw) if intent_raw else ""
        
        # Verbose mode for detailed logging
        self.verbose = str_to_bool(uri.get_param("verbose", "false"))
        
        # Log file for timing logs (passed from CLI --log-file)
        self.log_file = uri.get_param("log_file", None)
        self.log_format = uri.get_param("log_format", "csv")  # csv, json, yaml, md, all
        
        # RAM disk for fast frame capture
        self.use_ramdisk = str_to_bool(uri.get_param("ramdisk", config.get("SQ_RAMDISK_ENABLED", "true")))
        
        # Get defaults from config
        default_model = config.get("SQ_MODEL", "llava:7b")
        default_duration = config.get("SQ_STREAM_DURATION", "30")
        
        # Descriptive parameters (analysis, motion, frames)
        from ..presets import get_descriptive_preset
        
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
        
        # Lite mode (no images in memory) and quiet mode
        self.lite_mode = str_to_bool(uri.get_param("lite", "false"))
        self.quiet = str_to_bool(uri.get_param("quiet", "false"))
        
        # Real-time DSL streaming (WebSocket server for live animation)
        self.realtime = str_to_bool(uri.get_param("realtime", "false"))
        self._realtime_server = None
        
        # DSL-only mode: skip LLM, use only OpenCV tracking (fast, up to 20 FPS)
        self.dsl_only = str_to_bool(uri.get_param("dsl_only", "false"))
        
        # Target FPS for real-time mode
        target_fps_str = uri.get_param("target_fps", "")
        if target_fps_str:
            self.target_fps = float(target_fps_str)
        elif self.dsl_only and self.realtime:
            self.target_fps = 10.0  # Default 10 FPS for DSL-only realtime
        elif self.realtime:
            self.target_fps = 2.0  # Default 2 FPS for normal realtime
        else:
            self.target_fps = 1.0 / self.interval  # Based on interval
        
        # Async LLM mode: non-blocking inference for higher throughput
        self.async_llm = str_to_bool(uri.get_param("async_llm", "true"))  # Default ON
        self._async_llm_instance = None
        self._pending_llm_frame = None  # Frame waiting for LLM result
        
        # Language
        self.language = uri.get_param("lang", "en")
        
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
        
        # Movement tracking state (for smart track mode)
        self._position_history: List[Dict] = []  # [{x, y, timestamp, regions}]
        self._last_position: Optional[Dict] = None
        self._movement_direction: str = ""  # entering, exiting, left, right, stationary
        self._person_state: str = ""  # visible, not_visible, just_appeared, just_left
        
        # Object tracker for multi-object tracking across frames
        self._object_tracker = None  # Lazy init
    
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
    
    def _analyze_movement(self, analysis: Dict, frame_width: int = 1920, frame_height: int = 1080) -> Dict:
        """Analyze movement direction from motion regions using ObjectTracker.
        
        Returns dict with:
            - direction: entering, exiting, moving_left, moving_right, stationary, unknown
            - person_state: visible, not_visible, just_appeared, just_left
            - position: center position of motion (x, y)
            - description: human-readable movement description
            - tracked_objects: list of tracked objects with IDs
        """
        from ..object_tracker import ObjectTracker, extract_detections_from_regions
        
        # Initialize tracker if needed
        if self._object_tracker is None:
            self._object_tracker = ObjectTracker(
                focus=self.focus or "person",
                max_lost_frames=5,
                iou_threshold=0.3,
                distance_threshold=0.25,
            )
        
        regions = analysis.get("motion_regions", [])
        has_motion = analysis.get("has_motion", False)
        likely_person = analysis.get("likely_person", False)
        
        result = {
            "direction": "unknown",
            "person_state": "unknown",
            "position": None,
            "description": "",
            "tracked_objects": [],
            "object_count": 0,
        }
        
        # Convert regions to detections with frame dimensions
        for r in regions:
            r["frame_width"] = frame_width
            r["frame_height"] = frame_height
        
        detections = extract_detections_from_regions(regions)
        
        # Update tracker
        tracking_result = self._object_tracker.update(detections)
        
        result["tracked_objects"] = tracking_result.objects
        result["object_count"] = tracking_result.active_count
        
        if not tracking_result.objects:
            # No objects tracked
            if self._last_position:
                result["person_state"] = "just_left"
                result["direction"] = "exiting"
                result["description"] = f"{self.focus.title()} left the frame"
            else:
                result["person_state"] = "not_visible"
                result["description"] = "Scene is still"
            
            self._last_position = None
            return result
        
        # Get primary object (largest or first)
        primary_obj = max(tracking_result.objects, key=lambda o: o.bbox.area)
        
        # Update position
        center_x = primary_obj.bbox.x * frame_width
        center_y = primary_obj.bbox.y * frame_height
        current_pos = {"x": center_x, "y": center_y, "timestamp": time.time()}
        result["position"] = current_pos
        
        # Use tracker's direction
        result["direction"] = primary_obj.direction.value
        result["person_state"] = primary_obj.state.value
        
        # Build description from tracker
        if tracking_result.active_count == 1:
            result["description"] = primary_obj.get_summary()
        else:
            # Multiple objects
            summaries = [f"#{obj.id}: {obj.get_summary()}" for obj in tracking_result.objects[:3]]
            result["description"] = f"{tracking_result.active_count} objects tracked. " + ". ".join(summaries)
        
        # Add entry/exit events
        if tracking_result.has_entries():
            for obj in tracking_result.entries:
                result["description"] += f" {obj.object_type.title()} #{obj.id} entered."
        
        if tracking_result.has_exits():
            for obj in tracking_result.exits:
                result["description"] += f" {obj.object_type.title()} #{obj.id} left."
        
        # Update position history
        self._position_history.append(current_pos)
        if len(self._position_history) > 10:
            self._position_history.pop(0)
        
        self._last_position = current_pos
        self._movement_direction = result["direction"]
        self._person_state = result["person_state"]
        
        return result
    
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
        from ..timing_logger import get_logger, set_log_file
        from ..frame_optimizer import get_optimizer, OptimizerConfig
        from ..smart_detector import SmartDetector
        
        # Check if log_file was passed through URI
        log_file = getattr(self, 'log_file', None)
        if log_file:
            set_log_file(log_file, verbose=self.verbose)
        
        # Get logger (will reuse existing if set_log_file was called)
        tlog = get_logger(verbose=self.verbose)
        
        if self.verbose:
            print("\n📊 Verbose mode: showing all steps in real-time", flush=True)
        
        # Initialize SVG analysis exporter for visual analysis
        from ..frame_diff_dsl import FrameDiffAnalyzer, DSLGenerator
        from ..dsl_visualizer import SVGFrameGenerator
        
        svg_analyzer = FrameDiffAnalyzer()
        dsl_generator = DSLGenerator()
        svg_generator = SVGFrameGenerator(width=640, height=480)
        frame_deltas = []  # Collect all deltas for final export
        
        # Start real-time DSL server if enabled
        # Use separate process for complete isolation from LLM
        self._dsl_streamer_process = None
        if self.realtime:
            try:
                from ..dsl_streamer_process import start_dsl_streamer
                self._dsl_streamer_process = start_dsl_streamer(
                    rtsp_url=self.source,
                    fps=max(5, self.target_fps),  # Min 5 FPS for smooth viewer
                    ws_port=8765,
                    http_port=8766,
                )
                print(f"🚀 DSL Streamer running in separate process (isolated from LLM)", flush=True)
            except Exception as e:
                logger.warning(f"DSL streamer process failed, using in-process: {e}")
                # Fallback to in-process server
                try:
                    from ..realtime_dsl_server import get_realtime_server
                    self._realtime_server = get_realtime_server(auto_start=True)
                    if self._realtime_server:
                        print(f"🌐 Real-time viewer: http://localhost:8766", flush=True)
                except Exception as e2:
                    logger.debug(f"Real-time server failed: {e2}")
        
        # Initialize DSL timing logger for performance analysis
        dsl_timing = None
        if self.dsl_only or self.realtime:
            try:
                from ..dsl_timing_logger import DSLTimingLogger
                timing_file = f"dsl_timing_{int(time.time())}.csv"
                dsl_timing = DSLTimingLogger(log_file=timing_file, print_realtime=True)
                print(f"📊 DSL timing log: {timing_file}", flush=True)
            except Exception as e:
                logger.debug(f"DSL timing logger failed: {e}")
        
        # Initialize parallel processor for multi-threaded execution
        from ..parallel_processor import get_processor, TaskPriority
        import os
        cpu_count = os.cpu_count() or 4
        parallel = get_processor(max_workers=max(4, cpu_count // 2))
        print(f"⚡ Parallel processing enabled ({parallel.max_workers} workers)", flush=True)
        
        # Initialize async LLM for non-blocking inference
        if self.async_llm and not self.dsl_only:
            try:
                from ..async_llm import get_async_llm
                self._async_llm_instance = get_async_llm(max_workers=2, ollama_url=self.ollama_url)
                print("🚀 Async LLM enabled (non-blocking inference)", flush=True)
            except Exception as e:
                logger.debug(f"Async LLM init failed: {e}")
                self._async_llm_instance = None
        
        # FastCapture for low-latency RTSP streaming (10x faster than subprocess)
        # Skip if DSL streamer process handles streaming separately
        from ..fast_capture import FastCapture
        fast_capture = None
        use_fast_capture = config.get("SQ_FAST_CAPTURE", "true").lower() == "true"
        
        # If DSL streamer process is running, use slower LLM-only capture rate
        if self._dsl_streamer_process:
            capture_fps = 0.5  # Slow rate for LLM analysis only
            print(f"📹 Main process: LLM-only mode (DSL streams separately)", flush=True)
        elif self.dsl_only or self.realtime:
            capture_fps = self.target_fps
        else:
            capture_fps = 1.0 / max(1.0, self.interval)
        
        if use_fast_capture and self.source.startswith("rtsp://"):
            try:
                fast_capture = FastCapture(
                    rtsp_url=self.source,
                    fps=min(30, capture_fps),  # Cap at 30 FPS
                    use_gpu=True,
                    buffer_size=5 if self.realtime else 3,  # Larger buffer for realtime
                )
                fast_capture.start()
                print(f"🚀 FastCapture enabled ({capture_fps:.1f} FPS, buffer={fast_capture.buffer_size})", flush=True)
                # Wait for first frame
                import time as _time
                _time.sleep(0.5)  # Shorter wait
            except Exception as e:
                logger.warning(f"FastCapture init failed, using fallback: {e}")
                fast_capture = None
        
        if self.use_ramdisk:
            print("📁 Using RAM disk for frame storage", flush=True)
        
        # Pipeline: capture next frame while processing current
        next_frame_future = None
        
        # Initialize frame optimizer for intelligent processing
        opt_config = OptimizerConfig(
            base_interval=self.interval,
            min_interval=max(1.0, self.interval / 3),
            max_interval=min(15.0, self.interval * 3),
            use_local_detection=True,
        )
        optimizer = get_optimizer(opt_config)
        
        # Initialize detection pipeline from intent or mode
        guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
        
        # Check if intent was specified
        intent_str = getattr(self, 'intent', None) or config.get("SQ_INTENT", "")
        
        if intent_str:
            from ..detection_pipeline import DetectionPipeline
            detection_pipeline = DetectionPipeline.from_intent(
                intent_str,
                guarder_model=guarder_model,
                vision_model=self.model,
            )
            logger.info(f"Using intent-based pipeline: {detection_pipeline.intent.name}")
        else:
            detection_pipeline = None
        
        # Fallback to SmartDetector for non-intent mode
        # Enable YOLO by default for faster detection
        use_yolo = config.get("SQ_USE_YOLO", "true").lower() == "true"
        yolo_model = config.get("SQ_YOLO_MODEL", "yolov8n")
        
        smart_detector = SmartDetector(
            focus=self.focus or "person",
            guarder_model=guarder_model,
            use_hog=True,
            use_small_llm=True,
            use_yolo=use_yolo,
            yolo_model=yolo_model,
        )
        
        start_time = time.time()
        frame_num = 0
        current_interval = self.interval
        
        # Register cleanup handler for Ctrl+C
        import signal
        import threading
        def cleanup_handler(signum, frame):
            print("\n🛑 Interrupted - cleaning up...", flush=True)
            self._running = False
            if self._realtime_server:
                try:
                    from ..realtime_dsl_server import stop_realtime_server
                    stop_realtime_server()
                except:
                    pass
        
        original_handler = signal.signal(signal.SIGINT, cleanup_handler)
        
        # Show configuration
        if self.realtime or self.dsl_only:
            print(f"\n🎬 Starting real-time loop (target={self.target_fps:.1f} FPS, duration={self.duration}s)", flush=True)
        else:
            print(f"\n🎬 Starting narrator loop (duration={self.duration}s, interval={self.interval}s)", flush=True)
        
        while time.time() - start_time < self.duration and self._running:
            frame_num += 1
            elapsed = time.time() - start_time
            
            if self.verbose or frame_num <= 3:
                print(f"🔄 Frame #{frame_num} (elapsed={elapsed:.1f}s)", flush=True)
            
            tlog.start_frame(frame_num)
            
            # Capture frame - use FastCapture if available (10x faster)
            tlog.start("capture")
            if fast_capture and fast_capture.is_running:
                # Get pre-buffered frame from FastCapture
                if self.verbose:
                    print(f"   📷 Getting frame from FastCapture (queue={fast_capture._frame_queue.qsize()})...", flush=True)
                frame_info = fast_capture.get_frame(timeout=5.0)
                if frame_info:
                    frame_path = frame_info.path
                    tlog.end("capture", f"fast={frame_info.capture_time_ms:.0f}ms")
                    if self.verbose:
                        print(f"   ✅ Got frame: {frame_path}", flush=True)
                else:
                    print(f"   ⚠️ FastCapture timeout, using fallback", flush=True)
                    frame_path = self._capture_frame(frame_num)
                    tlog.end("capture", "fallback")
            else:
                frame_path = self._capture_frame(frame_num)
                tlog.end("capture")
            
            if not frame_path or not frame_path.exists():
                print(f"   ❌ Frame capture failed", flush=True)
                tlog.end_frame("capture_failed")
                time.sleep(current_interval)
                continue
            
            # === SVG ANALYSIS (runs in parallel, doesn't block) ===
            try:
                svg_delta = svg_analyzer.analyze(frame_path, timing_logger=dsl_timing)
                dsl_generator.add_delta(svg_delta)
                frame_deltas.append(svg_delta)
                
                # Stream to real-time server IMMEDIATELY (non-blocking)
                if self._realtime_server and svg_delta:
                    bg = svg_delta.background_base64 if hasattr(svg_delta, 'background_base64') else ""
                    self._realtime_server.add_frame(svg_delta, bg)
            except Exception as e:
                logger.debug(f"SVG analysis failed: {e}")
            
            # === REAL-TIME MODE with separate DSL process ===
            # DSL streaming is handled by separate process - main loop only does LLM
            if self.realtime and self._dsl_streamer_process:
                # DSL streaming is in separate process - only do LLM here (throttled)
                if not hasattr(self, '_llm_thread') or self._llm_thread is None or not self._llm_thread.is_alive():
                    def process_llm_async(fp, fn):
                        try:
                            self._process_frame_with_llm(fp, {}, fn, tlog, parallel, optimizer)
                        except Exception as e:
                            logger.debug(f"Async LLM error: {e}")
                    
                    self._llm_thread = threading.Thread(
                        target=process_llm_async, 
                        args=(frame_path, frame_num),
                        daemon=True
                    )
                    self._llm_thread.start()
                    if self.verbose:
                        print(f"   🧠 LLM processing F{frame_num} in background", flush=True)
                
                # Main loop runs at slower rate for LLM (every few seconds)
                self._prev_frame = frame_path
                tlog.end_frame("realtime_process")
                time.sleep(max(1.0, self.interval))  # LLM rate, not DSL rate
                continue
            
            # === REAL-TIME MODE without separate process (fallback) ===
            if self.realtime and not self.dsl_only:
                # Track LLM thread state
                if not hasattr(self, '_llm_thread') or self._llm_thread is None or not self._llm_thread.is_alive():
                    # LLM is idle - submit new frame for processing
                    def process_llm_async(fp, fa, fn):
                        try:
                            self._process_frame_with_llm(fp, fa, fn, tlog, parallel, optimizer)
                        except Exception as e:
                            logger.debug(f"Async LLM error: {e}")
                    
                    self._llm_thread = threading.Thread(
                        target=process_llm_async, 
                        args=(frame_path, {}, frame_num),
                        daemon=True
                    )
                    self._llm_thread.start()
                    if self.verbose:
                        print(f"   🧠 LLM processing F{frame_num} in background", flush=True)
                else:
                    # LLM is busy - skip this frame for LLM, but DSL already streamed
                    if self.verbose and frame_num % 10 == 0:
                        print(f"   ⏭️ LLM busy, skipping F{frame_num} for analysis", flush=True)
                
                # Continue immediately to next frame at target FPS
                self._prev_frame = frame_path
                tlog.end_frame("realtime_async")
                frame_interval = 1.0 / self.target_fps
                time.sleep(max(0.02, frame_interval))  # Min 50 FPS
                continue
            
            # === DSL-ONLY MODE: Skip LLM, just use OpenCV tracking ===
            if self.dsl_only:
                # Fast path: only DSL analysis, no LLM calls (~10ms per frame)
                self._prev_frame = frame_path
                tlog.end_frame("dsl_only")
                
                # Use target_fps for timing
                frame_interval = 1.0 / self.target_fps
                time.sleep(max(0.02, frame_interval))  # Min 50 FPS cap
                continue
            
            # === SMART DETECTION PIPELINE ===
            # Priority: OpenCV (fast) → Small LLM (medium) → Large LLM (slow)
            
            frame_analysis = {}
            annotated_frame = frame_path
            
            if self.mode == "track":
                # Use SmartDetector for tracking mode
                tlog.start("smart_detect")
                detection = smart_detector.analyze(frame_path, self._prev_frame)
                tlog.end("smart_detect", f"target={detection.has_target} motion={detection.motion_percent:.1f}%")
                
                # Adaptive interval based on motion
                current_interval = optimizer.get_adaptive_interval(detection.motion_percent)
                
                # Skip if SmartDetector says no need to process
                if detection.skip_reason and frame_num > 1:
                    if not self.quiet:
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"⚪ [{ts}] {detection.skip_reason} (next: {current_interval:.1f}s)", flush=True)
                    
                    # Log the skip decision
                    tlog.log_decision(
                        frame_num, "smart_detect", "skipped",
                        detection.skip_reason,
                        {"motion": detection.motion_percent, "has_target": detection.has_target}
                    )
                    tlog.increment_frame_count(skipped=True)
                    tlog.end_frame(detection.skip_reason)
                    self._prev_frame = frame_path
                    time.sleep(current_interval)
                    continue
                
                # If SmartDetector has quick summary, use it
                if detection.quick_summary and not detection.should_process_llm:
                    description = detection.quick_summary
                    
                    # Check if should notify (TTS)
                    if detection.should_notify:
                        from ..response_filter import should_notify as check_notify, format_for_tts
                        
                        if not self.quiet:
                            ts = datetime.now().strftime("%H:%M:%S")
                            print(f"📝 [{ts}] {description}", flush=True)
                        
                        # TTS
                        if self.tts_enabled and check_notify(description, mode=self.mode):
                            tts_text = format_for_tts(description)
                            if tts_text:
                                self._speak(tts_text)
                        
                        # Log entry
                        entry = NarrationEntry(
                            timestamp=datetime.now(),
                            frame_num=frame_num,
                            description=description,
                        )
                        self._history.append(entry)
                    
                    tlog.end_frame(description[:30] if description else "smart_skip")
                    self._prev_frame = frame_path
                    time.sleep(current_interval)
                    continue
                
                # Store motion and detection info for later
                frame_analysis = {
                    "motion_percent": detection.motion_percent,
                    "has_motion": detection.motion_level.value > 0,
                    "has_target": detection.has_target,
                    "detection_method": detection.detection_method,
                    "detection_count": detection.detection_count,
                    "quick_summary": detection.quick_summary,
                    "detections": detection.detections,
                }
                self._last_analysis = frame_analysis
                
            elif self.use_advanced:
                # Legacy advanced analysis for non-tracking modes
                tlog.start("motion_analysis")
                frame_analysis, annotated_frame = self._frame_analyzer.analyze(frame_path)
                tlog.end("motion_analysis", f"motion={frame_analysis.get('motion_percent', 0):.1f}%")
                self._last_analysis = frame_analysis
                
                motion_pct = frame_analysis.get("motion_percent", 0)
                current_interval = optimizer.get_adaptive_interval(motion_pct)
                
                if motion_pct < 0.5 and frame_num > 1:
                    if not self.quiet:
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"⚪ [{ts}] No significant motion", flush=True)
                    tlog.end_frame("low_motion")
                    self._prev_frame = frame_path
                    time.sleep(current_interval)
                    continue
            else:
                # Simple diff fallback
                if self.use_diff and self._prev_frame:
                    change_pct = self._compute_change(frame_path)
                    if change_pct < self.min_change:
                        tlog.end_frame("no_change")
                        self._prev_frame = frame_path
                        time.sleep(self.interval)
                        continue
            
            # Optimize image for LLM (reduces transfer time) - can run in parallel
            tlog.start("image_optimize")
            try:
                from ..image_optimizer import optimize_for_llm, get_optimal_size_for_model, get_description_cache
                
                optimal_size = get_optimal_size_for_model(self.model)
                
                # Run optimization in background thread
                def do_optimize():
                    return optimize_for_llm(
                        annotated_frame or frame_path,
                        max_size=optimal_size,
                        quality=75
                    )
                
                opt_future = parallel.submit_optimize(do_optimize)
                optimized_path = parallel.wait_for(opt_future, timeout=5)
                if optimized_path and optimized_path.result:
                    optimized_path = optimized_path.result
                else:
                    optimized_path = annotated_frame or frame_path
                
                tlog.end("image_optimize", f"size={optimal_size}")
                
                # Check cache first (but disable in track mode - we need fresh descriptions)
                cache = get_description_cache()
                
                # Disable cache in track mode - movement changes need fresh analysis
                use_cache = self.mode != "track"
                
                cached_desc = cache.get(optimized_path) if use_cache else None
                if cached_desc:
                    tlog.log_decision(frame_num, "cache", "hit", f"Using cached: {cached_desc[:40]}")
                    description = cached_desc
                    tlog.start("vision_llm")
                    tlog.end("vision_llm", "cache_hit")
                else:
                    # Check for pending async LLM result from previous frame
                    if self._async_llm_instance and self._pending_llm_frame:
                        prev_result = self._async_llm_instance.get_result(
                            self._pending_llm_frame, timeout=0.1
                        )
                        if prev_result and prev_result.success:
                            # Process previous frame's result in background
                            logger.debug(f"Got async result for frame {self._pending_llm_frame}")
                    
                    # Submit async LLM request (non-blocking)
                    if self._async_llm_instance:
                        tlog.start("vision_llm")
                        # Build prompt (reuse advanced prompt builder)
                        prompt = self._build_advanced_prompt(frame_analysis or {})
                        self._async_llm_instance.submit(
                            prompt=prompt,
                            image_path=str(optimized_path),
                            model=self.model,
                            frame_num=frame_num,
                        )
                        self._pending_llm_frame = frame_num
                        
                        # Wait briefly for result (allows pipelining)
                        result = self._async_llm_instance.get_result(frame_num, timeout=3.0)
                        if result and result.success:
                            description = result.text
                            tlog.end("vision_llm", f"async len={len(description)}")
                        else:
                            # Fall back to sync if async not ready
                            description = self._describe_frame_advanced(optimized_path, frame_analysis)
                            tlog.end("vision_llm", f"sync len={len(description) if description else 0}")
                    else:
                        # Sync fallback
                        tlog.start("vision_llm")
                        description = self._describe_frame_advanced(
                            optimized_path, 
                            frame_analysis
                        )
                        tlog.end("vision_llm", f"len={len(description) if description else 0}")
                    
                    # Cache the result in background (but not in track mode)
                    if description and use_cache:
                        parallel.submit_optimize(lambda: cache.put(optimized_path, description))
            except ImportError:
                tlog.end("image_optimize", "skipped")
                # Fallback without optimization
                tlog.start("vision_llm")
                description = self._describe_frame_advanced(
                    annotated_frame or frame_path, 
                    frame_analysis
                )
                tlog.end("vision_llm", f"len={len(description) if description else 0}")
            
            # Log the LLM response
            tlog.log_decision(
                frame_num, "vision_llm_response", 
                "received" if description else "empty",
                description[:100] if description else "No response",
                {"length": len(description) if description else 0}
            )
            
            # Check for duplicates and filter noise
            if description:
                # Smart filtering - uses LLM with tracking data to summarize
                from ..response_filter import is_significant_smart, should_notify, format_for_tts
                
                # Build tracking data from analysis and movement
                movement_data = self._analyze_movement(frame_analysis or {})
                tracking_data = {
                    "object_count": movement_data.get("object_count", 0),
                    "direction": movement_data.get("direction", "unknown"),
                    "person_state": movement_data.get("person_state", "unknown"),
                    "position": movement_data.get("position"),
                    "tracked_objects": movement_data.get("tracked_objects", []),
                    "description": movement_data.get("description", ""),
                    "motion_percent": frame_analysis.get("motion_percent", 0) if frame_analysis else 0,
                }
                
                tlog.start("guarder_llm")
                guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
                is_worth_logging, short_description = is_significant_smart(
                    description, 
                    mode=self.mode,
                    focus=self.focus or "person",
                    guarder_model=guarder_model,
                    tracking_data=tracking_data,
                )
                tlog.end("guarder_llm", short_description[:40] if short_description else "")
                
                # State change detection - always report person appeared/disappeared
                prev_had_person = hasattr(self, '_last_state_person') and self._last_state_person
                curr_has_person = "person" in short_description.lower() and "no person" not in short_description.lower()
                state_changed = prev_had_person != curr_has_person
                self._last_state_person = curr_has_person
                
                # Skip if same as last description AND no state change
                if short_description == getattr(self, '_last_short_description', '') and not state_changed:
                    tlog.log_decision(frame_num, "duplicate_filter", "skipped", 
                                     f"Same as previous: {short_description[:40]}", {})
                    tlog.increment_frame_count(skipped=True)
                    tlog.end_frame("duplicate")
                    self._prev_frame = frame_path
                    time.sleep(self.interval)
                    continue
                
                self._last_description = description
                self._last_short_description = short_description
                
                # Log guarder decision with full context
                filter_reason = ""
                if not is_worth_logging:
                    # Determine why it was filtered
                    if "no person" in short_description.lower() or "no " + (self.focus or "person").lower() in short_description.lower():
                        filter_reason = "no_target_detected"
                    elif "no_change" in short_description.lower():
                        filter_reason = "no_change_from_previous"
                    elif not short_description or len(short_description) < 5:
                        filter_reason = "empty_summary"
                    else:
                        filter_reason = "not_significant"
                
                tlog.log_decision(
                    frame_num, "guarder_filter",
                    "accepted" if is_worth_logging else "filtered",
                    f"ORIGINAL: {description[:80]}... | SUMMARY: {short_description[:50]} | REASON: {filter_reason}",
                    {"original_len": len(description), "summary_len": len(short_description) if short_description else 0, 
                     "is_significant": is_worth_logging, "mode": self.mode, "focus": self.focus, "filter_reason": filter_reason}
                )
                
                # Use short description instead of verbose one
                description = short_description
                
                # Check triggers (on original verbose description for accuracy)
                triggered, matches = self._check_triggers(self._last_description)
                
                # Skip logging if not significant and no trigger (reduce noise)
                if not is_worth_logging and not triggered:
                    if not self.quiet:
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"⚪ [{ts}] {short_description}", flush=True)
                    
                    # Log the filter decision
                    tlog.log_decision(
                        frame_num, "output_filter", "filtered",
                        f"Not significant and no trigger: {short_description[:60]}",
                        {"triggered": triggered, "is_worth_logging": is_worth_logging}
                    )
                    tlog.increment_frame_count(skipped=True)
                    tlog.end_frame("filtered")
                    self._prev_frame = frame_path
                    time.sleep(self.interval)
                    continue
                
                # Encode BOTH original and annotated frames for report
                original_base64 = ""
                annotated_base64 = ""
                if not getattr(self, 'lite_mode', False):  # Skip if --lite
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
                        print(f"🔴 [{ts}]{analysis_info} TRIGGER: {', '.join(matches)}", flush=True)
                        print(f"   {description}", flush=True)
                    else:
                        print(f"📝 [{ts}]{analysis_info} {description}", flush=True)
                
                # Speak (TTS) only for significant events
                should_speak = should_notify(description, mode=self.mode) or triggered
                tlog.start("tts_check")
                
                # Log the TTS decision with full context
                tlog.log_decision(
                    frame_num, "tts_check", 
                    "will_speak" if (self.tts_enabled and should_speak) else "skipped",
                    f"enabled={self.tts_enabled} should_notify={should_speak} triggered={triggered}",
                    {"description": description[:100], "mode": self.mode}
                )
                
                if self.tts_enabled and should_speak:
                    if triggered:
                        tlog.end("tts_check", "trigger_speak")
                        self._speak(f"Alert! {matches[0]}")
                    else:
                        tts_text = format_for_tts(description)
                        if tts_text:
                            tlog.end("tts_check", f"speak: {tts_text[:30]}")
                            tlog.log_decision(frame_num, "tts_speak", "spoken", tts_text[:50])
                            self._speak(tts_text)
                        else:
                            tlog.end("tts_check", "no_tts_text")
                            tlog.log_decision(frame_num, "tts_format", "empty", "format_for_tts returned empty")
                else:
                    tlog.end("tts_check", f"skip: enabled={self.tts_enabled} should={should_speak}")
                
                # Webhook
                if triggered and self.webhook_url:
                    self._send_webhook(entry)
                
                tlog.increment_frame_count(skipped=False)
                tlog.end_frame(description[:30] if description else "logged")
            else:
                tlog.increment_frame_count(skipped=True)
                tlog.end_frame("duplicate")
            
            self._prev_frame = frame_path
            time.sleep(current_interval)
        
        # Cleanup FastCapture
        if fast_capture:
            fast_capture.stop()
            print("🛑 FastCapture stopped", flush=True)
        
        # Write timing summary and optimizer stats
        tlog.write_summary()
        tlog.log(f"Optimizer stats: {optimizer.get_stats()}")
        tlog.log(f"Parallel stats: {parallel.stats}")
        
        # Export logs in requested format
        if self.log_file:
            from pathlib import Path
            base_path = Path(self.log_file).with_suffix('')
            
            if self.log_format == 'all':
                tlog.export_all(str(base_path))
            elif self.log_format == 'json':
                tlog.export_json(base_path.with_suffix('.json'))
                print(f"\n📊 Logs saved: {base_path.with_suffix('.json')}", flush=True)
            elif self.log_format == 'yaml':
                tlog.export_yaml(base_path.with_suffix('.yaml'))
                print(f"\n📊 Logs saved: {base_path.with_suffix('.yaml')}", flush=True)
            elif self.log_format == 'md':
                tlog.export_markdown(base_path.with_suffix('.md'))
                print(f"\n📊 Logs saved: {base_path.with_suffix('.md')}", flush=True)
            else:
                # Default: CSV (already saved during logging)
                tlog.print_log_summary()
        else:
            tlog.print_log_summary()
        
        # Print parallel processing stats
        pstats = parallel.stats
        print(f"\n⚡ Parallel stats: {pstats['completed']} tasks, avg {pstats['avg_time_ms']:.0f}ms", flush=True)
        
        # Export lightweight HTML with DSL-driven player
        if frame_deltas:
            try:
                from ..dsl_visualizer import generate_dsl_html_lightweight
                from pathlib import Path
                
                # Determine output path
                if self.log_file:
                    html_path = Path(self.log_file).with_suffix('.html')
                else:
                    html_path = Path(f"motion_analysis_{int(time.time())}.html")
                
                dsl_output = dsl_generator.get_full_dsl()
                generate_dsl_html_lightweight(
                    deltas=frame_deltas,
                    dsl_output=dsl_output,
                    output_path=str(html_path),
                    title=f"Motion Analysis - {self.mode} mode",
                    fps=2.0,
                    include_backgrounds=True,  # 128px frame thumbnails
                    embed_assets=True,  # Inline CSS/JS for standalone file
                )
                
                # Calculate file size
                html_size = html_path.stat().st_size / 1024
                print(f"\n🎯 Motion Analysis saved: {html_path} ({html_size:.1f}KB)", flush=True)
                print(f"   Frames: {len(frame_deltas)}, Tracked: {len(dsl_generator.tracks)}", flush=True)
            except Exception as e:
                logger.debug(f"HTML export failed: {e}")
        
        # Stop DSL streamer process if running
        if hasattr(self, '_dsl_streamer_process') and self._dsl_streamer_process:
            try:
                from ..dsl_streamer_process import stop_dsl_streamer
                stop_dsl_streamer()
                print("🔌 DSL Streamer process stopped", flush=True)
            except Exception as e:
                logger.debug(f"Error stopping DSL streamer: {e}")
        
        # Stop real-time server if running (fallback mode)
        if self._realtime_server:
            try:
                from ..realtime_dsl_server import stop_realtime_server
                stop_realtime_server()
                print("🔌 Real-time server stopped", flush=True)
            except Exception as e:
                logger.debug(f"Error stopping realtime server: {e}")
        
        # Shutdown async LLM
        if self._async_llm_instance:
            try:
                from ..async_llm import shutdown_async_llm
                stats = self._async_llm_instance.stats
                shutdown_async_llm()
                print(f"🔌 Async LLM stopped (completed: {stats['completed']}, avg: {stats['avg_latency_ms']:.0f}ms)", flush=True)
            except Exception as e:
                logger.debug(f"Error stopping async LLM: {e}")
        
        # Close DSL timing logger and print summary
        if dsl_timing:
            try:
                dsl_timing.print_summary()
                dsl_timing.close()
            except Exception as e:
                logger.debug(f"Error closing DSL timing logger: {e}")
        
        # Wait for any pending TTS to complete before exiting
        if self.tts_enabled:
            from ..tts import wait_for_tts
            wait_for_tts(timeout=5.0)
        
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
            # SVG Analysis
            "svg_analysis_path": str(html_path) if frame_deltas else None,
            "svg_frames_analyzed": len(frame_deltas),
            "svg_objects_tracked": len(dsl_generator.tracks) if frame_deltas else 0,
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
        """Capture frame from source.
        
        Uses RAM disk (/dev/shm) when enabled for faster I/O.
        Supports GPU acceleration (NVDEC) when available.
        """
        # Use RAM disk path if enabled
        if self.use_ramdisk and self.source.startswith("rtsp://"):
            ramdisk_path = Path(config.get("SQ_RAMDISK_PATH", "/dev/shm/streamware"))
            ramdisk_path.mkdir(parents=True, exist_ok=True)
            output_path = ramdisk_path / f"frame_{frame_num:05d}.jpg"
        else:
            output_path = self._temp_dir / f"frame_{frame_num:05d}.jpg"
        
        try:
            if self.source.startswith("rtsp://"):
                # RTSP capture with optimizations
                cmd = ["ffmpeg", "-y"]
                
                # Check for GPU acceleration
                has_gpu = getattr(self, '_has_nvdec', None)
                if has_gpu is None:
                    # Check once
                    try:
                        result = subprocess.run(
                            ["ffmpeg", "-hide_banner", "-hwaccels"],
                            capture_output=True, text=True, timeout=3
                        )
                        has_gpu = "cuda" in result.stdout.lower()
                        self._has_nvdec = has_gpu
                    except Exception:
                        self._has_nvdec = False
                        has_gpu = False
                
                # GPU hardware decoding
                if has_gpu:
                    cmd.extend(["-hwaccel", "cuda"])
                
                # Low latency options
                cmd.extend([
                    "-rtsp_transport", "tcp",
                    "-fflags", "nobuffer",
                    "-flags", "low_delay",
                    "-i", self.source,
                    "-frames:v", "1",
                    "-q:v", "2",
                    str(output_path)
                ])
            else:
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.source,
                    "-frames:v", "1",
                    str(output_path)
                ]
            
            subprocess.run(cmd, check=True, capture_output=True, timeout=10, stdin=subprocess.DEVNULL)

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

    def _process_frame_with_llm(self, frame_path: Path, frame_analysis: Dict, frame_num: int, tlog, parallel, optimizer):
        """Process frame with LLM in background thread (for async realtime mode)."""
        try:
            from ..image_optimizer import optimize_for_llm, get_optimal_size_for_model, get_description_cache
            from ..response_filter import is_significant_smart
            from ..config import config
            
            # Optimize image
            optimal_size = get_optimal_size_for_model(self.model)
            optimized_path = optimize_for_llm(frame_path, max_size=optimal_size, quality=75)
            if not optimized_path:
                optimized_path = frame_path
            
            # Get AI description
            description = self._describe_frame_advanced(optimized_path, frame_analysis)
            
            if description:
                # Filter and check significance
                guarder_model = config.get("SQ_GUARDER_MODEL", "gemma:2b")
                is_worth, short_desc = is_significant_smart(
                    description,
                    mode=self.mode,
                    focus=self.focus or "person",
                    guarder_model=guarder_model,
                    tracking_data={},
                )
                
                if is_worth and short_desc:
                    # Log significant detection
                    if not self.quiet:
                        print(f"   🎯 [LLM F{frame_num}] {short_desc}", flush=True)
                    
                    # Handle TTS, webhooks etc in background
                    self._handle_detection(short_desc, frame_path, frame_num)
                    
        except Exception as e:
            logger.debug(f"Background LLM processing error: {e}")
    
    def _handle_detection(self, description: str, frame_path: Path, frame_num: int):
        """Handle detection event (TTS, webhook, etc) - called from background thread."""
        try:
            # TTS if enabled
            if self.tts_enabled:
                from ..tts import speak_async
                speak_async(description)
            
            # Webhook if configured
            if self.webhook_url:
                import requests
                try:
                    requests.post(self.webhook_url, json={
                        "event": "detection",
                        "description": description,
                        "frame_num": frame_num,
                    }, timeout=2)
                except:
                    pass
        except Exception as e:
            logger.debug(f"Detection handler error: {e}")
    
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
        from ..timing_logger import get_logger
        tlog = get_logger()
        
        try:
            from ..llm_client import get_client
            
            # Crop to motion regions if available to focus LLM on changes
            tlog.start("crop_motion")
            crop_path = self._crop_to_motion_regions(frame_path, analysis or {})
            tlog.end("crop_motion")
            
            # Build context-aware prompt
            tlog.start("build_prompt")
            prompt = self._build_advanced_prompt(analysis)
            tlog.end("build_prompt", f"len={len(prompt)}")
            
            # Use centralized LLM client
            tlog.start("llm_request")
            client = get_client()
            result = client.analyze_image(crop_path, prompt, model=self.model)
            tlog.end("llm_request", f"success={result.get('success')}")
            
            # Verbose logging: show prompt and response
            if self.verbose:
                # Log prompt (truncated for readability)
                prompt_preview = prompt.replace('\n', ' ')[:200]
                tlog.log_decision(
                    0, "llm_prompt", "sent",
                    f"[{self.model}] {prompt_preview}...",
                    {"prompt_len": len(prompt), "model": self.model}
                )
                # Log full response
                response_text = result.get("response", "")[:300] if result.get("success") else "FAILED"
                tlog.log_decision(
                    0, "llm_response", "received" if result.get("success") else "failed",
                    f"[{self.model}] {response_text}",
                    {"response_len": len(result.get("response", "")), "success": result.get("success")}
                )
            
            if result.get("success"):
                desc = result.get("response", "").strip()
                self._prev_description = desc
                return desc
            return ""
            
        except Exception as e:
            logger.warning(f"Advanced description failed: {e}")
            return self._describe_frame(frame_path)  # Fallback
    
    def _build_advanced_prompt(self, analysis: Dict) -> str:
        """Build prompt with motion/edge analysis context.
        
        Prompts are loaded from streamware/prompts/*.txt files.
        Can be customized by editing those files or via environment variables.
        """
        from ..prompts import get_prompt, render_prompt
        
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
        
        # Add YOLO detection info if available
        has_target = analysis.get("has_target", False)
        detection_method = analysis.get("detection_method", "")
        quick_summary = analysis.get("quick_summary", "")
        detections = analysis.get("detections", [])
        
        if has_target and "yolo" in detection_method.lower():
            if quick_summary:
                context_parts.append(f"⚠️ YOLO DETECTED: {quick_summary}")
            elif detections:
                det_types = [d.get("type", "object") for d in detections[:3]]
                context_parts.append(f"⚠️ YOLO DETECTED: {', '.join(det_types)}")
        
        context = "\n".join(context_parts) if context_parts else "No pre-analysis data"
        
        # Build mode-specific prompt with context
        if self.mode == "track" and self.focus:
            focus_obj = self.focus.lower()
            prev_info = f'\nPrevious: "{self._prev_description[:60]}"' if self._prev_description else ""
            
            # Analyze movement direction from regions
            movement = self._analyze_movement(analysis)
            movement_hint = ""
            if movement["description"]:
                movement_hint = f"\nMOVEMENT ANALYSIS: {movement['description']}"
                movement_hint += f" (state: {movement['person_state']}, direction: {movement['direction']})"
            
            # Activity focus for high motion
            activity_focus = ""
            if motion_pct > 20:
                activity_focus = "\n⚠️ SIGNIFICANT MOTION DETECTED - Look for activity changes like walking, moving, standing up!"
            
            # Try to load prompt from file, fallback to default
            prompt_vars = {
                "context": context,
                "movement_hint": movement_hint,
                "prev_info": prev_info,
                "activity_focus": activity_focus,
                "motion_pct": f"{motion_pct:.0f}",
                "focus": self.focus,
                "Focus": self.focus.title(),
            }
            
            if focus_obj in ("person", "people", "human"):
                # Try loading from file
                file_prompt = get_prompt("track_person")
                if file_prompt:
                    try:
                        return file_prompt.format(**prompt_vars)
                    except KeyError:
                        pass  # Fall through to default
                
                # Clear prompt for person detection - verify presence first
                return "Look at this image carefully. Is there a person clearly visible? If YES, describe what they are doing in one sentence. If NO person is visible, say 'No person visible' and briefly describe what you see instead."
            
            elif focus_obj in ("bird", "birds"):
                # Load from file
                file_prompt = get_prompt("track_bird")
                if file_prompt:
                    try:
                        return file_prompt.format(**prompt_vars)
                    except KeyError:
                        pass
                return "Describe any birds in this image - count, activity, and location."
            
            elif focus_obj in ("animal", "cat", "dog", "pet", "wildlife"):
                # Load from file
                file_prompt = get_prompt("track_animal")
                if file_prompt:
                    try:
                        return file_prompt.format(**prompt_vars)
                    except KeyError:
                        pass
                return f"Describe any {focus_obj} in this image - what it is doing and where."
            
            else:
                # Generic tracking - load from file
                file_prompt = get_prompt("track_generic")
                if file_prompt:
                    try:
                        return file_prompt.format(**prompt_vars)
                    except KeyError:
                        pass
                return f"Describe {self.focus}'s position and movement in this image."

        elif self.mode == "diff":
            # Diff mode - load from file
            file_prompt = get_prompt("diff_describe")
            if file_prompt:
                try:
                    return file_prompt.format(
                        context=context,
                        prev_description=self._prev_description[:150],
                        focus=self.focus or "any changes"
                    )
                except KeyError:
                    pass
            return f"Describe only what changed from previous frame. Focus on: {self.focus or 'any changes'}"

        else:  # full mode
            # Full mode - load from file
            file_prompt = get_prompt("full_describe")
            if file_prompt:
                try:
                    return file_prompt.format(context=context)
                except KeyError:
                    pass
            return "Describe what you see in this security camera image. Be concise."
    
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
