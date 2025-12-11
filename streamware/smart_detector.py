"""
Smart Detector for Streamware

Prioritized detection pipeline for tracking mode:
1. YOLO (fast, accurate) - object detection if available
2. OpenCV (fastest) - motion detection, HOG person detection (fallback)
3. Small LLM (fast) - validate detection, check significance
4. Large LLM (slow) - only when full description needed

YOLO is auto-installed on first use for best detection accuracy.

Usage:
    from streamware.smart_detector import SmartDetector
    
    detector = SmartDetector(focus="person", use_yolo=True)
    
    result = detector.analyze(frame_path, prev_frame_path)
    # result.should_process - whether to call large LLM
    # result.has_target - whether target object detected
    # result.motion_level - motion intensity
    # result.quick_summary - short description from small LLM
    # result.detections - YOLO detections if available
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

# Import constants from response_filter to avoid duplication
from .response_filter import DEFAULT_OLLAMA_URL
from typing import Optional, Tuple, List
from .config import config

logger = logging.getLogger(__name__)


class DetectionLevel(Enum):
    """Detection confidence level."""
    NONE = 0        # No target detected
    LOW = 1         # Possible detection (needs verification)
    MEDIUM = 2      # Likely detection
    HIGH = 3        # Confident detection
    CONFIRMED = 4   # LLM confirmed


class MotionLevel(Enum):
    """Motion intensity level."""
    NONE = 0        # No motion
    MINIMAL = 1     # Very slight motion (<1%)
    LOW = 2         # Low motion (1-5%)
    MEDIUM = 3      # Medium motion (5-15%)
    HIGH = 4        # High motion (>15%)


@dataclass
class DetectionResult:
    """Result from smart detection pipeline."""
    # Core results
    has_target: bool = False
    detection_level: DetectionLevel = DetectionLevel.NONE
    motion_level: MotionLevel = MotionLevel.NONE
    
    # Processing decisions
    should_process_llm: bool = False
    should_notify: bool = False
    
    # Details
    quick_summary: str = ""
    motion_percent: float = 0.0
    confidence: float = 0.0
    
    # YOLO detections (if available)
    detections: List = field(default_factory=list)  # List of Detection objects
    detection_count: int = 0
    # Motion regions from OpenCV detector (list of (x, y, w, h))
    motion_regions: List = field(default_factory=list)
    
    # Timing
    opencv_ms: float = 0.0
    yolo_ms: float = 0.0
    small_llm_ms: float = 0.0
    
    # Debug
    skip_reason: str = ""
    detection_method: str = ""


class SmartDetector:
    """Intelligent detection pipeline optimized for tracking.
    
    Uses YOLO for fast, accurate detection when available.
    Falls back to HOG if YOLO is not installed.
    """
    
    def __init__(
        self,
        focus: str = "person",
        guarder_model: str = "gemma:2b",
        motion_threshold: float = None,  # None = use config
        use_yolo: bool = True,
        use_hog: bool = True,
        motion_gate_threshold: int = None,  # Pixels threshold for motion gating
        periodic_interval: int = None,  # Force detection every N frames
        use_small_llm: bool = True,
        yolo_model: str = "yolov8n",
        mode: str = "full",  # Track mode detection
    ):
        from .config import config
        
        self.focus = focus
        self.guarder_model = guarder_model
        
        # Use config if not specified (lower = more sensitive)
        # Default 0.1% which means ~0.1% of pixels must change
        if motion_threshold is None:
            motion_threshold = float(config.get("SQ_MIN_CHANGE", "0.1"))
        self.motion_threshold = motion_threshold
        
        # Motion gating parameters (from demo)
        if motion_gate_threshold is None:
            motion_gate_threshold = int(config.get("SQ_MOTION_GATE_THRESHOLD", "1000"))
        self.motion_gate_threshold = motion_gate_threshold
        
        if periodic_interval is None:
            periodic_interval = int(config.get("SQ_PERIODIC_INTERVAL", "30"))
        self.periodic_interval = periodic_interval
        
        self.use_yolo = use_yolo
        self.use_hog = use_hog
        self.use_small_llm = use_small_llm
        self.yolo_model = yolo_model
        self.mode = mode
        
        self._hog_detector = None
        self._yolo_detector = None
        self._animal_detector = None  # For animal/bird detection
        self._yolo_available = None  # None = not checked yet
        self._prev_summary: str = ""
        self._prev_detection: Optional[DetectionResult] = None
        self._consecutive_no_target: int = 0
    
    def _init_yolo(self) -> bool:
        """Initialize YOLO detector if available."""
        if self._yolo_available is not None:
            return self._yolo_available
        
        if not self.use_yolo:
            logger.debug("YOLO disabled by config")
            self._yolo_available = False
            return False
        
        try:
            from .yolo_detector import ensure_yolo_available, YOLODetector
            
            # Try to install/check YOLO (verbose=False to reduce noise)
            if ensure_yolo_available(verbose=False):
                # Map focus to YOLO classes
                classes = None
                if self.focus == "person":
                    classes = ["person"]
                elif self.focus == "vehicle":
                    classes = ["car", "truck", "bus", "motorcycle", "bicycle"]
                elif self.focus in ("animal", "bird", "cat", "dog", "pet", "wildlife"):
                    # Use specialized animal detector
                    from .animal_detector import AnimalDetector
                    self._animal_detector = AnimalDetector(
                        focus=self.focus if self.focus != "animal" else "all",
                        model=self.yolo_model,
                        confidence_threshold=float(config.get("SQ_YOLO_CONFIDENCE_THRESHOLD", "0.25")),
                    )
                    self._yolo_available = True
                    logger.info(f"🎯 Animal detector initialized: {self.focus}")
                    return True
                
                self._yolo_detector = YOLODetector(
                    model=self.yolo_model,
                    classes=classes,
                    confidence_threshold=float(config.get("SQ_YOLO_CONFIDENCE_THRESHOLD_HIGH", "0.5")),  # Higher threshold to reduce false positives
                )
                self._yolo_available = True
                logger.info(f"🎯 YOLO detector initialized: {self.yolo_model}, classes={classes}")
                return True
            else:
                logger.warning("YOLO not available (ultralytics not installed). Using HOG fallback.")
        except ImportError as e:
            logger.warning(f"YOLO import failed: {e}. Using HOG fallback.")
        except Exception as e:
            logger.warning(f"YOLO initialization failed: {e}. Using HOG fallback.")
        
        self._yolo_available = False
        return False
    
    def analyze(
        self,
        frame_path: Path,
        prev_frame_path: Optional[Path] = None,
    ) -> DetectionResult:
        """Run smart detection pipeline.
        
        Priority order:
        1. Motion detection (OpenCV) - skip if no motion
        2. YOLO detection (if available) - fast, accurate
        3. HOG Person Detection (fallback) - skip if no person shape
        4. Small LLM validation - confirm detection
        5. Change detection - skip if same as before
        
        Args:
            frame_path: Current frame
            prev_frame_path: Previous frame for comparison
            
        Returns:
            DetectionResult with all analysis
        """
        from .config import config
        
        result = DetectionResult()
        result.detections = []
        
        # Stage 1: Motion Detection (OpenCV)
        start = time.time()
        motion_pct, motion_regions = self._detect_motion(frame_path, prev_frame_path)
        result.opencv_ms = (time.time() - start) * 1000
        result.motion_percent = motion_pct
        result.motion_level = self._classify_motion(motion_pct)
        result.motion_regions = motion_regions
        
        # Skip if no motion - but do periodic checks even without motion
        # to catch slow movements or stationary people
        self._frame_count = getattr(self, '_frame_count', 0) + 1
        force_check = (self._frame_count % self.periodic_interval == 0)
        
        # Calculate motion area in pixels (from motion regions)
        motion_area = sum(r[2] * r[3] for r in motion_regions)  # r is (x, y, w, h) tuple
        
        # For track mode, be more lenient with motion gating to detect stationary people
        # Use lower threshold or more frequent periodic checks
        is_track_mode = self.focus == "person" and self.mode == "track"
        effective_threshold = self.motion_gate_threshold // 2 if is_track_mode else self.motion_gate_threshold
        periodic_interval = int(config.get("SQ_TRACK_PERIODIC_INTERVAL", "2")) if is_track_mode else self.periodic_interval  # Check every N frames in track mode
        force_check = (self._frame_count % periodic_interval == 0)
        
        if (motion_area < effective_threshold and 
            prev_frame_path and 
            not force_check):
            result.skip_reason = f"motion_gate_{motion_area}px"
            result.detection_method = "opencv_motion"
            return result
        
        # Stage 2: YOLO Detection (if available) - much more accurate than HOG
        yolo_detected = False
        if self._init_yolo():
            try:
                start = time.time()
                
                # Use animal detector for animal/bird focus
                if self._animal_detector and self.focus in ("animal", "bird", "cat", "dog", "pet", "wildlife"):
                    animal_result = self._animal_detector.detect(frame_path)
                    result.yolo_ms = animal_result.detection_ms
                    
                    if animal_result.has_animals:
                        result.detections = [
                            {
                                "x": a.x, "y": a.y, "w": a.w, "h": a.h,
                                "confidence": a.confidence,
                                "type": a.species.value,
                                "behavior": a.behavior.value,
                                "position": a.position,
                            }
                            for a in animal_result.animals
                        ]
                        result.detection_count = animal_result.total_count
                        result.has_target = True
                        result.confidence = max(a.confidence for a in animal_result.animals)
                        result.detection_level = DetectionLevel.HIGH
                        result.detection_method = "yolo_animal"
                        yolo_detected = True
                        self._consecutive_no_target = 0
                        
                        result.quick_summary = animal_result.get_detailed_summary()
                        logger.debug(f"Animal detected: {result.quick_summary} in {result.yolo_ms:.0f}ms")
                    else:
                        self._consecutive_no_target += 1
                        if self._consecutive_no_target % int(config.get("SQ_CONSECUTIVE_NO_TARGET_SKIP", "5")) != 0:
                            result.skip_reason = "yolo_no_animal"
                            result.detection_method = "yolo_animal"
                            return result
                
                # Use regular YOLO detector
                elif self._yolo_detector:
                    detections = self._yolo_detector.detect(frame_path)
                    result.yolo_ms = (time.time() - start) * 1000
                    
                    if detections:
                        result.detections = [d.to_dict() for d in detections]
                        result.detection_count = len(detections)
                        result.has_target = True
                        result.confidence = max(d.confidence for d in detections)
                        result.detection_level = DetectionLevel.HIGH
                        result.detection_method = "yolo"
                        yolo_detected = True
                        self._consecutive_no_target = 0
                        
                        # Build quick summary from YOLO detections
                        class_counts = {}
                        for d in detections:
                            class_counts[d.class_name] = class_counts.get(d.class_name, 0) + 1
                        
                        summary_parts = []
                        for cls, count in class_counts.items():
                            if count == 1:
                                summary_parts.append(f"{cls.title()}")
                            else:
                                summary_parts.append(f"{count} {cls}s")
                        
                        result.quick_summary = ", ".join(summary_parts) + " detected"
                        logger.debug(f"YOLO detected: {result.quick_summary} in {result.yolo_ms:.0f}ms")
                    else:
                        # YOLO found nothing
                        self._consecutive_no_target += 1
                        if self._consecutive_no_target % int(config.get("SQ_CONSECUTIVE_NO_TARGET_SKIP", "5")) != 0:
                            result.skip_reason = "yolo_no_target"
                            result.detection_method = "yolo"
                            return result
                    
            except Exception as e:
                logger.warning(f"YOLO detection failed: {e}")
                # Fall through to HOG
        
        # Stage 3: HOG Person Detection (fallback if no YOLO or YOLO failed)
        if not yolo_detected and self.use_hog and self.focus == "person":
            has_person_hog, hog_confidence, _ = self._detect_person_hog(frame_path)
            
            if not has_person_hog and hog_confidence > float(config.get("SQ_HOG_CONFIDENCE_THRESHOLD", "0.85")):  # Increased threshold to be less strict
                # HOG confident no person - but verify with LLM occasionally
                self._consecutive_no_target += 1
                
                # Every 3rd frame in track mode, verify with LLM to avoid false negatives
                # Every 5th frame in other modes
                skip_interval = int(config.get("SQ_TRACK_SKIP_INTERVAL", "3")) if self.mode == 'track' else int(config.get("SQ_SKIP_INTERVAL", "5"))
                if self._consecutive_no_target % skip_interval != 0:
                    result.skip_reason = f"hog_no_person_{hog_confidence:.1f}"
                    result.detection_method = "opencv_hog"
                    return result
            else:
                self._consecutive_no_target = 0
                result.has_target = has_person_hog
                result.confidence = hog_confidence
                result.detection_level = DetectionLevel.MEDIUM if has_person_hog else DetectionLevel.LOW
                result.detection_method = "opencv_hog"
        
        # Stage 3: Small LLM Validation
        if self.use_small_llm:
            start = time.time()
            
            # Quick check: is target present?
            llm_has_target, llm_confidence = self._llm_quick_check(frame_path)
            result.small_llm_ms = (time.time() - start) * 1000
            
            if llm_has_target:
                result.has_target = True
                result.detection_level = DetectionLevel.CONFIRMED
                result.confidence = max(result.confidence, llm_confidence)
                
                # Get quick summary
                summary = self._llm_quick_summary(frame_path)
                result.quick_summary = summary
                
                # Check if changed from previous
                if self._prev_summary:
                    has_change = self._llm_check_change(summary, self._prev_summary)
                    if not has_change:
                        result.skip_reason = "no_change"
                        result.should_notify = False
                        # Still update summary
                        self._prev_summary = summary
                        return result
                
                self._prev_summary = summary
                result.should_notify = True
                result.should_process_llm = True
                result.detection_method = "small_llm"
            else:
                result.has_target = False
                result.skip_reason = f"llm_no_{self.focus}"
                result.detection_method = "small_llm"
                
                # Clear previous summary if target left
                if self._prev_summary:
                    result.quick_summary = f"No {self.focus} visible"
                    result.should_notify = True  # Notify that target left
                    self._prev_summary = ""
                
                return result
        else:
            # No small LLM - use OpenCV results
            result.should_process_llm = result.has_target or result.motion_level.value >= MotionLevel.MEDIUM.value
            result.detection_method = "opencv_only"
        
        self._prev_detection = result
        return result
    
    def _detect_motion(
        self,
        frame_path: Path,
        prev_frame_path: Optional[Path]
    ) -> Tuple[float, List]:
        """Detect motion between frames using OpenCV."""
        from .config import config
        
        if not prev_frame_path:
            return float(config.get("SQ_MOTION_FIRST_FRAME_PERCENT", "100.0")), []  # First frame - assume motion
        
        try:
            import cv2
            
            # Load frames
            curr = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
            prev = cv2.imread(str(prev_frame_path), cv2.IMREAD_GRAYSCALE)
            
            if curr is None or prev is None:
                return float(config.get("SQ_MOTION_ERROR_PERCENT", "50.0")), []
            
            # Resize for speed
            scale = min(
                int(config.get("SQ_MOTION_SCALE_WIDTH", "320")) / curr.shape[1], 
                int(config.get("SQ_MOTION_SCALE_HEIGHT", "240")) / curr.shape[0], 
                1.0
            )
            if scale < 1.0:
                curr = cv2.resize(curr, None, fx=scale, fy=scale)
                prev = cv2.resize(prev, None, fx=scale, fy=scale)
            
            # Blur to reduce noise
            blur_kernel = int(config.get("SQ_MOTION_BLUR_KERNEL", "5"))
            curr = cv2.GaussianBlur(curr, (blur_kernel, blur_kernel), 0)
            prev = cv2.GaussianBlur(prev, (blur_kernel, blur_kernel), 0)
            
            # Compute difference
            diff = cv2.absdiff(curr, prev)
            _, thresh = cv2.threshold(diff, int(config.get("SQ_MOTION_DIFF_THRESHOLD", "25")), 255, cv2.THRESH_BINARY)
            
            # Calculate motion percentage
            motion_pixels = cv2.countNonZero(thresh)
            total_pixels = thresh.shape[0] * thresh.shape[1]
            motion_pct = (motion_pixels / total_pixels) * 100
            
            # Find motion regions
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            regions = [cv2.boundingRect(c) for c in contours if cv2.contourArea(c) > int(config.get("SQ_MOTION_CONTOUR_MIN_AREA", "100"))]
            
            return motion_pct, regions
            
        except ImportError:
            logger.debug("OpenCV not available for motion detection")
            return float(config.get("SQ_MOTION_ERROR_PERCENT", "50.0")), []
        except Exception as e:
            logger.debug(f"Motion detection failed: {e}")
            return float(config.get("SQ_MOTION_ERROR_PERCENT", "50.0")), []
    
    def _detect_person_hog(self, frame_path: Path) -> Tuple[bool, float, List]:
        """Detect person using HOG descriptor."""
        from .config import config
        
        try:
            import cv2
            
            if self._hog_detector is None:
                self._hog_detector = cv2.HOGDescriptor()
                self._hog_detector.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            img = cv2.imread(str(frame_path))
            if img is None:
                return False, 0.0, []
            
            # Resize for speed
            height, width = img.shape[:2]
            scale = min(
                int(config.get("SQ_HOG_SCALE", "400")) / width, 
                int(config.get("SQ_HOG_SCALE", "400")) / height, 
                1.0
            )
            if scale < 1.0:
                img = cv2.resize(img, None, fx=scale, fy=scale)
            
            # Detect
            boxes, weights = self._hog_detector.detectMultiScale(
                img,
                winStride=(
                    int(config.get("SQ_HOG_WINSTRIDE", "8")), 
                    int(config.get("SQ_HOG_WINSTRIDE", "8"))
                ),
                padding=(
                    int(config.get("SQ_HOG_PADDING", "4")), 
                    int(config.get("SQ_HOG_PADDING", "4"))
                ),
                scale=float(config.get("SQ_HOG_SCALE_FACTOR", "1.05"))
            )
            
            if len(boxes) > 0:
                confidence = float(max(weights)) if len(weights) > 0 else 0.5
                return True, min(confidence, 1.0), list(boxes)
            
            return False, float(config.get("SQ_HOG_CONFIDENT_NO_PERSON", "0.8")), []  # Confident no person
            
        except ImportError:
            return True, float(config.get("SQ_HOG_MIGHT_BE_PERSON", "0.5")), []  # Assume might be person
        except Exception as e:
            logger.debug(f"HOG detection failed: {e}")
            return True, float(config.get("SQ_HOG_MIGHT_BE_PERSON", "0.5")), []
    
    def _llm_quick_check(self, frame_path: Path) -> Tuple[bool, float]:
        """Quick LLM check: is target present?
        
        NOTE: Most small models (gemma:2b, etc.) are NOT vision models.
        Only use vision-capable models for this check.
        If guarder_model is not a vision model, assume target is present
        and let the main vision LLM handle detection.
        """
        import requests
        from .config import config
        from .image_optimize import prepare_image_for_llm_base64
        
        # Check if guarder model is vision-capable
        # Most guarder models (gemma, qwen, phi) are text-only!
        vision_models = config.get("SQ_VISION_MODELS", "llava,moondream,bakllava,llava-llama3,minicpm-v").split(",")
        guarder_lower = self.guarder_model.lower()
        is_vision_model = any(vm in guarder_lower for vm in vision_models)
        
        if not is_vision_model:
            # Non-vision model - cannot check images, assume target might be present
            # This is less strict - better to process than miss detections
            logger.debug(f"Guarder {self.guarder_model} is not vision model, skipping quick check")
            return True, float(config.get("SQ_VISION_ASSUME_PRESENT", "0.5"))  # Assume present, let main LLM decide
        
        try:
            image_data = prepare_image_for_llm_base64(frame_path, preset="fast")
        except Exception:
            return True, float(config.get("SQ_VISION_ASSUME_PRESENT", "0.5"))
        
        ollama_url = config.get("SQ_OLLAMA_URL", DEFAULT_OLLAMA_URL)
        
        prompt = f"Is there a {self.focus} in this image? Answer only YES or NO."
        
        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.guarder_model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                },
                timeout=int(config.get("SQ_VISION_TIMEOUT", "10")),
            )
            
            if resp.ok:
                answer = resp.json().get("response", "").strip().upper()
                if "YES" in answer:
                    return True, float(config.get("SQ_VISION_CONFIDENT_PRESENT", "0.9"))
                elif "NO" in answer:
                    return False, float(config.get("SQ_VISION_CONFIDENT_ABSENT", "0.9"))
            
            return True, float(config.get("SQ_VISION_ASSUME_PRESENT", "0.5"))  # On error, assume present
            
        except Exception:
            return True, float(config.get("SQ_VISION_ASSUME_PRESENT", "0.5"))  # On error, assume present
    
    def _llm_quick_summary(self, frame_path: Path) -> str:
        """Get quick summary from small LLM.
        
        NOTE: Only works with vision-capable models.
        For text-only models, returns empty string (main LLM will describe).
        """
        import requests
        from .config import config
        from .image_optimize import prepare_image_for_llm_base64
        
        # Check if guarder model is vision-capable
        vision_models = config.get("SQ_VISION_MODELS", "llava,moondream,bakllava,llava-llama3,minicpm-v").split(",")
        guarder_lower = self.guarder_model.lower()
        is_vision_model = any(vm in guarder_lower for vm in vision_models)
        
        if not is_vision_model:
            # Non-vision model - cannot describe images
            return ""
        
        try:
            image_data = prepare_image_for_llm_base64(frame_path, preset="fast")
        except Exception:
            return ""
        
        ollama_url = config.get("SQ_OLLAMA_URL", DEFAULT_OLLAMA_URL)
        
        prompt = f"""Describe the {self.focus} briefly (max 10 words). Just describe what you see, no format.
