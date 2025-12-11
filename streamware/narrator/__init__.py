"""
Narrator Module - Refactored video analysis pipeline.

This module demonstrates the proposed refactoring of live_narrator.py
into smaller, focused components.

Architecture:
    ┌─────────────────────────────────────────────────────────────┐
    │                    NarratorOrchestrator                     │
    │                                                             │
    │  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐     │
    │  │ Capture │→ │ Detector │→ │ Tracker │→ │ Describer│     │
    │  └─────────┘  └──────────┘  └─────────┘  └──────────┘     │
    │       ↓            ↓             ↓            ↓            │
    │                    └─────────────┴────────────┘            │
    │                              ↓                              │
    │                      ┌────────────┐                        │
    │                      │   Output   │                        │
    │                      └────────────┘                        │
    └─────────────────────────────────────────────────────────────┘

Usage:
    from streamware.narrator import NarratorOrchestrator, NarratorConfig
    
    config = NarratorConfig.from_intent("track person")
    narrator = NarratorOrchestrator(config)
    narrator.run(duration=30)
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class NarratorConfig:
    """Unified configuration for narrator pipeline."""
    
    # Source
    url: str = ""
    
    # Detection
    mode: str = "track"
    focus: str = "person"
    fps: float = 1.0
    
    # LLM
    use_llm: bool = False
    llm_model: str = "llava:7b"
    skip_llm_threshold: float = 0.3
    
    # Tracking
    use_tracking: bool = True
    use_reid: bool = True
    
    # Output
    tts_enabled: bool = True
    tts_mode: str = "diff"
    log_format: str = "yaml"
    
    @classmethod
    def from_intent(cls, text: str) -> "NarratorConfig":
        """Create config from natural language."""
        from ..intent import parse_intent
        intent = parse_intent(text)
        return cls(
            mode=intent.mode,
            focus=intent.target,
            fps=intent.fps,
            use_llm=intent.llm,
            llm_model=intent.llm_model,
            tts_enabled=intent.tts,
            tts_mode=intent.tts_mode,
        )
    
    @classmethod
    def from_preset(cls, preset: str) -> "NarratorConfig":
        """Create config from preset name."""
        from ..workflow import load_workflow
        workflow = load_workflow(preset=preset)
        return cls(
            fps=workflow.fps,
            focus=workflow.detect_classes[0] if workflow.detect_classes else "person",
            use_llm=workflow.llm,
            llm_model=workflow.llm_model,
            use_tracking=workflow.track,
            use_reid=workflow.reid,
            tts_enabled=workflow.tts,
            tts_mode=workflow.tts_mode,
        )


@dataclass
class FrameResult:
    """Result of processing a single frame."""
    frame_num: int
    frame_path: Path
    has_target: bool = False
    target_count: int = 0
    confidence: float = 0.0
    description: str = ""
    detections: List[Dict] = field(default_factory=list)
    tracking: Dict[str, Any] = field(default_factory=dict)
    processing_ms: float = 0.0


class NarratorOrchestrator:
    """
    Main orchestrator for narrator pipeline.
    
    Coordinates all components:
    - FrameCapture: Get frames from video source
    - SmartDetector: Detect objects
    - ObjectTracker: Track objects across frames
    - Describer: Generate descriptions (YOLO or LLM)
    - OutputHandler: TTS, logging, HTML reports
    """
    
    def __init__(self, config: NarratorConfig):
        self.config = config
        self._running = False
        self._frame_count = 0
        self._results: List[FrameResult] = []
    
    def run(self, url: str, duration: int = 30) -> List[FrameResult]:
        """Run narrator for specified duration."""
        import time
        from ..smart_detector import SmartDetector
        from ..fast_capture import FastCapture
        
        self.config.url = url
        self._running = True
        
        # Initialize components
        detector = SmartDetector(
            focus=self.config.focus,
            mode=self.config.mode,
        )
        
        capture = FastCapture(url, fps=self.config.fps * 2)
        capture.start()
        
        interval = 1.0 / self.config.fps
        start_time = time.time()
        
        print(f"🎬 Starting narrator (duration={duration}s, fps={self.config.fps})")
        
        try:
            while self._running and (time.time() - start_time) < duration:
                frame_start = time.time()
                self._frame_count += 1
                
                # 1. Capture
                frame_info = capture.get_frame()
                if not frame_info or not frame_info.path.exists():
                    time.sleep(0.1)
                    continue
                
                # 2. Detect
                detection = detector.analyze(
                    frame_path=frame_info.path,
                    prev_frame_path=None,
                )
                
                # 3. Create result
                result = FrameResult(
                    frame_num=self._frame_count,
                    frame_path=frame_info.path,
                    has_target=detection.has_target,
                    confidence=detection.confidence,
                    description=detection.quick_summary or "No target",
                    detections=detection.detections,
                    processing_ms=(time.time() - frame_start) * 1000,
                )
                
                # 4. Output
                if detection.has_target:
                    print(f"  ✅ F{self._frame_count}: {result.description}")
                else:
                    print(f"  ⚪ F{self._frame_count}: {result.description}")
                
                self._results.append(result)
                
                # Sleep for interval
                elapsed = time.time() - frame_start
                if elapsed < interval:
                    time.sleep(interval - elapsed)
        
        finally:
            capture.stop()
            self._running = False
        
        return self._results
    
    def stop(self):
        """Stop the narrator."""
        self._running = False


# Convenience function
def run_narrator(url: str, intent: str = "track person", duration: int = 30):
    """Run narrator with natural language config.
    
    Example:
        run_narrator("rtsp://...", "track person entering", duration=60)
    """
    config = NarratorConfig.from_intent(intent)
    narrator = NarratorOrchestrator(config)
    return narrator.run(url, duration)
