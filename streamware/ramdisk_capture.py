"""
RAM Disk Frame Capture - High-performance frame capture using tmpfs

Instead of writing frames to disk, uses a RAM-based filesystem for:
- Ultra-fast I/O (no disk latency)
- Automatic cleanup
- Reduced SSD wear

Usage:
    from streamware.ramdisk_capture import RAMDiskCapture
    
    capture = RAMDiskCapture(rtsp_url, fps=1)
    capture.start()
    
    frame_path = capture.get_latest_frame()
    # Process frame...
    
    capture.stop()

Configuration via .env:
    SQ_RAMDISK_PATH=/dev/shm/streamware
    SQ_RAMDISK_SIZE_MB=512
    SQ_CAPTURE_FPS=1
"""

import logging
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Thread, Event, Lock
from typing import Optional, Callable, Tuple
from queue import Queue, Empty

from .config import config

logger = logging.getLogger(__name__)


@dataclass
class CaptureConfig:
    """Configuration for RAM disk capture."""
    rtsp_url: str
    fps: float = 1.0                    # Frames per second to capture
    ramdisk_path: str = "/dev/shm/streamware"  # Default Linux shared memory
    max_frames: int = 5                  # Keep last N frames
    resolution: Tuple[int, int] = None   # Optional resize (width, height)
    quality: int = 85                    # JPEG quality


