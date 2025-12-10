"""
Detection Pipeline - Prioritized Multi-Stage Detection System

Provides intelligent detection with priority-based processing:
- Stage 1: Fast local detection (OpenCV, PIL)
- Stage 2: Small LLM validation (gemma:2b, qwen2.5:3b)
- Stage 3: Large LLM description (llava, gpt-4o)

Each stage can short-circuit if detection is confident enough.

Usage:
    from streamware.detection_pipeline import DetectionPipeline, UserIntent
    
    # Create pipeline based on user intent
    pipeline = DetectionPipeline.from_intent("notify me when someone enters")
    
    # Or with explicit config
    pipeline = DetectionPipeline(
        intent=UserIntent.ALERT_ON_ENTRY,
        focus="person",
        sensitivity="high"
    )
    
    result = pipeline.process(frame_path, prev_frame_path)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable, Any

logger = logging.getLogger(__name__)


# =============================================================================
# USER INTENTS - What the user wants to achieve
# =============================================================================

class UserIntent(Enum):
    """User's goal - determines pipeline configuration."""
    
    # Monitoring intents
    WATCH_GENERAL = auto()          # "watch this camera"
    TRACK_PERSON = auto()           # "track people", "follow person"
    TRACK_OBJECT = auto()           # "track cars", "watch for packages"
    
    # Alert intents
    ALERT_ON_ENTRY = auto()         # "notify when someone enters"
    ALERT_ON_EXIT = auto()          # "notify when someone leaves"
    ALERT_ON_MOTION = auto()        # "alert on any motion"
    ALERT_ON_CHANGE = auto()        # "notify if anything changes"
    
    # Security intents
    SECURITY_WATCH = auto()         # "security monitoring"
    INTRUSION_DETECT = auto()       # "detect intruders"
    
    # Activity intents
    ACTIVITY_LOG = auto()           # "log all activity"
    BEHAVIOR_WATCH = auto()         # "watch what they're doing"
    
    # Custom
    CUSTOM = auto()                 # User-defined rules


# Intent keywords for parsing user input
INTENT_KEYWORDS = {
    UserIntent.TRACK_PERSON: [
        "track person", "follow person", "watch person", "monitor person",
        "track people", "detect person", "find person", "osoba", "człowiek"
    ],
    UserIntent.TRACK_OBJECT: [
        "track car", "track vehicle", "watch package", "monitor object",
        "detect object", "find object", "samochód", "paczka"
    ],
    UserIntent.ALERT_ON_ENTRY: [
        "notify when enter", "alert when enter", "someone enters",
        "person enters", "detect entry", "wchodzi", "wejście"
    ],
    UserIntent.ALERT_ON_EXIT: [
        "notify when leave", "alert when exit", "someone leaves",
        "person exits", "detect exit", "wychodzi", "wyjście"
    ],
    UserIntent.ALERT_ON_MOTION: [
        "motion alert", "detect motion", "any movement", "ruch"
    ],
    UserIntent.ALERT_ON_CHANGE: [
        "notify change", "alert change", "anything changes", "zmiana"
    ],
    UserIntent.SECURITY_WATCH: [
        "security", "surveillance", "guard", "protect", "bezpieczeństwo"
    ],
    UserIntent.INTRUSION_DETECT: [
        "intruder", "intrusion", "break in", "unauthorized", "włamanie"
    ],
    UserIntent.ACTIVITY_LOG: [
        "log activity", "record activity", "log everything", "aktywność"
    ],
    UserIntent.BEHAVIOR_WATCH: [
        "what doing", "behavior", "action", "activity", "co robi"
    ],
}


