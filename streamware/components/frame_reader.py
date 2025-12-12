"""
Frame Reader Component - OCR + LLM Vision Analysis

Reads text from video frames using OCR and optionally queries LLM 
for image understanding.

Usage:
    sq live reader --url rtsp://... --ocr --llm-query "what is happening?"
    sq live reader --url /dev/video0 --ocr --lang pl
    sq live reader --url screen:// --ocr --continuous

Features:
    - Multiple OCR engines (tesseract, easyocr, paddleocr)
    - LLM vision queries (ollama, openai)
    - Text tracking across frames (diff mode)
    - Multi-language OCR support
    - Continuous or single-shot mode
"""

import logging
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR text extraction."""
    text: str
    confidence: float
    boxes: List[Dict] = field(default_factory=list)  # Bounding boxes
    language: str = "en"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "boxes": self.boxes,
            "language": self.language,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class FrameAnalysis:
    """Combined OCR + LLM analysis result."""
    frame_num: int
    ocr_result: Optional[OCRResult]
    llm_response: Optional[str]
    frame_path: Optional[Path]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "frame_num": self.frame_num,
            "ocr": self.ocr_result.to_dict() if self.ocr_result else None,
            "llm_response": self.llm_response,
            "frame_path": str(self.frame_path) if self.frame_path else None,
            "timestamp": self.timestamp.isoformat(),
        }


@register("reader")
class FrameReaderComponent(Component):
    """
    Frame Reader - OCR and LLM Vision Analysis
    
    Captures frames from video sources and extracts text using OCR,
    with optional LLM queries for deeper image understanding.
    """
    
    name = "reader"
    category = "live"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        
        # Helper to safely parse bool params (handles both str and bool)
        def parse_bool(val, default=False):
            if isinstance(val, bool):
                return val
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes")
            return default
        
        # Source configuration
        self.source = uri.get_param("url") or uri.get_param("source")
        
        # OCR configuration
        self.ocr_enabled = parse_bool(uri.get_param("ocr", "true"), True)
        self.ocr_engine = uri.get_param("ocr_engine", "tesseract")  # tesseract, easyocr, paddleocr
        self.ocr_lang = uri.get_param("lang", "eng")  # tesseract language code
        
        # LLM configuration
        self.llm_enabled = parse_bool(uri.get_param("llm", "false"), False)
        self.llm_query = uri.get_param("query", "") or ""
        self.llm_model = uri.get_param("model", "llava:7b")
        self.ollama_url = uri.get_param("ollama_url", "http://localhost:11434")
        
        # Processing configuration
        self.interval = float(uri.get_param("interval", "2.0") or 2.0)
        self.duration = float(uri.get_param("duration", "60") or 60)
        self.continuous = parse_bool(uri.get_param("continuous", "false"), False)
        self.diff_mode = parse_bool(uri.get_param("diff", "false"), False)
        
        # TTS configuration
        self.tts_enabled = parse_bool(uri.get_param("tts", "false"), False)
        self.tts_lang = uri.get_param("tts_lang", "en") or "en"
        
        # State
        self._running = False
        self._prev_text = ""
        self._history: List[FrameAnalysis] = []
        self._temp_dir: Optional[Path] = None
        
    def process(self, data: Any = None) -> Dict:
        """Run frame reading and analysis."""
        if not self.source:
            raise ComponentError("Source URL is required")
        
        self._temp_dir = Path(tempfile.mkdtemp())
        self._running = True
        
        print(f"📖 Frame Reader starting...")
        print(f"   Source: {self.source}")
        print(f"   OCR: {self.ocr_engine} ({self.ocr_lang})")
        if self.llm_enabled:
            print(f"   LLM: {self.llm_model}")
            if self.llm_query:
                print(f"   Query: {self.llm_query}")
        print(f"   Interval: {self.interval}s, Duration: {self.duration}s")
        
        start_time = time.time()
        frame_num = 0
        
        while self._running:
            elapsed = time.time() - start_time
            
            if not self.continuous and elapsed >= self.duration:
                break
            
            frame_num += 1
            
            # Capture frame
            frame_path = self._capture_frame(frame_num)
            if not frame_path or not frame_path.exists():
                print(f"   ⚠️ Frame capture failed")
                time.sleep(self.interval)
                continue
            
            # Analyze frame
            analysis = self._analyze_frame(frame_num, frame_path)
            
            if analysis:
                self._history.append(analysis)
                self._print_analysis(analysis)
                
                # TTS if enabled
                if self.tts_enabled and analysis.ocr_result and analysis.ocr_result.text:
                    self._speak(analysis.ocr_result.text[:200])
            
            time.sleep(self.interval)
        
        print(f"\n📖 Frame Reader finished")
        print(f"   Frames analyzed: {frame_num}")
        print(f"   Text extractions: {len([h for h in self._history if h.ocr_result and h.ocr_result.text])}")
        
        return {
            "frames": frame_num,
            "analyses": len(self._history),
            "history": [h.to_dict() for h in self._history[-10:]],
        }
    
    def _capture_frame(self, frame_num: int) -> Optional[Path]:
        """Capture a single frame from the source."""
        output_path = self._temp_dir / f"frame_{frame_num:04d}.jpg"
        
        try:
            # Screen capture
            if self.source.startswith("screen://"):
                return self._capture_screen(output_path)
            
            # Webcam or video file
            cmd = [
                "ffmpeg", "-y",
                "-i", self.source,
                "-vframes", "1",
                "-q:v", "2",
                str(output_path)
            ]
            
            # Add RTSP options
            if self.source.startswith("rtsp://"):
                cmd = ["ffmpeg", "-y", "-rtsp_transport", "tcp", "-i", self.source,
                       "-vframes", "1", "-q:v", "2", str(output_path)]
            
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            
            if output_path.exists():
                return output_path
                
        except Exception as e:
            logger.debug(f"Frame capture error: {e}")
        
        return None
    
    def _capture_screen(self, output_path: Path) -> Optional[Path]:
        """Capture screenshot."""
        try:
            # Try different screenshot tools
            tools = [
                ["gnome-screenshot", "-f", str(output_path)],
                ["scrot", str(output_path)],
                ["import", "-window", "root", str(output_path)],
            ]
            
            for cmd in tools:
                try:
                    subprocess.run(cmd, capture_output=True, timeout=5)
                    if output_path.exists():
                        return output_path
                except FileNotFoundError:
                    continue
                    
        except Exception as e:
            logger.debug(f"Screen capture error: {e}")
        
        return None
    
    def _analyze_frame(self, frame_num: int, frame_path: Path) -> Optional[FrameAnalysis]:
        """Analyze frame with OCR and optional LLM."""
        ocr_result = None
        llm_response = None
        
        # OCR extraction
        if self.ocr_enabled:
            ocr_result = self._extract_text(frame_path)
            
            # Diff mode - skip if same as previous
            if self.diff_mode and ocr_result:
                if ocr_result.text.strip() == self._prev_text.strip():
                    return None
                self._prev_text = ocr_result.text
        
        # LLM query
        if self.llm_enabled:
            query = self.llm_query
            
            # If no explicit query, ask about OCR text
            if not query and ocr_result and ocr_result.text:
                query = f"I see this text in the image: '{ocr_result.text[:200]}'. What is this? Describe what you see."
            elif not query:
                query = "Describe what you see in this image. Be concise."
            
            llm_response = self._query_llm(frame_path, query)
        
        return FrameAnalysis(
            frame_num=frame_num,
            ocr_result=ocr_result,
            llm_response=llm_response,
            frame_path=frame_path,
        )
    
    def _extract_text(self, frame_path: Path) -> Optional[OCRResult]:
        """Extract text from image using OCR."""
        try:
            if self.ocr_engine == "tesseract":
                return self._ocr_tesseract(frame_path)
            elif self.ocr_engine == "easyocr":
                return self._ocr_easyocr(frame_path)
            elif self.ocr_engine == "paddleocr":
                return self._ocr_paddleocr(frame_path)
            else:
                return self._ocr_tesseract(frame_path)
        except Exception as e:
            logger.debug(f"OCR error: {e}")
            return None
    
    def _ocr_tesseract(self, frame_path: Path) -> Optional[OCRResult]:
        """Extract text using Tesseract OCR."""
        try:
            result = subprocess.run(
                ["tesseract", str(frame_path), "stdout", "-l", self.ocr_lang],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                text = result.stdout.strip()
                return OCRResult(
                    text=text,
                    confidence=0.8 if text else 0.0,
                    language=self.ocr_lang,
                )
        except FileNotFoundError:
            print("   ⚠️ Tesseract not found. Install: sudo apt install tesseract-ocr")
        except Exception as e:
            logger.debug(f"Tesseract error: {e}")
        
        return None
    
    def _ocr_easyocr(self, frame_path: Path) -> Optional[OCRResult]:
        """Extract text using EasyOCR."""
        try:
            import easyocr
            
            # Map language codes
            lang_map = {"eng": "en", "pol": "pl", "deu": "de"}
            lang = lang_map.get(self.ocr_lang, self.ocr_lang)
            
            reader = easyocr.Reader([lang], gpu=False)
            results = reader.readtext(str(frame_path))
            
            if results:
                text = " ".join([r[1] for r in results])
                avg_conf = sum(r[2] for r in results) / len(results)
                boxes = [{"box": r[0], "text": r[1], "conf": r[2]} for r in results]
                
                return OCRResult(
                    text=text,
                    confidence=avg_conf,
                    boxes=boxes,
                    language=lang,
                )
        except ImportError:
            print("   ⚠️ EasyOCR not installed. Install: pip install easyocr")
        except Exception as e:
            logger.debug(f"EasyOCR error: {e}")
        
        return None
    
    def _ocr_paddleocr(self, frame_path: Path) -> Optional[OCRResult]:
        """Extract text using PaddleOCR."""
        try:
            from paddleocr import PaddleOCR
            
            lang_map = {"eng": "en", "pol": "pl", "deu": "german"}
            lang = lang_map.get(self.ocr_lang, "en")
            
            ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
            results = ocr.ocr(str(frame_path), cls=True)
            
            if results and results[0]:
                texts = []
                confidences = []
                boxes = []
                
                for line in results[0]:
                    if line[1]:
                        texts.append(line[1][0])
                        confidences.append(line[1][1])
                        boxes.append({"box": line[0], "text": line[1][0], "conf": line[1][1]})
                
                return OCRResult(
                    text=" ".join(texts),
                    confidence=sum(confidences) / len(confidences) if confidences else 0,
                    boxes=boxes,
                    language=lang,
                )
        except ImportError:
            print("   ⚠️ PaddleOCR not installed. Install: pip install paddleocr")
        except Exception as e:
            logger.debug(f"PaddleOCR error: {e}")
        
        return None
    
    def _query_llm(self, frame_path: Path, query: str) -> Optional[str]:
        """Query LLM about the image."""
        try:
            import base64
            import requests
            
            # Read and encode image
            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Add language instruction
            if self.tts_lang == "pl":
                query = f"🇵🇱 ODPOWIEDZ PO POLSKU!\n\n{query}\n\n⚠️ Odpowiedz po polsku."
            elif self.tts_lang == "de":
                query = f"🇩🇪 ANTWORTE AUF DEUTSCH!\n\n{query}\n\n⚠️ Antworte auf Deutsch."
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.llm_model,
                    "prompt": query,
                    "images": [image_data],
                    "stream": False
                },
                timeout=60
            )
            
            if response.ok:
                return response.json().get("response", "").strip()
                
        except Exception as e:
            logger.debug(f"LLM query error: {e}")
        
        return None
    
    def _print_analysis(self, analysis: FrameAnalysis):
        """Print analysis results."""
        ts = analysis.timestamp.strftime("%H:%M:%S")
        print(f"\n🔍 [{ts}] Frame #{analysis.frame_num}")
        
        if analysis.ocr_result and analysis.ocr_result.text:
            text = analysis.ocr_result.text[:200]
            conf = analysis.ocr_result.confidence
            print(f"   📝 OCR ({conf:.0%}): {text}")
        
        if analysis.llm_response:
            response = analysis.llm_response[:300]
            print(f"   🤖 LLM: {response}")
    
    def _speak(self, text: str):
        """Speak text using TTS."""
        try:
            from ..tts_worker_process import get_tts_worker
            
            worker = get_tts_worker(
                engine="pico",
                lang=self.tts_lang,
            )
            worker.speak(text, voice=self.tts_lang if self.tts_lang != "en" else "")
        except Exception as e:
            logger.debug(f"TTS error: {e}")
    
    def stop(self):
        """Stop the frame reader."""
        self._running = False


def register_reader_commands(subparsers):
    """Register CLI commands for frame reader."""
    reader_parser = subparsers.add_parser('reader', help='Read text from video frames using OCR')
    reader_parser.add_argument('--url', '-u', required=True, help='Video source URL')
    reader_parser.add_argument('--ocr', action='store_true', default=True, help='Enable OCR (default)')
    reader_parser.add_argument('--ocr-engine', choices=['tesseract', 'easyocr', 'paddleocr'], default='tesseract')
    reader_parser.add_argument('--lang', '-l', default='eng', help='OCR language (eng, pol, deu, etc.)')
    reader_parser.add_argument('--llm', action='store_true', help='Enable LLM vision queries')
    reader_parser.add_argument('--query', '-q', help='Custom LLM query about the image')
    reader_parser.add_argument('--model', '-m', default='llava:7b', help='Vision LLM model')
    reader_parser.add_argument('--interval', '-i', type=float, default=2.0, help='Capture interval (seconds)')
    reader_parser.add_argument('--duration', '-d', type=float, default=60, help='Duration (seconds)')
    reader_parser.add_argument('--continuous', '-c', action='store_true', help='Run continuously')
    reader_parser.add_argument('--diff', action='store_true', help='Only report when text changes')
    reader_parser.add_argument('--tts', action='store_true', help='Read text aloud')
    reader_parser.add_argument('--tts-lang', default='en', help='TTS language (en, pl, de)')
