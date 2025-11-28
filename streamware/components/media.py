"""
Media Analysis Component for Streamware

Analyze multimedia content using AI models:
- Video captioning and description
- Audio transcription (STT) and generation (TTS)
- Image description and analysis
- Music analysis and generation

# Menu:
- [Quick Start](#quick-start)
- [Video Analysis](#video-analysis)
- [Audio Processing](#audio-processing)
- [Image Analysis](#image-analysis)
- [Models](#models)
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


@register("media")
@register("analyze")
class MediaComponent(Component):
    """
    Multimedia analysis with AI models
    
    Operations:
    - describe_video: Generate video description
    - describe_image: Generate image description
    - transcribe: Audio to text (STT)
    - speak: Text to speech (TTS)
    - analyze_music: Analyze music properties
    - caption: Generate captions for media
    
    Models:
    - llava: Vision-language model (Ollama)
    - whisper: Speech recognition
    - bark: Text to speech
    - musicgen: Music generation
    
    URI Examples:
        media://describe_video?file=video.mp4&model=llava
        media://transcribe?file=audio.mp3&model=whisper
        media://speak?text=Hello&model=bark
        media://describe_image?file=photo.jpg&model=llava
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    MODELS = {
        "llava": {
            "provider": "ollama",
            "use": ["video", "image"],
            "install_cmd": "ollama pull llava"
        },
        "whisper": {
            "provider": "openai",
            "use": ["audio"],
            "install_cmd": "pip install openai-whisper"
        },
        "bark": {
            "provider": "suno",
            "use": ["tts"],
            "install_cmd": "pip install bark"
        },
        "musicgen": {
            "provider": "facebook",
            "use": ["music"],
            "install_cmd": "pip install audiocraft"
        }
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "describe_video"
        
        self.file = uri.get_param("file")
        self.text = uri.get_param("text")
        self.model = uri.get_param("model", "llava")
        self.prompt = uri.get_param("prompt", "Describe what you see in detail")
        self.language = uri.get_param("language", "en")
        self.output_file = uri.get_param("output")
        
        # Auto-install
        self.auto_install = uri.get_param("auto_install", True)
    
    def process(self, data: Any) -> Dict:
        """Process media analysis"""
        if self.auto_install:
            self._ensure_model()
        
        operations = {
            "describe_video": self._describe_video,
            "describe_image": self._describe_image,
            "transcribe": self._transcribe_audio,
            "speak": self._text_to_speech,
            "analyze_music": self._analyze_music,
            "caption": self._generate_caption,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _ensure_model(self):
        """Ensure model is installed"""
        if self.model not in self.MODELS:
            logger.warning(f"Unknown model: {self.model}")
            return
        
        model_info = self.MODELS[self.model]
        
        # Check if model is available
        if model_info["provider"] == "ollama":
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags")
                if response.ok:
                    models = response.json().get("models", [])
                    if not any(self.model in m.get("name", "") for m in models):
                        logger.info(f"Installing {self.model}...")
                        subprocess.run(["ollama", "pull", self.model], check=True)
            except Exception as e:
                logger.warning(f"Could not check Ollama models: {e}")
    
    def _describe_video(self, data: Any) -> Dict:
        """Generate video description using vision-language model"""
        if not self.file:
            raise ComponentError("Video file required")
        
        video_path = Path(self.file)
        if not video_path.exists():
            raise ComponentError(f"Video file not found: {self.file}")
        
        # Extract key frames
        frames = self._extract_frames(video_path)
        
        # Analyze frames with LLaVA
        descriptions = []
        for frame_path in frames:
            desc = self._analyze_image_with_llava(frame_path, self.prompt)
            descriptions.append(desc)
        
        # Combine descriptions
        combined = self._combine_descriptions(descriptions)
        
        return {
            "success": True,
            "file": str(video_path),
            "model": self.model,
            "description": combined,
            "num_frames": len(frames)
        }
    
    def _describe_image(self, data: Any) -> Dict:
        """Generate image description"""
        if not self.file:
            raise ComponentError("Image file required")
        
        image_path = Path(self.file)
        if not image_path.exists():
            raise ComponentError(f"Image not found: {self.file}")
        
        description = self._analyze_image_with_llava(image_path, self.prompt)
        
        return {
            "success": True,
            "file": str(image_path),
            "model": self.model,
            "description": description
        }
    
    def _transcribe_audio(self, data: Any) -> Dict:
        """Transcribe audio to text (STT)"""
        if not self.file:
            raise ComponentError("Audio file required")
        
        audio_path = Path(self.file)
        if not audio_path.exists():
            raise ComponentError(f"Audio not found: {self.file}")
        
        # Use Whisper for transcription
        try:
            import whisper
            model = whisper.load_model("base")
            result = model.transcribe(str(audio_path), language=self.language)
            
            text = result["text"]
            
            # Save if output specified
            if self.output_file:
                Path(self.output_file).write_text(text)
            
            return {
                "success": True,
                "file": str(audio_path),
                "model": "whisper",
                "text": text,
                "language": result.get("language", self.language)
            }
        except ImportError:
            # Fallback to system whisper if available
            try:
                result = subprocess.run(
                    ["whisper", str(audio_path), "--model", "base"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return {
                    "success": True,
                    "file": str(audio_path),
                    "output": result.stdout
                }
            except FileNotFoundError:
                raise ComponentError("Whisper not installed. Install with: pip install openai-whisper")
    
    def _text_to_speech(self, data: Any) -> Dict:
        """Convert text to speech (TTS)"""
        text = self.text or str(data)
        if not text:
            raise ComponentError("Text required for TTS")
        
        output = self.output_file or "output.wav"
        
        try:
            # Try using bark
            from bark import SAMPLE_RATE, generate_audio, preload_models
            from scipy.io.wavfile import write as write_wav
            
            preload_models()
            audio_array = generate_audio(text)
            write_wav(output, SAMPLE_RATE, audio_array)
            
            return {
                "success": True,
                "text": text,
                "model": "bark",
                "output_file": output
            }
        except ImportError:
            # Fallback to system TTS
            try:
                subprocess.run(
                    ["espeak", "-w", output, text],
                    check=True
                )
                return {
                    "success": True,
                    "text": text,
                    "model": "espeak",
                    "output_file": output
                }
            except FileNotFoundError:
                raise ComponentError("TTS not available. Install bark: pip install bark")
    
    def _analyze_music(self, data: Any) -> Dict:
        """Analyze music properties"""
        if not self.file:
            raise ComponentError("Audio file required")
        
        audio_path = Path(self.file)
        if not audio_path.exists():
            raise ComponentError(f"Audio not found: {self.file}")
        
        try:
            import librosa
            
            # Load audio
            y, sr = librosa.load(str(audio_path))
            
            # Analyze
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            
            return {
                "success": True,
                "file": str(audio_path),
                "tempo": float(tempo),
                "duration": len(y) / sr,
                "sample_rate": sr,
                "analysis": "Music analysis complete"
            }
        except ImportError:
            raise ComponentError("librosa not installed. Install with: pip install librosa")
    
    def _generate_caption(self, data: Any) -> Dict:
        """Generate caption for media"""
        if not self.file:
            raise ComponentError("Media file required")
        
        file_path = Path(self.file)
        suffix = file_path.suffix.lower()
        
        if suffix in [".jpg", ".jpeg", ".png", ".gif", ".bmp"]:
            return self._describe_image(data)
        elif suffix in [".mp4", ".avi", ".mov", ".mkv"]:
            return self._describe_video(data)
        elif suffix in [".mp3", ".wav", ".ogg", ".flac"]:
            return self._transcribe_audio(data)
        else:
            raise ComponentError(f"Unsupported file type: {suffix}")
    
    # Helper methods
    def _extract_frames(self, video_path: Path, num_frames: int = 5) -> list:
        """Extract key frames from video"""
        frames_dir = Path(tempfile.mkdtemp())
        
        try:
            # Use ffmpeg to extract frames
            subprocess.run([
                "ffmpeg",
                "-i", str(video_path),
                "-vf", f"select='not(mod(n\\,{num_frames}))'",
                "-vsync", "0",
                "-frames:v", str(num_frames),
                str(frames_dir / "frame_%03d.jpg")
            ], check=True, capture_output=True)
            
            return sorted(frames_dir.glob("*.jpg"))
        except FileNotFoundError:
            raise ComponentError("ffmpeg not installed")
        except subprocess.CalledProcessError:
            # Fallback: just use first frame
            subprocess.run([
                "ffmpeg",
                "-i", str(video_path),
                "-vframes", "1",
                str(frames_dir / "frame_001.jpg")
            ], check=True, capture_output=True)
            
            return list(frames_dir.glob("*.jpg"))
    
    def _analyze_image_with_llava(self, image_path: Path, prompt: str) -> str:
        """Analyze image using LLaVA"""
        try:
            import requests
            import base64
            
            # Read image and encode
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # Call LLaVA via Ollama
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llava",
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                }
            )
            
            if response.ok:
                return response.json().get("response", "")
            else:
                return f"Error analyzing image: {response.status_code}"
                
        except Exception as e:
            return f"Could not analyze image: {e}"
    
    def _combine_descriptions(self, descriptions: list) -> str:
        """Combine multiple descriptions into coherent narrative"""
        if not descriptions:
            return "No description available"
        
        if len(descriptions) == 1:
            return descriptions[0]
        
        # Use LLM to combine descriptions
        try:
            import requests
            
            combined_text = "\n\n".join([f"Frame {i+1}: {desc}" for i, desc in enumerate(descriptions)])
            prompt = f"Based on these frame descriptions, write a single coherent video description:\n\n{combined_text}"
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.ok:
                return response.json().get("response", combined_text)
            else:
                return combined_text
                
        except Exception:
            return " ".join(descriptions)


# Quick helpers
def describe_video(file: str, model: str = "llava") -> Dict:
    """Quick video description"""
    from ..core import flow
    uri = f"media://describe_video?file={file}&model={model}"
    return flow(uri).run()


def transcribe(file: str) -> str:
    """Quick audio transcription"""
    from ..core import flow
    result = flow(f"media://transcribe?file={file}").run()
    return result.get("text", "")


def speak(text: str, output: str = "output.wav") -> str:
    """Quick text to speech"""
    from ..core import flow
    result = flow(f"media://speak?text={text}&output={output}").run()
    return result.get("output_file", "")