def parse_user_intent(user_input: str) -> Tuple[UserIntent, Dict[str, Any]]:
    """Parse user input to determine intent and parameters.
    
    Args:
        user_input: Natural language description of what user wants
        
    Returns:
        (intent, params) tuple
    """
    input_lower = user_input.lower()
    params = {}
    
    # Check for focus objects
    focus_keywords = {
        "person": ["person", "people", "human", "someone", "osoba", "człowiek"],
        "car": ["car", "vehicle", "auto", "samochód"],
        "animal": ["animal", "pet", "dog", "cat", "zwierzę", "pies", "kot"],
        "package": ["package", "delivery", "box", "paczka"],
    }
    
    for focus, keywords in focus_keywords.items():
        if any(kw in input_lower for kw in keywords):
            params["focus"] = focus
            break
    else:
        params["focus"] = "person"  # Default
    
    # Check for sensitivity
    if any(w in input_lower for w in ["high", "sensitive", "all", "każdy"]):
        params["sensitivity"] = "high"
    elif any(w in input_lower for w in ["low", "only important", "tylko ważne"]):
        params["sensitivity"] = "low"
    else:
        params["sensitivity"] = "medium"
    
    # Match intent
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in input_lower for kw in keywords):
            return intent, params
    
    # Default based on keywords
    if "track" in input_lower or "śledź" in input_lower:
        return UserIntent.TRACK_PERSON, params
    elif "alert" in input_lower or "notify" in input_lower or "powiadom" in input_lower:
        return UserIntent.ALERT_ON_MOTION, params
    elif "security" in input_lower or "bezpieczeństwo" in input_lower:
        return UserIntent.SECURITY_WATCH, params
    
    return UserIntent.WATCH_GENERAL, params


# =============================================================================
# DETECTION METHODS - Available detection techniques
# =============================================================================

class DetectionMethod(Enum):
    """Available detection methods with priority."""
    
    # Local/Fast methods (priority 1-10)
    PIXEL_DIFF = 1              # Simple pixel difference
    MOTION_OPENCV = 2           # OpenCV motion detection
    EDGE_DETECT = 3             # Edge detection
    HOG_PERSON = 4              # HOG person detector
    HAAR_FACE = 5               # Haar cascade face
    CONTOUR_DETECT = 6          # Contour-based detection
    BACKGROUND_SUB = 7          # Background subtraction
    OPTICAL_FLOW = 8            # Optical flow
    
    # Small LLM methods (priority 20-30)
    LLM_QUICK_CHECK = 20        # Quick YES/NO from small LLM
    LLM_QUICK_SUMMARY = 21      # Short summary from small LLM
    LLM_CHANGE_CHECK = 22       # Compare two states
    LLM_CLASSIFY = 23           # Classify scene/action
    
    # Large LLM methods (priority 40-50)
    LLM_FULL_DESCRIBE = 40      # Full description
    LLM_DETAILED_ANALYSIS = 41  # Detailed analysis
    LLM_CONVERSATION = 42       # Conversational response


@dataclass
class DetectionConfig:
    """Configuration for a detection method."""
    method: DetectionMethod
    enabled: bool = True
    priority: int = 0           # Lower = run first
    confidence_threshold: float = 0.7
    timeout_ms: int = 5000
    model: str = ""             # For LLM methods
    params: Dict = field(default_factory=dict)


# =============================================================================
# LLM REGISTRY - Available LLMs and their capabilities
# =============================================================================

@dataclass
class LLMCapability:
    """Describes what an LLM can do."""
    name: str
    provider: str               # ollama, openai, anthropic
    size: str                   # small, medium, large
    vision: bool                # Can process images
    speed: str                  # fast, medium, slow
    quality: str                # low, medium, high
    cost: str                   # free, low, medium, high
    
    # Capabilities
    can_detect: bool = True     # YES/NO detection
    can_summarize: bool = True  # Short summaries
    can_describe: bool = True   # Full descriptions
    can_compare: bool = True    # Compare two states
    can_classify: bool = True   # Classify scenes
    can_converse: bool = False  # Conversational


# LLM Registry - all available models
LLM_REGISTRY: Dict[str, LLMCapability] = {
    # Small/Fast models (guarder)
    "gemma:2b": LLMCapability(
        name="gemma:2b", provider="ollama", size="small",
        vision=False, speed="fast", quality="medium", cost="free",
        can_describe=False, can_converse=False
    ),
    "qwen2.5:3b": LLMCapability(
        name="qwen2.5:3b", provider="ollama", size="small",
        vision=False, speed="fast", quality="medium", cost="free",
        can_describe=False, can_converse=False
    ),
    "phi3:mini": LLMCapability(
        name="phi3:mini", provider="ollama", size="small",
        vision=False, speed="fast", quality="medium", cost="free",
        can_describe=False, can_converse=False
    ),
    
    # Vision models (medium)
    "llava:7b": LLMCapability(
        name="llava:7b", provider="ollama", size="medium",
        vision=True, speed="medium", quality="medium", cost="free",
        can_converse=False
    ),
    "moondream": LLMCapability(
        name="moondream", provider="ollama", size="small",
        vision=True, speed="fast", quality="low", cost="free",
        can_converse=False
    ),
    "bakllava": LLMCapability(
        name="bakllava", provider="ollama", size="medium",
        vision=True, speed="medium", quality="medium", cost="free",
        can_converse=False
    ),
    
    # Large vision models
    "llava:13b": LLMCapability(
        name="llava:13b", provider="ollama", size="large",
        vision=True, speed="slow", quality="high", cost="free",
        can_converse=True
    ),
    "llava:34b": LLMCapability(
        name="llava:34b", provider="ollama", size="large",
        vision=True, speed="slow", quality="high", cost="free",
        can_converse=True
    ),
    
    # Cloud models
    "gpt-4o": LLMCapability(
        name="gpt-4o", provider="openai", size="large",
        vision=True, speed="medium", quality="high", cost="high",
        can_converse=True
    ),
    "gpt-4o-mini": LLMCapability(
        name="gpt-4o-mini", provider="openai", size="medium",
        vision=True, speed="fast", quality="medium", cost="medium",
        can_converse=True
    ),
    "claude-3-sonnet": LLMCapability(
        name="claude-3-sonnet", provider="anthropic", size="large",
        vision=True, speed="medium", quality="high", cost="high",
        can_converse=True
    ),
}