class RAMDiskCapture:
    """High-performance frame capture using RAM disk."""
    
    def __init__(
        self,
        rtsp_url: str,
        fps: float = None,
        ramdisk_path: str = None,
        max_frames: int = 5,
        resolution: Tuple[int, int] = None,
    ):
        self.rtsp_url = rtsp_url
        self.fps = fps or float(config.get("SQ_CAPTURE_FPS", "1"))
        self.max_frames = max_frames
        self.resolution = resolution
        
        # Determine RAM disk path
        self.ramdisk_path = Path(
            ramdisk_path or 
            config.get("SQ_RAMDISK_PATH", "/dev/shm/streamware")
        )
        
        # State
        self._running = False
        self._stop_event = Event()
        self._capture_thread: Optional[Thread] = None
        self._frame_num = 0
        self._frames_lock = Lock()
        self._frame_queue: Queue = Queue(maxsize=max_frames * 2)
        self._latest_frame: Optional[Path] = None
        self._latest_timestamp: float = 0
        
        # FFmpeg process
        self._ffmpeg_process: Optional[subprocess.Popen] = None
        
        # Initialize RAM disk
        self._init_ramdisk()
    
    def _init_ramdisk(self):
        """Initialize RAM disk directory."""
        try:
            # Use /dev/shm on Linux (already tmpfs)
            if self.ramdisk_path.parts[1] == "dev" and self.ramdisk_path.parts[2] == "shm":
                # /dev/shm is already a tmpfs mount on Linux
                self.ramdisk_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Using shared memory: {self.ramdisk_path}")
            else:
                # Create in /tmp as fallback (also often tmpfs)
                self.ramdisk_path = Path(tempfile.mkdtemp(prefix="streamware_"))
                logger.info(f"Using temp directory: {self.ramdisk_path}")
            
            # Clean old frames
            self._cleanup_old_frames()
            
        except Exception as e:
            logger.warning(f"Failed to create RAM disk at {self.ramdisk_path}: {e}")
            # Fallback to temp directory
            self.ramdisk_path = Path(tempfile.mkdtemp(prefix="streamware_"))
            logger.info(f"Fallback to: {self.ramdisk_path}")
    
    def _cleanup_old_frames(self):
        """Remove old frame files."""
        try:
            for f in self.ramdisk_path.glob("frame_*.jpg"):
                f.unlink()
        except Exception:
            pass
    
    def start(self):
        """Start continuous frame capture."""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._frame_num = 0
        
        # Start capture thread
        self._capture_thread = Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()
        
        logger.info(f"Started RAM disk capture: {self.fps} FPS → {self.ramdisk_path}")
    
    def stop(self):
        """Stop frame capture."""
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
        
        # Wait for thread
        if self._capture_thread:
            self._capture_thread.join(timeout=2)
        
        # Cleanup
        self._cleanup_old_frames()
        
        logger.info("Stopped RAM disk capture")
    
    def _capture_loop(self):
        """Main capture loop using FFmpeg."""
        interval = 1.0 / self.fps
        
        while not self._stop_event.is_set():
            try:
                frame_path = self._capture_single_frame()
                if frame_path:
                    with self._frames_lock:
                        self._latest_frame = frame_path
                        self._latest_timestamp = time.time()
                    
                    # Add to queue (non-blocking)
                    try:
                        self._frame_queue.put_nowait((self._frame_num, frame_path, time.time()))
                    except Exception:
                        pass
                    
                    # Cleanup old frames
                    self._cleanup_excess_frames()
                
            except Exception as e:
                logger.debug(f"Capture error: {e}")
            
            # Wait for next frame
            self._stop_event.wait(timeout=interval)
    
    def _capture_single_frame(self) -> Optional[Path]:
        """Capture a single frame using FFmpeg."""
        self._frame_num += 1
        output_path = self.ramdisk_path / f"frame_{self._frame_num:06d}.jpg"
        
        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-y",                    # Overwrite
            "-rtsp_transport", "tcp",  # More reliable for RTSP
            "-i", self.rtsp_url,
            "-vframes", "1",         # Single frame
            "-q:v", "2",             # High quality
        ]
        
        # Add resolution scaling if specified
        if self.resolution:
            cmd.extend(["-vf", f"scale={self.resolution[0]}:{self.resolution[1]}"])
        
        cmd.append(str(output_path))
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=10,
            )
            
            if result.returncode == 0 and output_path.exists():
                return output_path
            else:
                logger.debug(f"FFmpeg failed: {result.stderr.decode()[:100]}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.debug("FFmpeg timeout")
            return None
        except Exception as e:
            logger.debug(f"Capture failed: {e}")
            return None
    
    def _cleanup_excess_frames(self):
        """Remove excess frames, keeping only last N."""
        try:
            frames = sorted(self.ramdisk_path.glob("frame_*.jpg"))
            if len(frames) > self.max_frames:
                for f in frames[:-self.max_frames]:
                    try:
                        f.unlink()
                    except OSError:
                        pass
        except Exception:
            pass
    
    def get_latest_frame(self) -> Optional[Path]:
        """Get path to latest captured frame."""
        with self._frames_lock:
            if self._latest_frame and self._latest_frame.exists():
                return self._latest_frame
        return None
    
    def get_frame(self, timeout: float = 5.0) -> Optional[Tuple[int, Path, float]]:
        """Get next frame from queue (blocking).
        
        Returns:
            (frame_num, frame_path, timestamp) or None
        """
        try:
            return self._frame_queue.get(timeout=timeout)
        except Empty:
            return None
    
    def get_frame_age(self) -> float:
        """Get age of latest frame in seconds."""
        with self._frames_lock:
            if self._latest_timestamp:
                return time.time() - self._latest_timestamp
        return float('inf')
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def frame_count(self) -> int:
        return self._frame_num


class ContinuousCapture:
    """Continuous RTSP capture using FFmpeg stream to RAM disk.
    
    More efficient than single-frame capture for high FPS.
    """
    
    def __init__(
        self,
        rtsp_url: str,
        fps: float = 1.0,
        ramdisk_path: str = None,
        max_frames: int = 10,
    ):
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.max_frames = max_frames
        
        self.ramdisk_path = Path(
            ramdisk_path or 
            config.get("SQ_RAMDISK_PATH", "/dev/shm/streamware")
        )
        self.ramdisk_path.mkdir(parents=True, exist_ok=True)
        
        self._ffmpeg_process: Optional[subprocess.Popen] = None
        self._running = False
        self._frame_pattern = "frame_%06d.jpg"
    
    def start(self):
        """Start continuous FFmpeg capture."""
        if self._running:
            return
        
        # Cleanup old frames
        for f in self.ramdisk_path.glob("frame_*.jpg"):
            f.unlink()
        
        # FFmpeg command for continuous capture
        output_pattern = str(self.ramdisk_path / self._frame_pattern)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-rtsp_transport", "tcp",
            "-i", self.rtsp_url,
            "-vf", f"fps={self.fps}",  # Output at specified FPS
            "-q:v", "3",                # Good quality
            "-update", "1",             # Update single file (for latest)
            output_pattern,
        ]
        
        self._ffmpeg_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        
        self._running = True
        logger.info(f"Started continuous capture at {self.fps} FPS")
    
    def stop(self):
        """Stop FFmpeg capture."""
        if self._ffmpeg_process:
            self._ffmpeg_process.terminate()
            try:
                self._ffmpeg_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._ffmpeg_process.kill()
        
        self._running = False
        
        # Cleanup
        for f in self.ramdisk_path.glob("frame_*.jpg"):
            try:
                f.unlink()
            except OSError:
                pass
    
    def get_latest_frame(self) -> Optional[Path]:
        """Get most recent frame."""
        frames = sorted(self.ramdisk_path.glob("frame_*.jpg"))
        if frames:
            return frames[-1]
        return None
    
    def get_all_frames(self) -> list:
        """Get all available frames."""
        return sorted(self.ramdisk_path.glob("frame_*.jpg"))


# Global instance
_capture: Optional[RAMDiskCapture] = None


def get_ramdisk_capture(
    rtsp_url: str = None,
    fps: float = None,
    **kwargs
) -> RAMDiskCapture:
    """Get or create RAM disk capture instance."""
    global _capture
    
    if _capture is None or (rtsp_url and _capture.rtsp_url != rtsp_url):
        if _capture:
            _capture.stop()
        _capture = RAMDiskCapture(rtsp_url, fps=fps, **kwargs)
    
    return _capture


def cleanup():
    """Cleanup global capture instance."""
    global _capture
    if _capture:
        _capture.stop()
        _capture = None