If no {self.focus}: say "No {self.focus} visible"
Answer:"""
        
        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.guarder_model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                },
                timeout=int(config.get("SQ_VISION_TIMEOUT_LONG", "12")),
            )
            
            if resp.ok:
                summary = resp.json().get("response", "").strip()
                # Clean up
                summary = summary.replace('"', '').replace("'", "")
                summary = summary.split('\n')[0].strip()
                return summary[:int(config.get("SQ_VISION_SUMMARY_MAX_LENGTH", "80"))]
            
            return ""
            
        except Exception:
            return ""
    
    def _llm_check_change(self, current: str, previous: str) -> bool:
        """Check if there's meaningful change between summaries."""
        import requests
        from .config import config
        
        ollama_url = config.get("SQ_OLLAMA_URL", DEFAULT_OLLAMA_URL)
        
        prompt = f"""Compare these two observations:
BEFORE: "{previous}"
NOW: "{current}"

Is there a MEANINGFUL change? (person moved, different action, appeared/left)
Same position/action = NO change.
Answer only: YES or NO"""
        
        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.guarder_model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=8,
            )
            
            if resp.ok:
                answer = resp.json().get("response", "").strip().upper()
                return "YES" in answer
            
            return True  # Assume change on error
            
        except Exception:
            return True
    
    def _classify_motion(self, motion_pct: float) -> MotionLevel:
        """Classify motion percentage into level."""
        
        if motion_pct < float(config.get("SQ_MOTION_MIN_PERCENT", "0.5")):
            return MotionLevel.NONE
        elif motion_pct < float(config.get("SQ_MOTION_LOW_PERCENT", "1.0")):
            return MotionLevel.MINIMAL
        elif motion_pct < float(config.get("SQ_MOTION_MEDIUM_PERCENT", "5.0")):
            return MotionLevel.LOW
        elif motion_pct < float(config.get("SQ_MOTION_HIGH_PERCENT", "15.0")):
            return MotionLevel.MEDIUM
        else:
            return MotionLevel.HIGH
    
    def reset(self):
        """Reset detector state."""
        self._prev_summary = ""
        self._prev_detection = None
        self._consecutive_no_target = 0


# Convenience function
_detector: Optional[SmartDetector] = None


def get_smart_detector(focus: str = "person", **kwargs) -> SmartDetector:
    """Get or create smart detector."""
    global _detector
    if _detector is None or _detector.focus != focus:
        _detector = SmartDetector(focus=focus, **kwargs)
    return _detector
