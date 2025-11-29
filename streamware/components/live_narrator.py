"""
Live Narrator Component - Real-time stream description with TTS

Features:
1. Continuous stream analysis with AI
2. Text-to-speech output for descriptions
3. Configurable triggers ("alert when person appears")
4. Diff-based change detection before AI analysis
5. History tracking of descriptions

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
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import base64
import json
from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError

logger = logging.getLogger(__name__)


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
        
        # TTS settings
        self.tts_enabled = uri.get_param("tts", "false").lower() in ("true", "1", "yes")
        self.tts_engine = uri.get_param("tts_engine", "espeak")  # espeak, pico, festival
        self.tts_rate = int(uri.get_param("tts_rate", "150"))  # Words per minute
        
        # Analysis settings
        self.interval = float(uri.get_param("interval", "3"))
        self.duration = int(uri.get_param("duration", "60"))
        self.model = uri.get_param("model", "llava:13b")
        self.focus = uri.get_param("focus", "")
        
        # Diff settings (skip AI if no change)
        self.use_diff = uri.get_param("diff", "true").lower() in ("true", "1", "yes")
        self.diff_threshold = int(uri.get_param("threshold", "15"))
        self.min_change = float(uri.get_param("min_change", "0.5"))
        
        # Triggers
        trigger_str = uri.get_param("trigger", "")
        self.triggers = self._parse_triggers(trigger_str)
        self.webhook_url = uri.get_param("webhook_url", "")
        
        # Language
        self.language = uri.get_param("lang", "en")
        
        # State
        self._temp_dir = None
        self._prev_frame = None
        self._history: List[NarrationEntry] = []
        self._running = False
        self._tts_queue = []
        self._last_description = ""
    
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
        """Run continuous narration with TTS"""
        print(f"\n🎙️ Live Narrator Started")
        print(f"   Source: {self.source[:50]}...")
        print(f"   TTS: {'ON' if self.tts_enabled else 'OFF'}")
        print(f"   Triggers: {len(self.triggers)}")
        print(f"   Interval: {self.interval}s")
        print()
        
        start_time = time.time()
        frame_num = 0
        
        while time.time() - start_time < self.duration and self._running:
            frame_num += 1
            frame_path = self._capture_frame(frame_num)
            
            if not frame_path or not frame_path.exists():
                time.sleep(self.interval)
                continue
            
            # Check if there's a significant change
            has_change = True
            if self.use_diff and self._prev_frame:
                change_pct = self._compute_change(frame_path)
                has_change = change_pct >= self.min_change
                if not has_change:
                    print(f"   Frame {frame_num}: No significant change ({change_pct:.1f}%)")
            
            if has_change:
                # Get AI description
                description = self._describe_frame(frame_path)
                
                # Check for duplicates
                if description and description != self._last_description:
                    self._last_description = description
                    
                    # Check triggers
                    triggered, matches = self._check_triggers(description)
                    
                    # Create entry
                    entry = NarrationEntry(
                        timestamp=datetime.now(),
                        frame_num=frame_num,
                        description=description,
                        triggered=triggered,
                        trigger_matches=matches
                    )
                    self._history.append(entry)
                    
                    # Output
                    ts = entry.timestamp.strftime("%H:%M:%S")
                    if triggered:
                        print(f"🔴 [{ts}] TRIGGER: {', '.join(matches)}")
                        print(f"   {description[:200]}...")
                        
                        # Speak alert
                        if self.tts_enabled:
                            alert_text = f"Alert! {matches[0]}"
                            self._speak(alert_text)
                        
                        # Webhook
                        if self.webhook_url:
                            self._send_webhook(entry)
                    else:
                        print(f"📝 [{ts}] {description[:150]}...")
                        
                        # Speak description
                        if self.tts_enabled:
                            self._speak(description[:200])
            
            self._prev_frame = frame_path
            time.sleep(self.interval)
        
        # Summary
        triggered_count = sum(1 for e in self._history if e.triggered)
        
        return {
            "success": True,
            "operation": "narrator",
            "source": self.source,
            "tts_enabled": self.tts_enabled,
            "duration": self.duration,
            "frames_analyzed": frame_num,
            "descriptions": len(self._history),
            "triggers_fired": triggered_count,
            "history": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "frame": e.frame_num,
                    "description": e.description,
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
            import numpy as np
            
            img1 = Image.open(self._prev_frame).convert('L')
            img2 = Image.open(current_frame).convert('L')
            
            if img1.size != img2.size:
                img2 = img2.resize(img1.size)
            
            diff = ImageChops.difference(img1, img2)
            diff_array = np.array(diff)
            diff_binary = (diff_array > self.diff_threshold).astype(np.uint8)
            
            change_pct = (np.sum(diff_binary) / diff_binary.size) * 100
            return change_pct
            
        except Exception as e:
            logger.warning(f"Change computation failed: {e}")
            return 100  # Assume change on error
    
    def _describe_frame(self, frame_path: Path) -> str:
        """Get AI description of frame"""
        try:
            import requests
            
            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            focus_text = f"Focus on: {self.focus}. " if self.focus else ""
            
            prompt = f"""{focus_text}Describe what you see in this image concisely.
Include:
- People present and what they're doing
- Objects and their positions
- Any movement or activity
- Anything unusual or notable

Be specific and brief (2-3 sentences max)."""

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=30
            )
            
            if response.ok:
                return response.json().get("response", "").strip()
            return ""
            
        except Exception as e:
            logger.warning(f"Description failed: {e}")
            return ""
    
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
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=30
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
