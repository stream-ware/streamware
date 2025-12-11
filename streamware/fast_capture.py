"""
Fast Capture - Optimized RTSP frame capture

Uses:
- Persistent FFmpeg connection (no startup overhead)
- GPU hardware decoding (NVDEC on NVIDIA)
- OpenCV capture (alternative, often faster)
- RAM disk for all I/O
- Pre-buffering for instant frame access

Reduces capture time from ~4-5s to ~50-200ms.

Usage:
    from streamware.fast_capture import FastCapture
    
    capture = FastCapture(rtsp_url)
    capture.start()
    
    frame = capture.get_frame()  # Instant!
    
    capture.stop()
    
    # Or use OpenCV capture (even faster):
    capture = FastCapture(rtsp_url, backend="opencv")
"""

import logging
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread, Event, Lock
from queue import Queue, Empty
from typing import Optional, Tuple, List

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class FrameInfo:
    """Information about a captured frame."""
    path: Path
    frame_num: int
    timestamp: float
    capture_time_ms: float


class FastCapture:
    """High-performance RTSP capture with GPU acceleration.
    
    Backends:
        - "ffmpeg": Persistent FFmpeg process (default, most compatible)
        - "opencv": OpenCV VideoCapture (faster, requires opencv-python)
    """
    
    def __init__(
        self,
        rtsp_url: str,
        fps: float = 1.0,
        use_gpu: bool = True,
        buffer_size: int = 3,
        resolution: Tuple[int, int] = None,
        backend: str = "auto",  # "auto", "opencv", "ffmpeg"
        output_dir: str = None,  # Custom output directory for frame files
    ):
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.use_gpu = use_gpu
        self.buffer_size = buffer_size
        self.resolution = resolution
        
        # Auto-select backend: prefer OpenCV if available
        if backend == "auto":
            # Check config first
            config_backend = config.get("SQ_CAPTURE_BACKEND", "auto")
            if config_backend in ("opencv", "ffmpeg"):
                self.backend = config_backend
            else:
                self.backend = "opencv" if self._check_opencv() else "ffmpeg"
        else:
            self.backend = backend
        
        # Use RAM disk (custom directory if specified)
        if output_dir:
            self.ramdisk_path = Path(output_dir)
        else:
            self.ramdisk_path = Path(config.get("SQ_RAMDISK_PATH", "/dev/shm/streamware"))
        self.ramdisk_path.mkdir(parents=True, exist_ok=True)
        
        # State
        self._running = False
        self._stop_event = Event()
        self._capture_thread: Optional[Thread] = None
        self._frame_queue: Queue = Queue(maxsize=buffer_size)
        self._frame_num = 0
        self._lock = Lock()
        
        # FFmpeg process
        self._ffmpeg_process: Optional[subprocess.Popen] = None
        
        # OpenCV capture
        self._cv_capture = None
        
        # Check GPU availability
        self._has_nvdec = self._check_nvdec() if use_gpu else False
        
        # Stats
        self._capture_times: List[float] = []
    
    def _check_opencv(self) -> bool:
        """Check if OpenCV is available."""
        try:
            import cv2
            return True
        except ImportError:
            return False
    
    def _check_nvdec(self) -> bool:
        """Check if NVDEC hardware decoding is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-hwaccels"],
                capture_output=True, text=True, timeout=5
            )
            return "cuda" in result.stdout.lower() or "nvdec" in result.stdout.lower()
        except Exception:
            return False
    
    def _build_ffmpeg_cmd(self) -> List[str]:
        """Build optimized FFmpeg command for continuous capture."""
        cmd = ["ffmpeg", "-y"]
        
        # Input options - optimize for low latency RTSP
        cmd.extend([
            "-rtsp_transport", "tcp",
            "-fflags", "+nobuffer+flush_packets",
            "-flags", "low_delay",
            "-analyzeduration", "500000",   # 0.5 second
            "-probesize", "500000",
            "-max_delay", "500000",
            "-reorder_queue_size", "0",
        ])
        
        # GPU hardware decoding (NVIDIA)
        if self._has_nvdec:
            cmd.extend([
                "-hwaccel", "cuda",
            ])
            logger.info("Using NVIDIA NVDEC hardware decoding")
        
        # Input
        cmd.extend(["-i", self.rtsp_url])
        
        # Output - single file that gets overwritten (fastest)
        output_file = str(self.ramdisk_path / "latest.jpg")
        
        # FPS filter + output
        vf_filter = f"fps={self.fps}"
        if self.resolution:
            w, h = self.resolution
            vf_filter += f",scale={w}:{h}"
        
        cmd.extend([
            "-vf", vf_filter,
            "-q:v", "3",
            "-update", "1",  # Overwrite single file
            "-atomic_writing", "1",  # Atomic write
            output_file
        ])
        
        return cmd
    
    def start(self):
        """Start continuous capture."""
        if self._running:
            return
        
        # Clean old frames
        self._cleanup_frames()
        
        self._running = True
        self._stop_event.clear()
        self._frame_num = 0
        
        if self.backend == "opencv":
            # OpenCV capture (faster, lower latency)
            self._start_opencv()
        else:
            # FFmpeg capture (more compatible)
            self._start_ffmpeg()
        
        logger.info(f"Started fast capture: {self.fps} FPS, backend: {self.backend}, GPU: {self._has_nvdec}")
    
    def _start_opencv(self):
        """Start OpenCV-based capture with cross-platform compatibility."""
        try:
            import cv2
            
            # Try multiple backends in order of preference
            backends_to_try = []
            
            # 1. GStreamer with NVDEC (NVIDIA GPU)
            if self.use_gpu and self._has_nvdec:
                gst_pipeline = (
                    f"rtspsrc location={self.rtsp_url} latency=0 ! "
                    f"rtph264depay ! h264parse ! nvdec ! "
                    f"videoconvert ! appsink"
                )
                backends_to_try.append(("gstreamer_nvdec", gst_pipeline, cv2.CAP_GSTREAMER))
            
            # 2. GStreamer standard (Linux)
            gst_simple = (
                f"rtspsrc location={self.rtsp_url} latency=100 ! "
                f"decodebin ! videoconvert ! appsink"
            )
            backends_to_try.append(("gstreamer", gst_simple, cv2.CAP_GSTREAMER))
            
            # 3. FFmpeg backend (most compatible)
            backends_to_try.append(("ffmpeg", self.rtsp_url, cv2.CAP_FFMPEG))
            
            # 4. Any available backend
            backends_to_try.append(("any", self.rtsp_url, cv2.CAP_ANY))
            
            for name, source, backend in backends_to_try:
                try:
                    logger.debug(f"Trying OpenCV backend: {name}")
                    cap = cv2.VideoCapture(source, backend)
                    
                    # Set buffer size low for lower latency
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    if cap.isOpened():
                        # Test read a frame
                        ret, frame = cap.read()
                        if ret and frame is not None:
                            self._cv_capture = cap
                            logger.info(f"OpenCV capture started with backend: {name}")
                            
                            # Start capture thread
                            self._capture_thread = Thread(target=self._opencv_capture_loop, daemon=True)
                            self._capture_thread.start()
                            return
                        else:
                            cap.release()
                    else:
                        cap.release()
                except Exception as e:
                    logger.debug(f"Backend {name} failed: {e}")
                    continue
            
            # All backends failed
            raise RuntimeError("All OpenCV backends failed")
            
        except Exception as e:
            logger.warning(f"OpenCV capture failed, falling back to FFmpeg: {e}")
            self.backend = "ffmpeg"
            self._start_ffmpeg()
    
    def _start_ffmpeg(self):
        """Start FFmpeg-based capture."""
        cmd = self._build_ffmpeg_cmd()
        logger.debug(f"FFmpeg command: {' '.join(cmd)}")
        
        self._ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
        
        # Start frame monitoring thread
        self._capture_thread = Thread(target=self._monitor_frames, daemon=True)
        self._capture_thread.start()
    
    def _opencv_capture_loop(self):
        """OpenCV capture loop - fastest method."""
        try:
            import cv2
        except ImportError:
            return
        
        frame_interval = 1.0 / self.fps
        last_capture = 0
        read_errors = 0
        
        print(f"📹 FastCapture loop started (interval={frame_interval:.2f}s)", flush=True)
        
        while not self._stop_event.is_set():
            try:
                now = time.time()
                
                # Rate limit captures
                if now - last_capture < frame_interval:
                    time.sleep(0.01)
                    continue
                
                start = time.perf_counter()
                ret, frame = self._cv_capture.read()
                capture_ms = (time.perf_counter() - start) * 1000
                
                if not ret or frame is None:
                    read_errors += 1
                    if read_errors % 10 == 1:
                        print(f"⚠️ FastCapture read error #{read_errors}", flush=True)
                    time.sleep(0.1)
                    continue
                
                read_errors = 0  # Reset on success
                
                if ret and frame is not None:
                    self._frame_num += 1
                    
                    # Resize if needed
                    if self.resolution:
                        frame = cv2.resize(frame, self.resolution)
                    
                    # Save to RAM disk
                    frame_path = self.ramdisk_path / f"frame_{self._frame_num:05d}.jpg"
                    cv2.imwrite(str(frame_path), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                    
                    frame_info = FrameInfo(
                        path=frame_path,
                        frame_num=self._frame_num,
                        timestamp=now,
                        capture_time_ms=capture_ms
                    )
                    
                    # Add to queue
                    try:
                        self._frame_queue.put_nowait(frame_info)
                    except Exception:
                        try:
                            self._frame_queue.get_nowait()
                            self._frame_queue.put_nowait(frame_info)
                        except Exception:
                            pass
                    
                    self._capture_times.append(capture_ms)
                    last_capture = now
                    
                    # Cleanup old frames
                    self._cleanup_old_frames()
                    
            except Exception as e:
                logger.debug(f"OpenCV capture error: {e}")
                time.sleep(0.1)
        
        # Cleanup
        if self._cv_capture:
            self._cv_capture.release()
    
    def _cleanup_old_frames(self):
        """Remove old frame files, keep last 30 (enough for slow LLM processing)."""
        try:
            old_frames = sorted(self.ramdisk_path.glob("frame_*.jpg"))
            if len(old_frames) > 30:
                for old_frame in old_frames[:-30]:
                    try:
                        old_frame.unlink()
                    except OSError:
                        pass
        except OSError:
            pass
    
    def stop(self):
        """Stop capture."""
        self._running = False
        self._stop_event.set()
        
        # Stop FFmpeg
        if self._ffmpeg_process:
            self._ffmpeg_process.terminate()
            try:
                self._ffmpeg_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._ffmpeg_process.kill()
            self._ffmpeg_process = None
        
        # Stop OpenCV
        if self._cv_capture:
            try:
                self._cv_capture.release()
            except Exception:
                pass
            self._cv_capture = None
        
        # Wait for thread
        if self._capture_thread:
            self._capture_thread.join(timeout=2)
        
        # Cleanup
        self._cleanup_frames()
        
        logger.info(f"Stopped fast capture (backend: {self.backend})")
    
    def _monitor_frames(self):
        """Monitor for new frames from FFmpeg (single file mode)."""
        latest_file = self.ramdisk_path / "latest.jpg"
        last_mtime = 0
        
        while not self._stop_event.is_set():
            try:
                if latest_file.exists():
                    mtime = latest_file.stat().st_mtime
                    
                    if mtime > last_mtime:
                        # New frame available
                        self._frame_num += 1
                        
                        # Copy to numbered file for processing
                        frame_copy = self.ramdisk_path / f"frame_{self._frame_num:05d}.jpg"
                        try:
                            import shutil
                            shutil.copy2(latest_file, frame_copy)
                        except OSError:
                            frame_copy = latest_file
                        
                        frame_info = FrameInfo(
                            path=frame_copy,
                            frame_num=self._frame_num,
                            timestamp=time.time(),
                            capture_time_ms=0  # Continuous capture = ~0ms
                        )
                        
                        # Add to queue (non-blocking)
                        try:
                            self._frame_queue.put_nowait(frame_info)
                        except Exception:
                            # Queue full, remove oldest
                            try:
                                self._frame_queue.get_nowait()
                                self._frame_queue.put_nowait(frame_info)
                            except Exception:
                                pass
                        
                        last_mtime = mtime
                        
                        # Cleanup old frame copies (keep last 10 for slow processing)
                        old_frames = sorted(self.ramdisk_path.glob("frame_*.jpg"))
                        if len(old_frames) > 10:
                            for old_frame in old_frames[:-10]:
                                try:
                                    old_frame.unlink()
                                except OSError:
                                    pass
                
            except Exception as e:
                logger.debug(f"Frame monitor error: {e}")
            
            # Check every 100ms
            self._stop_event.wait(timeout=0.1)
    
    def get_frame(self, timeout: float = 5.0) -> Optional[FrameInfo]:
        """Get next available frame.
        
        Returns:
            FrameInfo or None if timeout
        """
        try:
            return self._frame_queue.get(timeout=timeout)
        except Empty:
            # Try to get latest frame directly
            latest = self.get_latest_frame()
            if latest and latest.exists():
                return FrameInfo(
                    path=latest,
                    frame_num=self._frame_num,
                    timestamp=time.time(),
                    capture_time_ms=0
                )
            return None
    
    def get_latest_frame(self) -> Optional[Path]:
        """Get path to latest frame (non-blocking)."""
        latest = self.ramdisk_path / "latest.jpg"
        if latest.exists():
            return latest
        frames = sorted(self.ramdisk_path.glob("frame_*.jpg"))
        return frames[-1] if frames else None
    
    def capture_single(self) -> Optional[Path]:
        """Capture a single frame (for non-streaming use).
        
        Optimized with GPU if available.
        """
        self._frame_num += 1
        output_path = self.ramdisk_path / f"single_{self._frame_num:05d}.jpg"
        
        cmd = ["ffmpeg", "-y"]
        
        # GPU acceleration
        if self._has_nvdec:
            cmd.extend(["-hwaccel", "cuda"])
        
        # Low latency input
        cmd.extend([
            "-rtsp_transport", "tcp",
            "-fflags", "nobuffer",
            "-i", self.rtsp_url,
            "-frames:v", "1",
            "-q:v", "2",
        ])
        
        # Resolution
        if self.resolution:
            w, h = self.resolution
            cmd.extend(["-vf", f"scale={w}:{h}"])
        
        cmd.append(str(output_path))
        
        start = time.perf_counter()
        try:
            subprocess.run(cmd, capture_output=True, timeout=10, check=True, stdin=subprocess.DEVNULL)
            capture_time = (time.perf_counter() - start) * 1000
            self._capture_times.append(capture_time)
            logger.debug(f"Single capture: {capture_time:.0f}ms")
            return output_path
        except Exception as e:
            logger.debug(f"Single capture failed: {e}")
            return None
    
    def _cleanup_frames(self):
        """Remove all frame files."""
        for pattern in ["frame_*.jpg", "single_*.jpg", "latest.jpg"]:
            for f in self.ramdisk_path.glob(pattern):
                try:
                    f.unlink()
                except OSError:
                    pass
    
    @property
    def avg_capture_time(self) -> float:
        """Average capture time in ms."""
        if self._capture_times:
            return sum(self._capture_times[-20:]) / len(self._capture_times[-20:])
        return 0
    
    @property
    def is_running(self) -> bool:
        return self._running


# Global instance
_fast_capture: Optional[FastCapture] = None


def get_fast_capture(rtsp_url: str = None, **kwargs) -> FastCapture:
    """Get or create fast capture instance."""
    global _fast_capture
    
    if _fast_capture is None or (rtsp_url and _fast_capture.rtsp_url != rtsp_url):
        if _fast_capture:
            _fast_capture.stop()
        _fast_capture = FastCapture(rtsp_url, **kwargs)
    
    return _fast_capture


def cleanup():
    """Cleanup global instance."""
    global _fast_capture
    if _fast_capture:
        _fast_capture.stop()
        _fast_capture = None
