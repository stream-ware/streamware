"""
Narrator Data Models

Data classes and types for the narrator system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class Trigger:
    """Condition that triggers notification/alert."""
    pattern: str
    action: str = "notify"
    cooldown: int = 60  # seconds between triggers
    last_triggered: float = 0.0


@dataclass
class NarrationEntry:
    """Single narration log entry."""
    timestamp: datetime
    frame_num: int
    description: str
    raw_response: str = ""
    processing_time: float = 0.0
    motion_percent: float = 0.0
    yolo_detections: List[Dict] = field(default_factory=list)
    llm_used: bool = False
    triggered: bool = False
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "frame": self.frame_num,
            "description": self.description,
            "processing_time": self.processing_time,
            "motion": self.motion_percent,
            "yolo": self.yolo_detections,
            "llm": self.llm_used,
            "triggered": self.triggered,
        }


@dataclass
class DetectionResult:
    """Result from detection pipeline."""
    frame_num: int
    timestamp: datetime
    
    # YOLO detections
    yolo_objects: List[Dict] = field(default_factory=list)
    yolo_count: int = 0
    
    # Motion analysis
    motion_detected: bool = False
    motion_percent: float = 0.0
    motion_regions: List[Dict] = field(default_factory=list)
    
    # LLM description
    description: str = ""
    quick_summary: str = ""
    
    # Flags
    should_process_llm: bool = True
    should_notify: bool = False
    triggered: bool = False
    
    # Metadata
    processing_time: float = 0.0
    screenshot_path: Optional[str] = None


@dataclass
class NarratorConfig:
    """Configuration for narrator component."""
    # Source
    source_url: str = ""
    
    # Detection
    mode: str = "hybrid"  # yolo, llm, hybrid
    target: str = "person"
    confidence: float = 0.5
    
    # Timing
    duration: int = 60
    fps: float = 2.0
    interval: float = 0.5
    
    # Output
    tts_enabled: bool = False
    tts_mode: str = "normal"
    quiet: bool = False
    verbose: bool = False
    
    # Notifications
    notify_email: Optional[str] = None
    notify_slack: Optional[str] = None
    notify_telegram: Optional[str] = None
    notify_webhook: Optional[str] = None
    notify_mode: str = "digest"
    notify_interval: int = 60
    
    # Paths
    output_dir: Optional[str] = None
    log_file: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> "NarratorConfig":
        """Create config from environment variables."""
        from ..config import config
        
        return cls(
            source_url=config.get("SQ_DEFAULT_URL", ""),
            mode=config.get("SQ_MODE", "hybrid"),
            target=config.get("SQ_TARGET", "person"),
            confidence=float(config.get("SQ_CONFIDENCE", "0.5")),
            duration=int(config.get("SQ_DURATION", "60")),
            fps=float(config.get("SQ_FPS", "2.0")),
            tts_enabled=config.get("SQ_TTS", "false").lower() == "true",
            notify_email=config.get("SQ_NOTIFY_EMAIL") or None,
            notify_mode=config.get("SQ_NOTIFY_MODE", "digest"),
        )


@dataclass
class AnalysisStats:
    """Statistics for analysis session."""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    frames_processed: int = 0
    frames_skipped: int = 0
    
    detections_count: int = 0
    notifications_sent: int = 0
    
    yolo_calls: int = 0
    llm_calls: int = 0
    
    total_processing_time: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        duration = (self.end_time or datetime.now()) - self.start_time
        return {
            "duration_seconds": duration.total_seconds(),
            "frames_processed": self.frames_processed,
            "frames_skipped": self.frames_skipped,
            "detections": self.detections_count,
            "notifications": self.notifications_sent,
            "yolo_calls": self.yolo_calls,
            "llm_calls": self.llm_calls,
            "avg_processing_ms": (
                self.total_processing_time / self.frames_processed * 1000
                if self.frames_processed > 0 else 0
            ),
        }
