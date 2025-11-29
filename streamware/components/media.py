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
from ..config import config

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
        
        # Video analysis mode: full, stream, diff
        self.mode = uri.get_param("mode", "full")
        
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
                ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
                response = requests.get(f"{ollama_url}/api/tags")
                if response.ok:
                    models = response.json().get("models", [])
                    if not any(self.model in m.get("name", "") for m in models):
                        logger.info(f"Installing {self.model}...")
                        subprocess.run(["ollama", "pull", self.model], check=True)
            except Exception as e:
                logger.warning(f"Could not check Ollama models: {e}")
    
    def _describe_video(self, data: Any) -> Dict:
        """Generate video description with multiple analysis modes.
        
        Modes:
            - full: Coherent narrative with scene tracking (default)
            - stream: Frame-by-frame detailed descriptions
            - diff: Differences between consecutive frames
        """
        if not self.file:
            raise ComponentError("Video file required")
        
        video_path = Path(self.file)
        if not video_path.exists():
            raise ComponentError(f"Video file not found: {self.file}")
        
        # Get video info
        video_info = self._get_video_info(video_path)
        
        # Extract frames based on mode
        if self.mode == "stream":
            # More frames for detailed analysis
            frames = self._extract_frames_smart(video_path, video_info, max_frames=20)
        else:
            frames = self._extract_frames_smart(video_path, video_info)
        
        # Route to appropriate analysis mode
        if self.mode == "stream":
            return self._analyze_stream_mode(frames, video_info, video_path)
        elif self.mode == "diff":
            return self._analyze_diff_mode(frames, video_info, video_path)
        else:  # full (default)
            return self._analyze_full_mode(frames, video_info, video_path)
    
    def _analyze_full_mode(self, frames: list, video_info: Dict, video_path: Path) -> Dict:
        """Full mode: Coherent narrative with scene tracking"""
        frame_analyses = []
        for i, frame_path in enumerate(frames):
            context_prompt = self._build_context_prompt(i, len(frames), frame_analyses)
            desc = self._analyze_image_with_llava(frame_path, context_prompt)
            frame_analyses.append({
                "frame": i + 1,
                "timestamp": self._get_frame_timestamp(i, len(frames), video_info),
                "description": desc
            })
        
        narrative = self._build_video_narrative(frame_analyses, video_info)
        
        return {
            "success": True,
            "file": str(video_path),
            "model": self.model,
            "mode": "full",
            "description": narrative,
            "num_frames": len(frames),
            "duration": video_info.get("duration", "unknown"),
            "scenes": len(frame_analyses)
        }
    
    def _analyze_stream_mode(self, frames: list, video_info: Dict, video_path: Path) -> Dict:
        """Stream mode: Detailed frame-by-frame analysis"""
        frame_details = []
        
        for i, frame_path in enumerate(frames):
            timestamp = self._get_frame_timestamp(i, len(frames), video_info)
            
            # Detailed prompt for each frame
            prompt = f"""Analyze this video frame in detail:
1. SUBJECTS: Who/what is visible? Describe appearance, position, actions.
2. SETTING: Where is this? Describe environment, lighting, colors.
3. OBJECTS: List all visible objects and their positions.
4. ACTION: What is happening in this exact moment?
5. TEXT: Any visible text, labels, or UI elements?

{self.prompt}"""
            
            desc = self._analyze_image_with_llava(frame_path, prompt)
            
            frame_details.append({
                "frame": i + 1,
                "timestamp": timestamp,
                "description": desc,
                "file": str(frame_path)
            })
        
        return {
            "success": True,
            "file": str(video_path),
            "model": self.model,
            "mode": "stream",
            "frames": frame_details,
            "num_frames": len(frames),
            "duration": video_info.get("duration", "unknown")
        }
    
    def _analyze_diff_mode(self, frames: list, video_info: Dict, video_path: Path) -> Dict:
        """Diff mode: Analyze changes between consecutive frames"""
        changes = []
        prev_description = None
        
        for i, frame_path in enumerate(frames):
            timestamp = self._get_frame_timestamp(i, len(frames), video_info)
            
            if i == 0:
                # First frame - full description
                prompt = f"Describe this opening frame: subjects, setting, objects, action. {self.prompt}"
                desc = self._analyze_image_with_llava(frame_path, prompt)
                changes.append({
                    "frame": 1,
                    "timestamp": timestamp,
                    "type": "start",
                    "description": desc
                })
                prev_description = desc
            else:
                # Compare with previous
                prompt = f"""Compare this frame with the previous description and identify CHANGES:

PREVIOUS: {prev_description[:500]}...

For THIS frame, describe ONLY what has changed:
1. NEW: What appeared that wasn't there before?
2. REMOVED: What disappeared?
3. MOVED: What changed position?
4. CHANGED: What looks different (lighting, color, expression)?
5. ACTION: What new action is happening?

If nothing significant changed, say "No significant changes."
{self.prompt}"""
                
                desc = self._analyze_image_with_llava(frame_path, prompt)
                
                change_type = "no_change" if "no significant" in desc.lower() else "change"
                
                changes.append({
                    "frame": i + 1,
                    "timestamp": timestamp,
                    "type": change_type,
                    "changes": desc
                })
                
                # Update context for next comparison
                if change_type == "change":
                    prev_description = desc
        
        # Summarize all changes
        summary = self._summarize_changes(changes, video_info)
        
        return {
            "success": True,
            "file": str(video_path),
            "model": self.model,
            "mode": "diff",
            "timeline": changes,
            "summary": summary,
            "num_frames": len(frames),
            "significant_changes": sum(1 for c in changes if c.get("type") == "change"),
            "duration": video_info.get("duration", "unknown")
        }
    
    def _summarize_changes(self, changes: list, video_info: Dict) -> str:
        """Summarize all detected changes in video"""
        significant = [c for c in changes if c.get("type") == "change"]
        
        if not significant:
            return "No significant changes detected throughout the video."
        
        try:
            import requests
            
            changes_text = "\n".join([
                f"[{c['timestamp']}] {c.get('changes', c.get('description', ''))[:200]}"
                for c in significant[:10]
            ])
            
            prompt = f"""Based on these detected changes in a video, write a brief summary of what happens:

{changes_text}

Summary (2-3 sentences):"""
            
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            default_model = config.get("SQ_MODEL", "qwen2.5:14b")
            timeout = int(config.get("SQ_LLM_TIMEOUT", "30"))
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={"model": default_model, "prompt": prompt, "stream": False},
                timeout=timeout
            )
            
            if response.ok:
                return response.json().get("response", f"{len(significant)} significant changes detected.")
        except Exception:
            pass
        
        return f"{len(significant)} significant changes detected across {len(changes)} frames."
    
    def _get_video_info(self, video_path: Path) -> Dict:
        """Get video metadata using ffprobe"""
        try:
            result = subprocess.run([
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(video_path)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                duration = float(data.get("format", {}).get("duration", 0))
                return {
                    "duration": duration,
                    "duration_str": f"{int(duration//60)}:{int(duration%60):02d}",
                    "fps": 30  # default
                }
        except Exception:
            pass
        return {"duration": 0, "duration_str": "unknown", "fps": 30}
    
    def _extract_frames_smart(self, video_path: Path, video_info: Dict, max_frames: int = 15) -> list:
        """Extract frames at scene changes and key moments"""
        import tempfile
        frames_dir = Path(tempfile.mkdtemp())
        
        duration = video_info.get("duration", 60)
        # More frames for longer videos, min 5, max based on mode
        num_frames = min(max_frames, max(5, int(duration / 10)))
        
        try:
            # Use scene detection if available
            subprocess.run([
                "ffmpeg", "-i", str(video_path),
                "-vf", f"select='gt(scene,0.3)',scale=640:-1",  # Scene change detection
                "-vsync", "vfr",
                "-frames:v", str(num_frames),
                str(frames_dir / "scene_%03d.jpg")
            ], check=True, capture_output=True, timeout=60)
            
            frames = sorted(frames_dir.glob("scene_*.jpg"))
            if frames:
                return frames
        except Exception:
            pass
        
        # Fallback: uniform sampling
        return self._extract_frames(video_path, num_frames)
    
    def _build_context_prompt(self, frame_idx: int, total_frames: int, prev_analyses: list) -> str:
        """Build context-aware prompt for frame analysis"""
        base_prompt = self.prompt or "Describe what you see in this video frame."
        
        if frame_idx == 0:
            return f"{base_prompt} This is the opening scene. Identify key subjects, setting, and initial action."
        
        # Include context from previous frames
        context = ""
        if prev_analyses:
            last = prev_analyses[-1]["description"][:200]
            context = f"Previous scene showed: {last}... "
        
        position = "middle" if frame_idx < total_frames - 1 else "final"
        return f"{context}Now describe this {position} scene. {base_prompt} Note any changes from before, track recurring subjects."
    
    def _get_frame_timestamp(self, frame_idx: int, total_frames: int, video_info: Dict) -> str:
        """Calculate approximate timestamp for frame"""
        duration = video_info.get("duration", 0)
        if duration and total_frames > 1:
            time_sec = (frame_idx / (total_frames - 1)) * duration
            return f"{int(time_sec//60)}:{int(time_sec%60):02d}"
        return f"frame {frame_idx + 1}"
    
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
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            model = config.get("SQ_MODEL", "llava")
            timeout = int(config.get("SQ_LLM_TIMEOUT", "60"))
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=timeout
            )
            
            if response.ok:
                return response.json().get("response", "")
            else:
                return f"Error analyzing image: {response.status_code}"
                
        except Exception as e:
            return f"Could not analyze image: {e}"
    
    def _build_video_narrative(self, frame_analyses: list, video_info: Dict) -> str:
        """Build coherent video narrative with scene tracking"""
        if not frame_analyses:
            return "No description available"
        
        if len(frame_analyses) == 1:
            return frame_analyses[0]["description"]
        
        # Build structured scene breakdown
        scenes_text = []
        for analysis in frame_analyses:
            ts = analysis.get("timestamp", "")
            desc = analysis["description"][:300]  # Limit length
            scenes_text.append(f"[{ts}] {desc}")
        
        duration_str = video_info.get("duration_str", "unknown length")
        
        # Use LLM to create narrative
        try:
            import requests
            
            prompt = f"""Analyze this video ({duration_str}) based on scene descriptions. 
Create a coherent narrative that:
1. Identifies main subjects/characters and tracks them through the video
2. Describes the setting and how it changes
3. Explains the story/action flow from start to end
4. Notes any recurring themes or objects

Scene breakdown:
{chr(10).join(scenes_text)}

Write a professional video description (2-3 paragraphs) that tells what happens in this video:"""
            
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            narrative_model = config.get("SQ_NARRATIVE_MODEL", "qwen2.5:14b")
            timeout = int(config.get("SQ_LLM_TIMEOUT", "60"))
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": narrative_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=timeout
            )
            
            if response.ok:
                return response.json().get("response", "\n".join(scenes_text))
            
        except Exception:
            pass
        
        # Fallback: structured scene list
        return f"Video ({duration_str}):\n" + "\n".join(scenes_text)
    
    def _combine_descriptions(self, descriptions: list) -> str:
        """Legacy: Combine multiple descriptions (deprecated, use _build_video_narrative)"""
        return self._build_video_narrative(
            [{"description": d, "timestamp": f"scene {i+1}"} for i, d in enumerate(descriptions)],
            {"duration_str": "unknown"}
        )


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
