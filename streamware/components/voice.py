"""
Voice Component for Streamware

Speech-to-Text (STT) and Text-to-Speech (TTS) for voice commands.
Control sq with voice and hear responses!

# Menu:
- [Quick Start](#quick-start)
- [Voice Commands](#voice-commands)
- [TTS Output](#tts-output)
- [Examples](#examples)
"""

from __future__ import annotations
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("voice")
@register("speech")
class VoiceComponent(Component):
    """
    Voice input/output component
    
    Operations:
    - listen: Listen for voice command (STT)
    - speak: Speak text (TTS)
    - command: Listen and execute sq command
    - interactive: Interactive voice mode
    
    Engines:
    - whisper: OpenAI Whisper (STT)
    - pyttsx3: Cross-platform TTS
    - espeak: Linux TTS
    - say: macOS TTS
    
    URI Examples:
        voice://listen
        voice://speak?text=Hello World
        voice://command
        voice://interactive
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "listen"
        
        # Configuration from .env
        from ..config import config
        self.stt_provider = config.get("SQ_STT_PROVIDER", "google")
        self.whisper_model = config.get("SQ_WHISPER_MODEL", "base")
        default_tts_engine = config.get("SQ_TTS_ENGINE", "auto")
        default_tts_voice = config.get("SQ_TTS_VOICE", "")
        default_tts_rate = config.get("SQ_TTS_RATE", "150")

        # URI parameters (override config where applicable)
        self.text = uri.get_param("text")
        self.language = uri.get_param("language", "en")
        self.voice = uri.get_param("voice", default_tts_voice)
        self.output_file = uri.get_param("output")
        self.engine = uri.get_param("engine", default_tts_engine)
        try:
            self.tts_rate = int(uri.get_param("rate", default_tts_rate))
        except (TypeError, ValueError):
            self.tts_rate = 150
        
        # Override if specified in URI
        if uri.get_param("provider"):
            self.stt_provider = uri.get_param("provider")
        
        # Auto-install
        self.auto_install = uri.get_param("auto_install", True)
    
    def process(self, data: Any) -> Dict:
        """Process voice operation"""
        if self.auto_install:
            self._ensure_dependencies()
        
        operations = {
            "listen": self._listen,
            "speak": self._speak,
            "command": self._voice_command,
            "interactive": self._interactive,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _ensure_dependencies(self):
        """Ensure voice dependencies are installed"""
        # Check for STT basics
        try:
            import speech_recognition
        except ImportError:
            logger.info("Installing SpeechRecognition...")
            subprocess.run(["pip", "install", "SpeechRecognition"], check=True, capture_output=True)
            
        # Check for PyAudio (needed for microphone)
        try:
            import pyaudio
        except ImportError:
            logger.info("Installing PyAudio...")
            try:
                subprocess.run(["pip", "install", "PyAudio"], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                logger.warning("Failed to install PyAudio. Please install portaudio19-dev first.")

        # Check for Whisper if selected
        if self.stt_provider == "whisper_local":
            try:
                import whisper
            except ImportError:
                logger.info("Installing openai-whisper...")
                subprocess.run(["pip", "install", "openai-whisper"], check=True, capture_output=True)
                
            try:
                import sounddevice
            except ImportError:
                logger.info("Installing sounddevice...")
                subprocess.run(["pip", "install", "sounddevice", "scipy"], check=True, capture_output=True)

        # Check for TTS
        try:
            import pyttsx3
        except ImportError:
            logger.info("Installing pyttsx3...")
            subprocess.run(["pip", "install", "pyttsx3"], check=True, capture_output=True)
    
    def _listen(self, data: Any) -> Dict:
        """Listen for voice input (STT)"""
        # Dispatch based on provider
        if self.stt_provider == "whisper_local":
            return self._listen_whisper(data)
        elif self.stt_provider == "whisper_api":
            return self._listen_whisper_api(data)
        else:
            return self._listen_google(data)

    def _listen_whisper(self, data: Any) -> Dict:
        """Listen using local Whisper model"""
        try:
            import whisper
            import sounddevice as sd
            import numpy as np
            import scipy.io.wavfile as wav
            
            logger.info(f"Loading Whisper model: {self.whisper_model}...")
            print(f"🧠 Loading Whisper ({self.whisper_model})...")
            model = whisper.load_model(self.whisper_model)
            
            # Record audio
            fs = 44100  # Sample rate
            duration = 5  # seconds (simple fixed duration for now, or dynamic silence detection)
            
            logger.info("Listening (Whisper)...")
            print("🎤 Listening (5s)...")
            
            # Record
            recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
            sd.wait()
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                temp_filename = tf.name
                
            # Convert to int16 for wav
            data_int = (recording * 32767).astype(np.int16)
            wav.write(temp_filename, fs, data_int)
            
            logger.info("Transcribing...")
            print("📝 Transcribing...")
            
            # Transcribe
            result = model.transcribe(temp_filename)
            text = result["text"].strip()
            
            # Cleanup
            os.remove(temp_filename)
            
            logger.info(f"Recognized: {text}")
            return {
                "success": True,
                "text": text,
                "language": result.get("language", "unknown"),
                "provider": "whisper_local"
            }
            
        except ImportError:
            raise ComponentError("Whisper dependencies missing. Run setup or install openai-whisper sounddevice scipy")
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _listen_whisper_api(self, data: Any) -> Dict:
        """Listen using OpenAI Whisper API"""
        # Placeholder for API implementation (requires capturing audio then sending to API)
        # For now fallback to Google or implement later
        return self._listen_google(data)

    def _listen_google(self, data: Any) -> Dict:
        """Listen using Google Web Speech (Standard)"""
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            
            # Listen from microphone
            with sr.Microphone() as source:
                logger.info("Listening... Speak now!")
                print("🎤 Listening... Speak now!")
                
                # Adjust for ambient noise
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                # Listen
                audio = recognizer.listen(source, timeout=10)
            
            logger.info("Processing speech...")
            print("🔄 Processing...")
            
            # Recognize speech
            try:
                text = recognizer.recognize_google(audio, language=self.language)
                logger.info(f"Recognized: {text}")
                
                return {
                    "success": True,
                    "text": text,
                    "language": self.language,
                    "provider": "google"
                }
            except sr.UnknownValueError:
                return {
                    "success": False,
                    "error": "Could not understand audio"
                }
            except sr.RequestError as e:
                return {
                    "success": False,
                    "error": f"API error: {e}"
                }
                
        except ImportError:
            raise ComponentError("speech_recognition not installed. Install: pip install SpeechRecognition PyAudio")
    
    def _speak(self, data: Any) -> Dict:
        """Speak text (TTS)"""
        # Prefer explicit text param; fallback to data only if text not provided
        text = self.text if self.text else (str(data) if data else None)
        if not text or not text.strip():
            raise ComponentError("Text required for TTS")
        
        logger.info(f"Speaking: {text}")
        
        # Try different TTS engines
        success = False
        engine_used = None
        preferred_engine = (self.engine or "auto").lower()
        
        # Try pyttsx3 (cross-platform)
        if preferred_engine in ("auto", "pyttsx3"):
            try:
                import pyttsx3
                engine = pyttsx3.init()

                # Apply configured rate if possible
                try:
                    if getattr(self, "tts_rate", None):
                        engine.setProperty('rate', int(self.tts_rate))
                except Exception as rate_err:
                    logger.debug(f"Failed to set TTS rate: {rate_err}")
                
                if self.voice:
                    voices = engine.getProperty('voices')
                    for voice in voices:
                        if self.voice.lower() in getattr(voice, 'name', '').lower():
                            engine.setProperty('voice', voice.id)
                            break
                
                engine.say(text)
                engine.runAndWait()
                success = True
                engine_used = "pyttsx3"
            except Exception as e:
                logger.debug(f"pyttsx3 failed: {e}")
        
        # Try system commands
        if not success:
            import platform
            system = platform.system()
            
            try:
                # macOS 'say'
                if preferred_engine in ("say",) or (preferred_engine == "auto" and system == "Darwin"):
                    subprocess.run(["say", text], check=True)
                    engine_used = "say"
                    success = True
                # Linux 'espeak'
                elif preferred_engine in ("espeak",) or (preferred_engine == "auto" and system == "Linux"):
                    subprocess.run(["espeak", text], check=True)
                    engine_used = "espeak"
                    success = True
                # Windows PowerShell TTS
                elif preferred_engine in ("powershell",) or (preferred_engine == "auto" and system == "Windows"):
                    subprocess.run(["powershell", "-Command", f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"], check=True)
                    engine_used = "powershell"
                    success = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        
        if success:
            return {
                "success": True,
                "text": text,
                "engine": engine_used
            }
        else:
            raise ComponentError("No TTS engine available. Install: pip install pyttsx3")
    
    def _voice_command(self, data: Any) -> Dict:
        """Listen for voice command and execute"""
        # Listen
        listen_result = self._listen(data)
        
        if not listen_result.get("success"):
            self._speak({"text": "Sorry, I didn't understand that"})
            return listen_result
        
        command_text = listen_result.get("text", "")
        print(f"🎯 Command: {command_text}")
        
        # Convert to sq command using LLM
        try:
            from ..core import flow
            
            # Generate sq command
            result = flow(f"text2sq://convert?prompt={command_text}").run()
            sq_command = result if isinstance(result, str) else str(result)
            
            print(f"💻 Generated: {sq_command}")
            
            # Confirm
            self._speak({"text": f"Executing: {sq_command}"})
            
            # Execute
            output = subprocess.run(
                sq_command,
                shell=True,
                capture_output=True,
                text=True
            )
            
            # Speak result
            if output.returncode == 0:
                self._speak({"text": "Command completed successfully"})
                result_text = output.stdout[:200]  # First 200 chars
                if result_text:
                    self._speak({"text": result_text})
            else:
                self._speak({"text": "Command failed"})
            
            return {
                "success": True,
                "voice_input": command_text,
                "sq_command": sq_command,
                "output": output.stdout,
                "returncode": output.returncode
            }
            
        except Exception as e:
            self._speak({"text": f"Error: {str(e)}"})
            return {
                "success": False,
                "error": str(e)
            }
    
    def _interactive(self, data: Any) -> Dict:
        """Interactive voice mode"""
        print("🎤 Interactive Voice Mode")
        print("Say 'exit' or 'quit' to stop")
        
        self._speak({"text": "Voice mode activated. Say your command."})
        
        commands_executed = []
        
        while True:
            # Listen
            result = self._voice_command(data)
            
            if result.get("success"):
                voice_input = result.get("voice_input", "").lower()
                
                # Check for exit
                if any(word in voice_input for word in ["exit", "quit", "stop", "goodbye"]):
                    self._speak({"text": "Goodbye!"})
                    break
                
                commands_executed.append(result)
            else:
                # Try again
                continue
        
        return {
            "success": True,
            "commands_executed": len(commands_executed),
            "commands": commands_executed
        }


# Quick helpers
def listen() -> str:
    """Quick voice listen"""
    from ..core import flow
    result = flow("voice://listen").run()
    return result.get("text", "")


def speak(text: str) -> Dict:
    """Quick text to speech"""
    from ..core import flow
    return flow(f"voice://speak?text={text}").run()


def voice_command() -> Dict:
    """Quick voice command"""
    from ..core import flow
    return flow("voice://command").run()
