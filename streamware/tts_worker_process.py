"""TTS worker process

Separate process for Text-to-Speech so that speaking never blocks
LiveNarrator or DSL / LLM processing.

Architecture:
    [Main process]
        └─ TTSWorkerProcess.speak(text)  →  multiprocessing.Queue
                                           ↓
    [TTS process]
        └─ reads queue, calls streamware.tts.speak(block=True)

Usage:
    from streamware.tts_worker_process import get_tts_worker, stop_tts_worker

    worker = get_tts_worker(engine="auto", rate=150, voice="")
    worker.speak("Person detected in the frame")

    # On shutdown
    stop_tts_worker()
"""

import logging
import multiprocessing as mp
import signal
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class TTSWorkerConfig:
    """Configuration for TTS worker process."""

    engine: str = "auto"
    rate: int = 150
    voice: str = ""


def _run_tts_worker(queue: mp.Queue, stop_event: mp.Event, config: TTSWorkerConfig):
    """Run TTS worker loop in separate process.

    Reads text messages from queue and calls streamware.tts.speak in a
    blocking way inside this worker process.
    """

    # Ignore SIGINT in child process (parent handles shutdown)
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        from .tts import speak
    except Exception as e:  # pragma: no cover - defensive
        print(f"❌ TTS worker init failed: cannot import tts.speak: {e}", flush=True)
        return

    voice_info = f", voice={config.voice}" if config.voice else ""
    print(
        f"🔊 TTS Worker started (PID={mp.current_process().pid}, engine={config.engine}{voice_info})",
        flush=True,
    )

    try:
        while not stop_event.is_set():
            try:
                item = queue.get(timeout=0.5)
            except Exception:
                # Timeout / empty queue
                continue

            if item is None:
                # Sentinel value for graceful shutdown
                break

            try:
                if isinstance(item, dict):
                    text = item.get("text", "")
                    # Per-message voice override (for language support)
                    msg_voice = item.get("voice", config.voice)
                else:
                    text = str(item)
                    msg_voice = config.voice
            except Exception:
                text = str(item)
                msg_voice = config.voice

            if not text:
                continue

            try:
                # Blocking speak inside worker is OK - it does not block narrator
                speak(
                    text,
                    engine=config.engine or None,
                    rate=config.rate or None,
                    voice=msg_voice or None,
                    block=True,
                )
            except Exception as e:
                print(f"❌ TTS speak failed: {e}", flush=True)
                time.sleep(0.1)

    except Exception as e:  # pragma: no cover - best effort
        logger.debug(f"TTS worker loop error: {e}")

    print("🔌 TTS Worker stopped", flush=True)


class TTSWorkerProcess:
    """Manager for background TTS worker process."""

    def __init__(self, engine: str = "auto", rate: int = 150, voice: str = ""):
        self.config = TTSWorkerConfig(engine=engine or "auto", rate=rate, voice=voice or "")
        self._queue: Optional[mp.Queue] = None
        self._stop_event: Optional[mp.Event] = None
        self._process: Optional[mp.Process] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start TTS worker process if not already running."""

        if self._process is not None and self._process.is_alive():
            return

        self._queue = mp.Queue()
        self._stop_event = mp.Event()
        self._process = mp.Process(
            target=_run_tts_worker,
            args=(self._queue, self._stop_event, self.config),
            daemon=True,
        )
        self._process.start()
        # short delay to avoid race on first message
        time.sleep(0.1)

    def stop(self, timeout: float = 2.0) -> None:
        """Stop TTS worker process gracefully."""

        if self._stop_event is not None:
            self._stop_event.set()

        if self._queue is not None:
            try:
                # Sentinel to unblock queue.get
                self._queue.put_nowait(None)
            except Exception:
                pass

        if self._process is not None:
            self._process.join(timeout=timeout)
            if self._process.is_alive():
                self._process.terminate()
            self._process = None

        if self._queue is not None:
            try:
                self._queue.close()
            except Exception:
                pass
            self._queue = None

        self._stop_event = None

    # ------------------------------------------------------------------
    # API
    # ------------------------------------------------------------------
    def speak(self, text: str, voice: str = "") -> None:
        """Enqueue text to be spoken by worker process.
        
        Args:
            text: Text to speak
            voice: Optional voice/language override (e.g. 'pl', 'de')
        """

        if not text:
            return

        if self._process is None or not self._process.is_alive():
            self.start()

        if self._queue is not None:
            try:
                msg = {"text": text}
                if voice:
                    msg["voice"] = voice
                self._queue.put_nowait(msg)
            except Exception as e:
                logger.debug(f"Failed to enqueue TTS text: {e}")

    def is_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()


# Global singleton worker
_worker: Optional[TTSWorkerProcess] = None


def get_tts_worker(engine: str = "auto", rate: int = 150, voice: str = "", lang: str = "en") -> TTSWorkerProcess:
    """Get global TTS worker instance, starting it if needed.
    
    Args:
        engine: TTS engine (auto, espeak, pyttsx3, etc.)
        rate: Speech rate
        voice: Voice name (if not set, will use lang)
        lang: Language code (en, pl, de) - sets voice if voice is empty
    """
    global _worker

    # Map language to voice if voice not specified
    if not voice and lang and lang != "en":
        # For espeak, voice is the language code
        voice = lang
    
    if _worker is None:
        _worker = TTSWorkerProcess(engine=engine, rate=rate, voice=voice)
        _worker.start()
    else:
        # Update config if changed (next process restart would pick it up)
        _worker.config.engine = engine or _worker.config.engine
        _worker.config.rate = rate or _worker.config.rate
        _worker.config.voice = voice or _worker.config.voice

        if not _worker.is_alive():
            _worker.start()

    return _worker


def stop_tts_worker(timeout: float = 2.0) -> None:
    """Stop global TTS worker if running."""
    global _worker

    if _worker is not None:
        try:
            _worker.stop(timeout=timeout)
        except Exception as e:
            logger.debug(f"Error stopping TTS worker: {e}")
        _worker = None
