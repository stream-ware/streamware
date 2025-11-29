"""
Presets - Descriptive parameters for intuitive configuration

Instead of numeric values like --threshold 10 --min-region 50,
use descriptive parameters that explain WHAT they do:

ANALYSIS DEPTH (how thoroughly to analyze):
    --analysis quick    # Fast, may miss details (good for overview)
    --analysis normal   # Balanced (default)
    --analysis deep     # Thorough, catches subtle changes
    --analysis forensic # Maximum detail, slow

MOTION DETECTION (how to detect movement):
    --motion any        # Detect all movement (noisy)
    --motion significant # Only notable movement (default)
    --motion objects    # Only when objects move
    --motion people     # Only human movement

FRAME PROCESSING (which frames to analyze):
    --frames all        # Analyze every frame
    --frames changed    # Only frames with changes (default)
    --frames keyframes  # Only significant keyframes
    --frames periodic   # Every Nth frame

AI FOCUS (what to look for):
    --focus general     # Describe everything
    --focus person      # Track people
    --focus activity    # Focus on actions/movement
    --focus security    # Look for threats/intrusions

Examples:
    sq live narrator --url $URL --analysis deep --motion people --focus person
    sq watch --url $URL --motion significant --frames changed --alert speak
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class Sensitivity(Enum):
    """Detection sensitivity presets"""
    ULTRA = "ultra"      # Detect even tiny changes (noisy, many false positives)
    HIGH = "high"        # Sensitive detection (good for security)
    MEDIUM = "medium"    # Balanced (default)
    LOW = "low"          # Only significant changes (fewer false alarms)
    MINIMAL = "minimal"  # Only major changes (very stable scenes)


class Speed(Enum):
    """Analysis speed presets"""
    REALTIME = "realtime"  # As fast as possible (high CPU)
    FAST = "fast"          # Quick checks, every 1-2s
    NORMAL = "normal"      # Balanced, every 3-5s (default)
    SLOW = "slow"          # Careful analysis, every 10s
    THOROUGH = "thorough"  # Deep analysis, every 30s


class Accuracy(Enum):
    """AI accuracy presets"""
    QUICK = "quick"        # Fast AI, may miss details
    BALANCED = "balanced"  # Good balance (default)
    PRECISE = "precise"    # Detailed analysis, slower
    EXPERT = "expert"      # Maximum accuracy, slowest


class DetectType(Enum):
    """What to detect"""
    PERSON = "person"
    PEOPLE = "people"       # Multiple people
    FACE = "face"
    VEHICLE = "vehicle"
    CAR = "car"
    ANIMAL = "animal"
    PET = "pet"
    PACKAGE = "package"
    MOTION = "motion"       # Any movement
    INTRUSION = "intrusion" # Unauthorized entry
    OBJECT = "object"       # Any object change
    ANY = "any"             # Anything


class WhenCondition(Enum):
    """When to trigger"""
    APPEARS = "appears"     # Object appears in frame
    DISAPPEARS = "disappears"  # Object leaves frame
    ENTERS = "enters"       # Object enters zone
    LEAVES = "leaves"       # Object exits zone
    MOVES = "moves"         # Object is moving
    STOPS = "stops"         # Object stops moving
    STAYS = "stays"         # Object stays too long
    CHANGES = "changes"     # Any change in scene


class AlertType(Enum):
    """How to alert"""
    NONE = "none"
    LOG = "log"
    SOUND = "sound"
    SPEAK = "speak"         # TTS
    SLACK = "slack"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"
    EMAIL = "email"
    RECORD = "record"       # Save video clip


# ============================================================================
# DESCRIPTIVE PARAMETERS (better than sensitivity levels)
# ============================================================================

class AnalysisDepth(Enum):
    """How thoroughly to analyze frames"""
    QUICK = "quick"        # Fast scan, may miss subtle details
    NORMAL = "normal"      # Balanced analysis (default)
    DEEP = "deep"          # Thorough, catches subtle changes
    FORENSIC = "forensic"  # Maximum detail, very slow


class MotionMode(Enum):
    """What kind of motion to detect"""
    ANY = "any"            # All movement (most sensitive, noisy)
    SIGNIFICANT = "significant"  # Only notable movement (default)
    OBJECTS = "objects"    # Only when distinct objects move
    PEOPLE = "people"      # Only human movement


class FrameMode(Enum):
    """Which frames to process"""
    ALL = "all"            # Every frame (resource intensive)
    CHANGED = "changed"    # Only when changes detected (default)
    KEYFRAMES = "keyframes"  # Only significant keyframes
    PERIODIC = "periodic"  # Every Nth frame


class FocusMode(Enum):
    """What the AI should focus on"""
    GENERAL = "general"    # Describe everything visible
    PERSON = "person"      # Track and describe people
    ACTIVITY = "activity"  # Focus on actions and movement
    SECURITY = "security"  # Look for threats/intrusions
    CHANGES = "changes"    # Only describe what changed


# Mapping descriptive params to numeric values
ANALYSIS_PRESETS = {
    "quick":    {"threshold": 30, "min_region": 300, "interval": 5, "ai_detail": "brief"},
    "normal":   {"threshold": 15, "min_region": 100, "interval": 3, "ai_detail": "normal"},
    "deep":     {"threshold": 8,  "min_region": 50,  "interval": 2, "ai_detail": "detailed"},
    "forensic": {"threshold": 3,  "min_region": 25,  "interval": 1, "ai_detail": "exhaustive"},
}

MOTION_PRESETS = {
    "any":         {"min_change": 0.1, "skip_stable": False, "edge_detect": False},
    "significant": {"min_change": 0.5, "skip_stable": True,  "edge_detect": False},
    "objects":     {"min_change": 1.0, "skip_stable": True,  "edge_detect": True},
    "people":      {"min_change": 0.3, "skip_stable": True,  "edge_detect": True, "focus": "person"},
}

FRAME_PRESETS = {
    "all":       {"interval": 0.5, "skip_unchanged": False},
    "changed":   {"interval": 2.0, "skip_unchanged": True},
    "keyframes": {"interval": 5.0, "skip_unchanged": True, "keyframe_only": True},
    "periodic":  {"interval": 10.0, "skip_unchanged": False},
}


def get_descriptive_preset(
    analysis: str = "normal",
    motion: str = "significant",
    frames: str = "changed",
    focus: str = "general"
) -> Dict[str, Any]:
    """
    Get optimized settings from descriptive parameters.
    
    Args:
        analysis: quick, normal, deep, forensic
        motion: any, significant, objects, people
        frames: all, changed, keyframes, periodic
        focus: general, person, activity, security, changes
    
    Returns:
        Dict with all numeric parameters optimized
    
    Example:
        settings = get_descriptive_preset(analysis="deep", motion="people", focus="person")
    """
    a = ANALYSIS_PRESETS.get(analysis, ANALYSIS_PRESETS["normal"])
    m = MOTION_PRESETS.get(motion, MOTION_PRESETS["significant"])
    f = FRAME_PRESETS.get(frames, FRAME_PRESETS["changed"])
    
    return {
        # Combined settings
        "threshold": a["threshold"],
        "min_region": a["min_region"],
        "interval": max(a["interval"], f["interval"]),
        "min_change": m["min_change"],
        "skip_stable": m.get("skip_stable", True),
        "edge_detect": m.get("edge_detect", False),
        "skip_unchanged": f.get("skip_unchanged", True),
        "ai_detail": a.get("ai_detail", "normal"),
        "focus": m.get("focus", focus),
        
        # Original descriptive params
        "_analysis": analysis,
        "_motion": motion,
        "_frames": frames,
        "_focus": focus,
    }


@dataclass
class DetectionPreset:
    """Optimized settings for a detection scenario"""
    # Pixel diff settings
    threshold: int          # 0-100, lower = more sensitive
    min_region: int         # Minimum changed pixels
    grid_size: int          # Grid for region detection
    
    # Timing
    interval: float         # Seconds between checks
    min_stable_frames: int  # Frames before "stable"
    
    # AI settings
    ai_enabled: bool
    ai_timeout: int         # Seconds
    focus_prompt: str       # What to look for
    
    # Alerts
    cooldown: float         # Seconds between alerts


# ============================================================================
# SENSITIVITY PRESETS
# ============================================================================

SENSITIVITY_PRESETS: Dict[str, DetectionPreset] = {
    "ultra": DetectionPreset(
        threshold=3,
        min_region=25,
        grid_size=16,
        interval=1.0,
        min_stable_frames=1,
        ai_enabled=True,
        ai_timeout=30,
        focus_prompt="",
        cooldown=5.0
    ),
    "high": DetectionPreset(
        threshold=8,
        min_region=50,
        grid_size=12,
        interval=2.0,
        min_stable_frames=2,
        ai_enabled=True,
        ai_timeout=30,
        focus_prompt="",
        cooldown=10.0
    ),
    "medium": DetectionPreset(
        threshold=15,
        min_region=100,
        grid_size=8,
        interval=3.0,
        min_stable_frames=3,
        ai_enabled=True,
        ai_timeout=30,
        focus_prompt="",
        cooldown=15.0
    ),
    "low": DetectionPreset(
        threshold=25,
        min_region=200,
        grid_size=6,
        interval=5.0,
        min_stable_frames=4,
        ai_enabled=True,
        ai_timeout=30,
        focus_prompt="",
        cooldown=30.0
    ),
    "minimal": DetectionPreset(
        threshold=40,
        min_region=500,
        grid_size=4,
        interval=10.0,
        min_stable_frames=5,
        ai_enabled=True,
        ai_timeout=30,
        focus_prompt="",
        cooldown=60.0
    ),
}


# ============================================================================
# DETECTION TYPE PRESETS
# ============================================================================

DETECT_PRESETS: Dict[str, Dict[str, Any]] = {
    "person": {
        "focus_prompt": "person, human, people",
        "min_region": 100,
        "sensitivity_boost": 1.2,  # Slightly more sensitive
        "ai_required": True,
    },
    "people": {
        "focus_prompt": "people, crowd, group of people",
        "min_region": 150,
        "sensitivity_boost": 1.0,
        "ai_required": True,
    },
    "face": {
        "focus_prompt": "face, facial features",
        "min_region": 50,
        "sensitivity_boost": 1.5,
        "ai_required": True,
    },
    "vehicle": {
        "focus_prompt": "vehicle, car, truck, motorcycle, bicycle",
        "min_region": 300,
        "sensitivity_boost": 0.8,
        "ai_required": True,
    },
    "car": {
        "focus_prompt": "car, automobile",
        "min_region": 400,
        "sensitivity_boost": 0.7,
        "ai_required": True,
    },
    "animal": {
        "focus_prompt": "animal, pet, dog, cat, bird",
        "min_region": 80,
        "sensitivity_boost": 1.3,
        "ai_required": True,
    },
    "pet": {
        "focus_prompt": "pet, dog, cat",
        "min_region": 60,
        "sensitivity_boost": 1.4,
        "ai_required": True,
    },
    "package": {
        "focus_prompt": "package, box, delivery, parcel",
        "min_region": 100,
        "sensitivity_boost": 1.1,
        "ai_required": True,
    },
    "motion": {
        "focus_prompt": "",
        "min_region": 50,
        "sensitivity_boost": 1.5,
        "ai_required": False,  # Pure pixel diff
    },
    "intrusion": {
        "focus_prompt": "intruder, unauthorized person, suspicious activity",
        "min_region": 100,
        "sensitivity_boost": 1.3,
        "ai_required": True,
    },
    "object": {
        "focus_prompt": "objects, items",
        "min_region": 100,
        "sensitivity_boost": 1.0,
        "ai_required": True,
    },
    "any": {
        "focus_prompt": "",
        "min_region": 50,
        "sensitivity_boost": 1.2,
        "ai_required": False,
    },
}


# ============================================================================
# SPEED PRESETS
# ============================================================================

SPEED_PRESETS: Dict[str, Dict[str, Any]] = {
    "realtime": {"interval": 0.5, "buffer_size": 100, "skip_stable": False},
    "fast": {"interval": 1.5, "buffer_size": 50, "skip_stable": True},
    "normal": {"interval": 3.0, "buffer_size": 30, "skip_stable": True},
    "slow": {"interval": 8.0, "buffer_size": 20, "skip_stable": True},
    "thorough": {"interval": 20.0, "buffer_size": 10, "skip_stable": False},
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_preset(
    sensitivity: str = "medium",
    detect: str = "any",
    speed: str = "normal"
) -> Dict[str, Any]:
    """
    Get optimized settings from qualitative parameters.
    
    Args:
        sensitivity: ultra, high, medium, low, minimal
        detect: person, vehicle, animal, motion, any, etc.
        speed: realtime, fast, normal, slow, thorough
    
    Returns:
        Dict with all numeric parameters optimized for the use case
    
    Example:
        settings = get_preset(sensitivity="high", detect="person", speed="fast")
        # Returns: {threshold: 6, min_region: 80, interval: 1.5, ...}
    """
    # Start with sensitivity preset
    base = SENSITIVITY_PRESETS.get(sensitivity, SENSITIVITY_PRESETS["medium"])
    
    # Get detection type modifiers
    detect_mods = DETECT_PRESETS.get(detect, DETECT_PRESETS["any"])
    
    # Get speed modifiers
    speed_mods = SPEED_PRESETS.get(speed, SPEED_PRESETS["normal"])
    
    # Combine settings
    boost = detect_mods.get("sensitivity_boost", 1.0)
    
    return {
        # Pixel diff (adjusted by detection type)
        "threshold": max(1, int(base.threshold / boost)),
        "min_region": detect_mods.get("min_region", base.min_region),
        "grid_size": base.grid_size,
        
        # Timing (from speed preset)
        "interval": speed_mods["interval"],
        "buffer_size": speed_mods["buffer_size"],
        "min_stable_frames": base.min_stable_frames,
        
        # AI settings
        "ai_enabled": detect_mods.get("ai_required", True),
        "ai_timeout": base.ai_timeout,
        "focus": detect_mods.get("focus_prompt", ""),
        
        # Alerts
        "cooldown": base.cooldown,
        
        # Original qualitative params (for reference)
        "_sensitivity": sensitivity,
        "_detect": detect,
        "_speed": speed,
    }


def build_uri_params(
    sensitivity: str = "medium",
    detect: str = "any",
    speed: str = "normal",
    when: str = "changes",
    alert: str = "none",
    **extra
) -> str:
    """
    Build URI parameters from qualitative settings.
    
    Example:
        params = build_uri_params(sensitivity="high", detect="person", speed="fast")
        uri = f"watch://stream?source={url}&{params}"
    """
    settings = get_preset(sensitivity, detect, speed)
    
    parts = [
        f"threshold={settings['threshold']}",
        f"min_region={settings['min_region']}",
        f"grid={settings['grid_size']}",
        f"interval={settings['interval']}",
        f"buffer_size={settings['buffer_size']}",
    ]
    
    if settings["focus"]:
        parts.append(f"focus={settings['focus']}")
    
    if not settings["ai_enabled"]:
        parts.append("no_ai=true")
    
    # Add condition
    if when != "changes":
        parts.append(f"when={when}")
    
    # Add alert
    if alert != "none":
        parts.append(f"alert={alert}")
    
    # Add any extra params
    for k, v in extra.items():
        parts.append(f"{k}={v}")
    
    return "&".join(parts)


def describe_settings(sensitivity: str, detect: str, speed: str) -> str:
    """
    Get human-readable description of settings.
    
    Example:
        print(describe_settings("high", "person", "fast"))
        # "High sensitivity person detection, checking every 1.5s"
    """
    settings = get_preset(sensitivity, detect, speed)
    
    sens_desc = {
        "ultra": "Ultra-sensitive (may have false positives)",
        "high": "High sensitivity",
        "medium": "Balanced sensitivity",
        "low": "Low sensitivity (fewer false alarms)",
        "minimal": "Minimal sensitivity (major changes only)",
    }
    
    detect_desc = {
        "person": "person detection",
        "people": "people/crowd detection",
        "vehicle": "vehicle detection",
        "animal": "animal detection",
        "motion": "motion detection (no AI)",
        "any": "any change detection",
    }
    
    speed_desc = f"checking every {settings['interval']}s"
    
    return f"{sens_desc.get(sensitivity, sensitivity)} {detect_desc.get(detect, detect)}, {speed_desc}"


# ============================================================================
# CLI ARGUMENT HELPERS
# ============================================================================

def add_qualitative_args(parser):
    """Add qualitative arguments to argparse parser"""
    parser.add_argument(
        '--sensitivity', '-s',
        choices=['ultra', 'high', 'medium', 'low', 'minimal'],
        default='medium',
        help='Detection sensitivity (default: medium)'
    )
    parser.add_argument(
        '--detect', '-d',
        choices=['person', 'people', 'face', 'vehicle', 'car', 'animal', 'pet',
                 'package', 'motion', 'intrusion', 'object', 'any'],
        default='any',
        help='What to detect (default: any)'
    )
    parser.add_argument(
        '--speed',
        choices=['realtime', 'fast', 'normal', 'slow', 'thorough'],
        default='normal',
        help='Analysis speed (default: normal)'
    )
    parser.add_argument(
        '--when', '-w',
        choices=['appears', 'disappears', 'enters', 'leaves', 'moves', 'stops', 'stays', 'changes'],
        default='changes',
        help='When to trigger (default: changes)'
    )
    parser.add_argument(
        '--alert', '-a',
        choices=['none', 'log', 'sound', 'speak', 'slack', 'telegram', 'webhook', 'record'],
        default='none',
        help='How to alert (default: none)'
    )


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def watch_person(url: str, sensitivity: str = "high", alert: str = "speak") -> Dict:
    """Watch for people with optimal settings"""
    from .core import flow
    params = build_uri_params(sensitivity=sensitivity, detect="person", speed="fast", alert=alert)
    return flow(f"watch://stream?source={url}&{params}").run()


def watch_vehicle(url: str, sensitivity: str = "medium", alert: str = "log") -> Dict:
    """Watch for vehicles with optimal settings"""
    from .core import flow
    params = build_uri_params(sensitivity=sensitivity, detect="vehicle", speed="normal", alert=alert)
    return flow(f"watch://stream?source={url}&{params}").run()


def watch_motion(url: str, sensitivity: str = "high") -> Dict:
    """Watch for any motion (no AI, fast)"""
    from .core import flow
    params = build_uri_params(sensitivity=sensitivity, detect="motion", speed="fast")
    return flow(f"watch://stream?source={url}&{params}").run()


def watch_package(url: str, alert: str = "slack") -> Dict:
    """Watch for package delivery"""
    from .core import flow
    params = build_uri_params(sensitivity="high", detect="package", speed="normal", alert=alert)
    return flow(f"watch://stream?source={url}&{params}").run()


def security_watch(url: str, alert: str = "slack") -> Dict:
    """Security monitoring with high sensitivity"""
    from .core import flow
    params = build_uri_params(sensitivity="high", detect="intrusion", speed="fast", alert=alert)
    return flow(f"watch://stream?source={url}&{params}").run()