def get_best_llm_for_task(
    task: str,
    require_vision: bool = False,
    prefer_speed: bool = True,
    prefer_quality: bool = False,
    available_models: List[str] = None,
) -> Optional[str]:
    """Find best LLM for a specific task.
    
    Args:
        task: detect, summarize, describe, compare, classify, converse
        require_vision: Must support image input
        prefer_speed: Prefer faster models
        prefer_quality: Prefer higher quality models
        available_models: List of available model names
        
    Returns:
        Model name or None
    """
    candidates = []
    
    for name, cap in LLM_REGISTRY.items():
        # Filter by availability
        if available_models and name not in available_models:
            continue
        
        # Filter by vision requirement
        if require_vision and not cap.vision:
            continue
        
        # Filter by task capability
        task_map = {
            "detect": cap.can_detect,
            "summarize": cap.can_summarize,
            "describe": cap.can_describe,
            "compare": cap.can_compare,
            "classify": cap.can_classify,
            "converse": cap.can_converse,
        }
        if not task_map.get(task, True):
            continue
        
        # Score model
        score = 0
        if prefer_speed:
            score += {"fast": 3, "medium": 2, "slow": 1}.get(cap.speed, 0)
        if prefer_quality:
            score += {"high": 3, "medium": 2, "low": 1}.get(cap.quality, 0)
        # Prefer free models
        score += {"free": 2, "low": 1, "medium": 0, "high": -1}.get(cap.cost, 0)
        
        candidates.append((name, score))
    
    if not candidates:
        return None
    
    # Sort by score descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0]


# =============================================================================
# DETECTION PIPELINE
# =============================================================================

@dataclass
class PipelineResult:
    """Result from detection pipeline."""
    # Detection results
    detected: bool = False
    target_present: bool = False
    confidence: float = 0.0
    
    # Content
    summary: str = ""
    description: str = ""
    
    # Actions
    should_notify: bool = False
    should_speak: bool = False
    should_log: bool = False
    
    # Metadata
    method_used: str = ""
    stages_run: List[str] = field(default_factory=list)
    total_time_ms: float = 0.0
    
    # Skip info
    skipped: bool = False
    skip_reason: str = ""


