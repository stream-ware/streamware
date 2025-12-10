"""
Unified Text-to-Speech Module for Streamware

Provides cross-platform TTS with automatic fallback:
- pyttsx3 (cross-platform, Python)
- espeak (Linux, lightweight)
- pico2wave (Linux, better quality)
- festival (Linux, full-featured)
- say (macOS)
- powershell (Windows)

Usage:
    from streamware.tts import speak, TTSEngine, get_available_engines

    # Quick usage
    speak("Hello world")

    # With options
    speak("Hello", engine="espeak", rate=150)

    # Check available engines
    engines = get_available_engines()
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import List, Optional

from .config import config

logger = logging.getLogger(__name__)


class TTSEngine(str, Enum):
    AUTO = "auto"
    PYTTSX3 = "pyttsx3"
    ESPEAK = "espeak"
    PICO = "pico"
    FESTIVAL = "festival"
    SAY = "say"  # macOS
    POWERSHELL = "powershell"  # Windows


@dataclass
class TTSConfig:
    """TTS configuration."""
    engine: TTSEngine = TTSEngine.AUTO
    voice: str = ""
    rate: int = 150
    
    @classmethod
    def from_env(cls) -> "TTSConfig":
        """Load from environment/.env"""
        engine_str = config.get("SQ_TTS_ENGINE", "auto").lower()
        try:
            engine = TTSEngine(engine_str)
        except ValueError:
            engine = TTSEngine.AUTO
        
        return cls(
            engine=engine,
            voice=config.get("SQ_TTS_VOICE", ""),
            rate=int(config.get("SQ_TTS_RATE", "150")),
        )


class TTSManager:
    """Unified TTS manager with automatic fallback."""
    
    _instance: Optional["TTSManager"] = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.config = TTSConfig.from_env()
        self._available_engines: Optional[List[TTSEngine]] = None
        self._pyttsx3_engine = None
        self._initialized = True
    
    def speak(
        self,
        text: str,
        engine: Optional[TTSEngine] = None,
        rate: Optional[int] = None,
        voice: Optional[str] = None,
        block: bool = False,
    ) -> bool:
        """Speak text using TTS.
        
        Args:
            text: Text to speak
            engine: Override engine (optional)
            rate: Override speech rate (optional)
            voice: Override voice (optional)
            block: Wait for speech to complete
            
        Returns:
            True if successful, False otherwise
        """
        # Clean text
        text = self._clean_text(text)
        if not text:
            return False
        
        engine = engine or self.config.engine
        rate = rate or self.config.rate
        voice = voice or self.config.voice
        
        # Determine engine order - always include fallbacks
        if engine == TTSEngine.AUTO:
            engines_to_try = self._get_engine_priority()
        else:
            # Try specified engine first, then fallback to others
            engines_to_try = [engine] + [e for e in self._get_engine_priority() if e != engine]
        
        # Try each engine
        for eng in engines_to_try:
            try:
                success = self._speak_with_engine(eng, text, rate, voice, block)
                if success:
                    return True
            except Exception as e:
                logger.debug(f"TTS engine {eng.value} failed: {e}")
                continue
        
        logger.warning("No TTS engine available. Run: sq check tts")
        return False
    
    def _clean_text(self, text: str) -> str:
        """Clean text for TTS."""
        if not text:
            return ""
        text = text.replace('"', '').replace("'", "").replace('`', '')
        text = ' '.join(text.split())
        return text[:500]  # Limit length
    
    def _get_engine_priority(self) -> List[TTSEngine]:
        """Get engines to try in priority order."""
        import platform
        system = platform.system().lower()
        
        if system == "darwin":
            return [TTSEngine.SAY, TTSEngine.PYTTSX3]
        elif system == "windows":
            return [TTSEngine.PYTTSX3, TTSEngine.POWERSHELL]
        else:  # Linux - espeak first (truly non-blocking with Popen)
            return [TTSEngine.ESPEAK, TTSEngine.PYTTSX3, TTSEngine.PICO, TTSEngine.FESTIVAL]
    
    def _speak_with_engine(
        self,
        engine: TTSEngine,
        text: str,
        rate: int,
        voice: str,
        block: bool,
    ) -> bool:
        """Speak using specific engine."""
        
        if engine == TTSEngine.PYTTSX3:
            return self._speak_pyttsx3(text, rate, voice, block)
        elif engine == TTSEngine.ESPEAK:
            return self._speak_espeak(text, rate, voice, block)
        elif engine == TTSEngine.PICO:
            return self._speak_pico(text, rate, block)
        elif engine == TTSEngine.FESTIVAL:
            return self._speak_festival(text, block)
        elif engine == TTSEngine.SAY:
            return self._speak_say(text, rate, voice, block)
        elif engine == TTSEngine.POWERSHELL:
            return self._speak_powershell(text, block)
        
        return False
    
    def _speak_pyttsx3(self, text: str, rate: int, voice: str, block: bool) -> bool:
        """Speak using pyttsx3."""
        import threading
        
        def _do_speak():
            try:
                import pyttsx3
                
                # Create new engine for thread safety
                engine = pyttsx3.init()
                engine.setProperty('rate', rate)
                
                if voice:
                    voices = engine.getProperty('voices')
                    for v in voices:
                        if voice.lower() in v.name.lower():
                            engine.setProperty('voice', v.id)
                            break
                
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception as e:
                logger.debug(f"pyttsx3 thread failed: {e}")
        
        if block:
            _do_speak()
        else:
            # Run in thread for non-blocking
            # NOT daemon - we want TTS to complete even if main thread exits
            t = threading.Thread(target=_do_speak, daemon=False)
            t.start()
            # Store reference to join later if needed
            if not hasattr(self, '_tts_threads'):
                self._tts_threads = []
            self._tts_threads.append(t)
        
        return True
    
    def wait_for_tts(self, timeout: float = 10.0):
        """Wait for all pending TTS to complete."""
        if hasattr(self, '_tts_threads'):
            for t in self._tts_threads:
                if t.is_alive():
                    t.join(timeout=timeout)
            self._tts_threads = []
    
    def _speak_espeak(self, text: str, rate: int, voice: str, block: bool) -> bool:
        """Speak using espeak."""
        cmd = ["espeak", "-s", str(rate)]
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text)
        
        if block:
            result = subprocess.run(cmd, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
            return result.returncode == 0
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            return True
    
    def _speak_pico(self, text: str, rate: int, block: bool) -> bool:
        """Speak using pico2wave."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name
        
        result = subprocess.run(
            ["pico2wave", "-w", wav_path, text],
            capture_output=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return False
        
        if block:
            subprocess.run(["aplay", wav_path], capture_output=True, timeout=30)
        else:
            subprocess.Popen(["aplay", wav_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Cleanup is handled by OS eventually
        return True
    
    def _speak_festival(self, text: str, block: bool) -> bool:
        """Speak using festival."""
        if block:
            result = subprocess.run(
                ["festival", "--tts"],
                input=text.encode(),
                capture_output=True,
                timeout=30
            )
            return result.returncode == 0
        else:
            proc = subprocess.Popen(
                ["festival", "--tts"],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            proc.stdin.write(text.encode())
            proc.stdin.close()
            return True
    
    def _speak_say(self, text: str, rate: int, voice: str, block: bool) -> bool:
        """Speak using macOS say."""
        cmd = ["say"]
        if rate:
            cmd.extend(["-r", str(rate)])
        if voice:
            cmd.extend(["-v", voice])
        cmd.append(text)
        
        if block:
            result = subprocess.run(cmd, capture_output=True, timeout=30)
            return result.returncode == 0
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    
    def _speak_powershell(self, text: str, block: bool) -> bool:
        """Speak using Windows PowerShell."""
        script = f'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{text}")'
        cmd = ["powershell", "-Command", script]
        
        if block:
            result = subprocess.run(cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        else:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
    
    def get_available_engines(self) -> List[TTSEngine]:
        """Check which TTS engines are available."""
        if self._available_engines is not None:
            return self._available_engines
        
        available = []
        
        # Check pyttsx3
        try:
            import pyttsx3
            pyttsx3.init()
            available.append(TTSEngine.PYTTSX3)
        except Exception:
            pass
        
        # Check espeak
        try:
            result = subprocess.run(["espeak", "--version"], capture_output=True, timeout=2)
            if result.returncode == 0:
                available.append(TTSEngine.ESPEAK)
        except Exception:
            pass
        
        # Check pico
        try:
            result = subprocess.run(["pico2wave", "--help"], capture_output=True, timeout=2)
            available.append(TTSEngine.PICO)
        except Exception:
            pass
        
        # Check festival
        try:
            result = subprocess.run(["festival", "--version"], capture_output=True, timeout=2)
            available.append(TTSEngine.FESTIVAL)
        except Exception:
            pass
        
        # Check say (macOS)
        try:
            result = subprocess.run(["say", "-v", "?"], capture_output=True, timeout=2)
            if result.returncode == 0:
                available.append(TTSEngine.SAY)
        except Exception:
            pass
        
        self._available_engines = available
        return available


# Convenience functions

_manager: Optional[TTSManager] = None


def get_manager() -> TTSManager:
    """Get singleton TTS manager."""
    global _manager
    if _manager is None:
        _manager = TTSManager()
    return _manager


def speak(
    text: str,
    engine: Optional[str] = None,
    rate: Optional[int] = None,
    voice: Optional[str] = None,
    block: bool = False,
) -> bool:
    """Speak text using TTS.
    
    Args:
        text: Text to speak
        engine: Engine name (auto, espeak, pyttsx3, pico, festival, say)
        rate: Speech rate (words per minute)
        voice: Voice name/language
        block: Wait for speech to complete
        
    Returns:
        True if successful
    """
    manager = get_manager()
    eng = None
    if engine:
        try:
            eng = TTSEngine(engine.lower())
        except ValueError:
            pass
    return manager.speak(text, engine=eng, rate=rate, voice=voice, block=block)


def get_available_engines() -> List[str]:
    """Get list of available TTS engine names."""
    manager = get_manager()
    return [e.value for e in manager.get_available_engines()]


def wait_for_tts(timeout: float = 10.0):
    """Wait for all pending TTS to complete."""
    manager = get_manager()
    manager.wait_for_tts(timeout)


def test_tts() -> dict:
    """Test TTS and return status."""
    manager = get_manager()
    available = manager.get_available_engines()
    
    result = {
        "available_engines": [e.value for e in available],
        "configured_engine": manager.config.engine.value,
        "test_result": "not_run",
    }
    
    if available:
        success = manager.speak("TTS test", block=True)
        result["test_result"] = "success" if success else "failed"
    else:
        result["test_result"] = "no_engines"
    
    return result