class DetectionPipeline:
    """Prioritized multi-stage detection pipeline."""
    
    def __init__(
        self,
        intent: UserIntent = UserIntent.TRACK_PERSON,
        focus: str = "person",
        sensitivity: str = "medium",
        guarder_model: str = "gemma:2b",
        vision_model: str = "llava:7b",
    ):
        self.intent = intent
        self.focus = focus
        self.sensitivity = sensitivity
        self.guarder_model = guarder_model
        self.vision_model = vision_model
        
        # State
        self._prev_summary: str = ""
        self._prev_state: Dict = {}
        self._consecutive_skip: int = 0
        
        # Configure pipeline based on intent
        self._stages = self._configure_stages()
    
    @classmethod
    def from_intent(cls, user_input: str, **kwargs) -> "DetectionPipeline":
        """Create pipeline from natural language intent.
        
        Args:
            user_input: e.g. "notify me when someone enters the room"
            **kwargs: Override parameters
            
        Returns:
            Configured pipeline
        """
        intent, params = parse_user_intent(user_input)
        params.update(kwargs)
        
        return cls(
            intent=intent,
            focus=params.get("focus", "person"),
            sensitivity=params.get("sensitivity", "medium"),
            **{k: v for k, v in kwargs.items() if k not in ["focus", "sensitivity"]}
        )
    
    def _configure_stages(self) -> List[DetectionConfig]:
        """Configure detection stages based on intent."""
        stages = []
        
        # Sensitivity affects thresholds
        thresholds = {
            "high": 0.3,
            "medium": 0.5,
            "low": 0.7,
        }
        conf_threshold = thresholds.get(self.sensitivity, 0.5)
        
        # Stage 1: Always start with motion detection
        stages.append(DetectionConfig(
            method=DetectionMethod.MOTION_OPENCV,
            priority=1,
            confidence_threshold=conf_threshold,
            timeout_ms=100,
        ))
        
        # Stage 2: Person detection for person-focused intents
        if self.focus == "person":
            stages.append(DetectionConfig(
                method=DetectionMethod.HOG_PERSON,
                priority=2,
                confidence_threshold=conf_threshold,
                timeout_ms=200,
            ))
        
        # Stage 3: Quick LLM check
        stages.append(DetectionConfig(
            method=DetectionMethod.LLM_QUICK_CHECK,
            priority=20,
            confidence_threshold=0.7,
            timeout_ms=3000,
            model=self.guarder_model,
        ))
        
        # Stage 4: Quick summary (for tracking/logging intents)
        if self.intent in [
            UserIntent.TRACK_PERSON, UserIntent.TRACK_OBJECT,
            UserIntent.ACTIVITY_LOG, UserIntent.BEHAVIOR_WATCH
        ]:
            stages.append(DetectionConfig(
                method=DetectionMethod.LLM_QUICK_SUMMARY,
                priority=21,
                timeout_ms=5000,
                model=self.guarder_model,
            ))
        
        # Stage 5: Change detection (for alert intents)
        if self.intent in [
            UserIntent.ALERT_ON_ENTRY, UserIntent.ALERT_ON_EXIT,
            UserIntent.ALERT_ON_CHANGE, UserIntent.SECURITY_WATCH
        ]:
            stages.append(DetectionConfig(
                method=DetectionMethod.LLM_CHANGE_CHECK,
                priority=22,
                timeout_ms=3000,
                model=self.guarder_model,
            ))
        
        # Stage 6: Full description (only when needed)
        if self.intent in [
            UserIntent.BEHAVIOR_WATCH, UserIntent.SECURITY_WATCH,
            UserIntent.INTRUSION_DETECT
        ]:
            stages.append(DetectionConfig(
                method=DetectionMethod.LLM_FULL_DESCRIBE,
                priority=40,
                timeout_ms=10000,
                model=self.vision_model,
            ))
        
        return sorted(stages, key=lambda s: s.priority)
    
    def process(
        self,
        frame_path: Path,
        prev_frame_path: Optional[Path] = None,
    ) -> PipelineResult:
        """Run detection pipeline on frame.
        
        Args:
            frame_path: Current frame
            prev_frame_path: Previous frame for comparison
            
        Returns:
            PipelineResult with all detection info
        """
        result = PipelineResult()
        start_time = time.time()
        
        # Run stages in priority order
        for stage in self._stages:
            if not stage.enabled:
                continue
            
            stage_result = self._run_stage(stage, frame_path, prev_frame_path, result)
            result.stages_run.append(stage.method.name)
            
            # Check if we can short-circuit
            if stage_result.get("skip"):
                result.skipped = True
                result.skip_reason = stage_result.get("reason", "")
                break
            
            # Update result with stage output
            if stage_result.get("detected"):
                result.detected = True
                result.target_present = True
                result.confidence = max(result.confidence, stage_result.get("confidence", 0))
            
            if stage_result.get("summary"):
                result.summary = stage_result["summary"]
            
            if stage_result.get("description"):
                result.description = stage_result["description"]
            
            # Check if we have enough info
            if self._can_short_circuit(stage, result):
                result.method_used = stage.method.name
                break
        
        # Determine actions based on intent
        self._determine_actions(result)
        
        result.total_time_ms = (time.time() - start_time) * 1000
        return result
    
    def _run_stage(
        self,
        stage: DetectionConfig,
        frame_path: Path,
        prev_frame_path: Optional[Path],
        current_result: PipelineResult,
    ) -> Dict:
        """Run a single detection stage."""
        
        method = stage.method
        
        if method == DetectionMethod.MOTION_OPENCV:
            return self._detect_motion(frame_path, prev_frame_path, stage)
        
        elif method == DetectionMethod.HOG_PERSON:
            return self._detect_person_hog(frame_path, stage)
        
        elif method == DetectionMethod.LLM_QUICK_CHECK:
            return self._llm_quick_check(frame_path, stage)
        
        elif method == DetectionMethod.LLM_QUICK_SUMMARY:
            return self._llm_quick_summary(frame_path, stage)
        
        elif method == DetectionMethod.LLM_CHANGE_CHECK:
            return self._llm_change_check(current_result.summary, stage)
        
        elif method == DetectionMethod.LLM_FULL_DESCRIBE:
            return self._llm_full_describe(frame_path, stage)
        
        return {}
    
    def _detect_motion(self, frame_path: Path, prev_frame_path: Optional[Path], stage: DetectionConfig) -> Dict:
        """OpenCV motion detection."""
        if not prev_frame_path:
            return {"detected": True, "confidence": 1.0, "motion_pct": 100}
        
        try:
            import cv2
            
            curr = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
            prev = cv2.imread(str(prev_frame_path), cv2.IMREAD_GRAYSCALE)
            
            if curr is None or prev is None:
                return {"detected": True, "confidence": 0.5}
            
            # Resize for speed
            scale = min(320 / curr.shape[1], 240 / curr.shape[0], 1.0)
            if scale < 1.0:
                curr = cv2.resize(curr, None, fx=scale, fy=scale)
                prev = cv2.resize(prev, None, fx=scale, fy=scale)
            
            curr = cv2.GaussianBlur(curr, (5, 5), 0)
            prev = cv2.GaussianBlur(prev, (5, 5), 0)
            
            diff = cv2.absdiff(curr, prev)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            
            motion_pixels = cv2.countNonZero(thresh)
            total_pixels = thresh.shape[0] * thresh.shape[1]
            motion_pct = (motion_pixels / total_pixels) * 100
            
            if motion_pct < stage.confidence_threshold:
                return {"skip": True, "reason": f"no_motion_{motion_pct:.1f}%"}
            
            return {"detected": True, "confidence": min(motion_pct / 10, 1.0), "motion_pct": motion_pct}
            
        except Exception as e:
            logger.debug(f"Motion detection failed: {e}")
            return {"detected": True, "confidence": 0.5}
    
    def _detect_person_hog(self, frame_path: Path, stage: DetectionConfig) -> Dict:
        """HOG person detection."""
        try:
            import cv2
            
            hog = cv2.HOGDescriptor()
            hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
            
            img = cv2.imread(str(frame_path))
            if img is None:
                return {"detected": True, "confidence": 0.5}
            
            # Resize for speed
            h, w = img.shape[:2]
            scale = min(400 / w, 400 / h, 1.0)
            if scale < 1.0:
                img = cv2.resize(img, None, fx=scale, fy=scale)
            
            boxes, weights = hog.detectMultiScale(img, winStride=(8, 8), padding=(4, 4), scale=1.05)
            
            if len(boxes) > 0:
                confidence = float(max(weights)) if len(weights) > 0 else 0.5
                return {"detected": True, "confidence": min(confidence, 1.0)}
            
            # No person - but verify occasionally
            self._consecutive_skip += 1
            if self._consecutive_skip % 5 == 0:
                return {"detected": False, "confidence": 0.8}  # Continue to LLM check
            
            return {"skip": True, "reason": "hog_no_person"}
            
        except Exception:
            return {"detected": True, "confidence": 0.5}
    
    def _llm_quick_check(self, frame_path: Path, stage: DetectionConfig) -> Dict:
        """Quick LLM check: is target present?"""
        import requests
        from .config import config
        from .image_optimize import prepare_image_for_llm_base64
        
        try:
            image_data = prepare_image_for_llm_base64(frame_path, preset="fast")
        except Exception:
            return {"detected": True, "confidence": 0.5}
        
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        prompt = f"Is there a {self.focus} in this image? Answer only YES or NO."
        
        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": stage.model, "prompt": prompt, "images": [image_data], "stream": False},
                timeout=stage.timeout_ms / 1000,
            )
            
            if resp.ok:
                answer = resp.json().get("response", "").strip().upper()
                if "YES" in answer:
                    self._consecutive_skip = 0
                    return {"detected": True, "confidence": 0.9}
                elif "NO" in answer:
                    # Target left - this is notable
                    if self._prev_summary and self.focus in self._prev_summary.lower():
                        return {"detected": True, "summary": f"No {self.focus} visible", "confidence": 0.9}
                    return {"skip": True, "reason": f"llm_no_{self.focus}"}
            
            return {"detected": True, "confidence": 0.5}
            
        except Exception:
            return {"detected": True, "confidence": 0.5}
    
    def _llm_quick_summary(self, frame_path: Path, stage: DetectionConfig) -> Dict:
        """Get quick summary from small LLM."""
        import requests
        from .config import config
        from .image_optimize import prepare_image_for_llm_base64
        
        try:
            image_data = prepare_image_for_llm_base64(frame_path, preset="fast")
        except Exception:
            return {}
        
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        prompt = f"""Describe the {self.focus} in ONE short sentence (max 10 words).
Format: "{self.focus.title()}: [location], [action]"
Example: "Person: at desk, using computer"
Answer:"""
        
        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": stage.model, "prompt": prompt, "images": [image_data], "stream": False},
                timeout=stage.timeout_ms / 1000,
            )
            
            if resp.ok:
                summary = resp.json().get("response", "").strip()
                summary = summary.replace('"', '').replace("'", "").split('\n')[0][:80]
                self._prev_summary = summary
                return {"summary": summary}
            
            return {}
            
        except Exception:
            return {}
    
    def _llm_change_check(self, current_summary: str, stage: DetectionConfig) -> Dict:
        """Check if there's meaningful change."""
        import requests
        from .config import config
        
        if not self._prev_summary or not current_summary:
            return {}
        
        ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
        prompt = f"""Compare:
BEFORE: "{self._prev_summary}"
NOW: "{current_summary}"

Is there a MEANINGFUL change? (moved, different action, appeared/left)
Answer only: YES or NO"""
        
        try:
            resp = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": stage.model, "prompt": prompt, "stream": False},
                timeout=stage.timeout_ms / 1000,
            )
            
            if resp.ok:
                answer = resp.json().get("response", "").strip().upper()
                if "NO" in answer:
                    return {"skip": True, "reason": "no_change"}
            
            return {}
            
        except Exception:
            return {}
    
    def _llm_full_describe(self, frame_path: Path, stage: DetectionConfig) -> Dict:
        """Get full description from vision LLM."""
        from .llm_client import get_client
        
        try:
            client = get_client()
            result = client.analyze_image(
                frame_path,
                f"Describe what the {self.focus} is doing in detail.",
                model=stage.model
            )
            
            if result.get("success"):
                return {"description": result.get("response", "")}
            
            return {}
            
        except Exception:
            return {}
    
    def _can_short_circuit(self, stage: DetectionConfig, result: PipelineResult) -> bool:
        """Check if we can stop processing early."""
        # For tracking, summary is enough
        if self.intent in [UserIntent.TRACK_PERSON, UserIntent.TRACK_OBJECT]:
            if result.summary:
                return True
        
        # For alerts, detection is enough
        if self.intent in [UserIntent.ALERT_ON_ENTRY, UserIntent.ALERT_ON_EXIT, UserIntent.ALERT_ON_MOTION]:
            if result.detected and result.confidence > 0.7:
                return True
        
        return False
    
    def _determine_actions(self, result: PipelineResult):
        """Determine what actions to take based on intent and result."""
        if result.skipped:
            return
        
        # Notify for alert intents
        if self.intent in [
            UserIntent.ALERT_ON_ENTRY, UserIntent.ALERT_ON_EXIT,
            UserIntent.ALERT_ON_MOTION, UserIntent.ALERT_ON_CHANGE,
            UserIntent.SECURITY_WATCH, UserIntent.INTRUSION_DETECT
        ]:
            if result.detected and result.confidence > 0.6:
                result.should_notify = True
                result.should_speak = True
        
        # Log for tracking/logging intents
        if self.intent in [
            UserIntent.TRACK_PERSON, UserIntent.TRACK_OBJECT,
            UserIntent.ACTIVITY_LOG, UserIntent.BEHAVIOR_WATCH,
            UserIntent.WATCH_GENERAL
        ]:
            if result.detected:
                result.should_log = True
        
        # Speak for behavior watch
        if self.intent == UserIntent.BEHAVIOR_WATCH:
            if result.summary and "no " not in result.summary.lower():
                result.should_speak = True
    
    def reset(self):
        """Reset pipeline state."""
        self._prev_summary = ""
        self._prev_state = {}
        self._consecutive_skip = 0
