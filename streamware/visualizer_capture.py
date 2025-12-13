"""
RTSP Capture Thread

Captures frames from RTSP stream in background thread.
Supports multiple backends: OpenCV, GStreamer, PyAV.
Extracted from realtime_visualizer.py for modularity.
"""

import logging
import queue
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class RTSPCapture:
    """
    Captures frames from RTSP stream in background thread.
    
    Args:
        rtsp_url: RTSP stream URL
        fps: Target frames per second
        width: Frame width
        height: Frame height
        transport: 'tcp' (stable) or 'udp' (lower latency)
        backend: 'opencv' (default), 'gstreamer' (faster), 'pyav' (direct API)
    """
    
    def __init__(
        self,
        rtsp_url: str,
        fps: float = 2.0,
        width: int = 640,
        height: int = 480,
        transport: str = "tcp",
        backend: str = "opencv",
    ):
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.width = width
        self.height = height
        self.transport = transport.lower()
        self.backend = backend.lower()
        
        self._running = False
        self._thread = None
        self._frame_queue = queue.Queue(maxsize=1)
        self._capture = None
        self._av_container = None
        self._stderr_fd = None
        self._devnull_fd = None
    
    def start(self):
        """Start capture thread."""
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
    
    def stop(self):
        """Stop capture thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._capture:
            self._capture.release()
    
    def get_frame(self, timeout: float = 1.0) -> Optional[bytes]:
        """Get next frame (JPEG bytes)."""
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _restore_stderr(self):
        """Restore stderr after suppressing H.264 errors."""
        import os
        try:
            if self._stderr_fd is not None:
                os.dup2(self._stderr_fd, 2)
                os.close(self._stderr_fd)
                self._stderr_fd = None
            if self._devnull_fd is not None:
                os.close(self._devnull_fd)
                self._devnull_fd = None
        except OSError:
            pass
    
    def _suppress_stderr(self):
        """Suppress stderr to hide H.264 decode errors."""
        import os
        try:
            if self._stderr_fd is None:
                self._stderr_fd = os.dup(2)
                self._devnull_fd = os.open(os.devnull, os.O_WRONLY)
                os.dup2(self._devnull_fd, 2)
        except OSError:
            pass
    
    def _capture_loop(self):
        """Background capture loop - supports multiple backends."""
        if self.backend == "pyav":
            self._capture_loop_pyav()
        elif self.backend == "gstreamer":
            self._capture_loop_gstreamer()
        else:
            self._capture_loop_opencv()
    
    def _capture_loop_pyav(self):
        """PyAV backend - OPTIMIZED with hardware decoding and threading."""
        try:
            import av
            import numpy as np
        except ImportError:
            print("❌ PyAV backend requires 'av' library. Falling back to OpenCV...")
            self._capture_loop_opencv()
            return
        
        options = {
            'rtsp_transport': self.transport,
            'fflags': 'nobuffer+discardcorrupt',
            'flags': 'low_delay',
            'max_delay': '0',
            'analyzeduration': '0',
            'probesize': '32768',
            'sync': 'ext',
        }
        
        if self.transport == 'udp':
            options['buffer_size'] = '16384'
            options['reorder_queue_size'] = '0'
        else:
            options['buffer_size'] = '32768'
        
        transport_label = "UDP" if self.transport == "udp" else "TCP"
        print(f"🎬 Opening RTSP with PyAV [{transport_label}]...")
        
        try:
            self._av_container = av.open(self.rtsp_url, options=options)
            stream = self._av_container.streams.video[0]
            stream.thread_type = 'AUTO'
            stream.thread_count = 0
            print(f"✅ PyAV connected [{transport_label}]")
        except Exception as e:
            print(f"❌ PyAV failed: {e}. Falling back to OpenCV...")
            self._capture_loop_opencv()
            return
        
        try:
            import cv2
            has_cv2 = True
        except ImportError:
            has_cv2 = False
        
        capture_fps = max(1.0, float(self.fps))
        interval = 1.0 / capture_fps
        last_capture = 0
        frame_count = 0
        
        try:
            for packet in self._av_container.demux(video=0):
                if not self._running:
                    break
                
                for frame in packet.decode():
                    if not self._running:
                        break
                    
                    now = time.time()
                    if now - last_capture < interval:
                        continue
                    
                    img = frame.to_ndarray(format='bgr24')
                    
                    h, w = img.shape[:2]
                    if has_cv2 and (w != self.width or h != self.height):
                        img = cv2.resize(img, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
                    
                    try:
                        self._frame_queue.put_nowait(img)
                    except queue.Full:
                        try:
                            self._frame_queue.get_nowait()
                            self._frame_queue.put_nowait(img)
                        except Exception:
                            pass
                    
                    last_capture = now
                    frame_count += 1
                    
                    if frame_count % 30 == 0:
                        ts = time.strftime("%H:%M:%S", time.localtime())
                        print(f"📷 [{ts}] PyAV F#{frame_count}")
                        
        except Exception as e:
            print(f"⚠️ PyAV capture error: {e}")
        finally:
            if self._av_container:
                self._av_container.close()
            print("🛑 PyAV capture stopped")
    
    def _capture_loop_gstreamer(self):
        """GStreamer backend via OpenCV."""
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available")
            return
        
        transport_opt = "protocols=tcp" if self.transport == "tcp" else "protocols=udp"
        gst_pipeline = (
            f"rtspsrc location={self.rtsp_url} latency=0 {transport_opt} ! "
            f"rtph264depay ! h264parse ! avdec_h264 ! "
            f"videoconvert ! videoscale ! "
            f"video/x-raw,format=BGR,width={self.width},height={self.height} ! "
            f"appsink drop=true max-buffers=1 sync=false"
        )
        
        print(f"🎬 Opening RTSP with GStreamer...")
        self._capture = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)
        
        if not self._capture.isOpened():
            print("❌ GStreamer failed. Falling back to OpenCV/ffmpeg...")
            self._capture_loop_opencv()
            return
        
        print(f"✅ GStreamer connected")
        
        capture_fps = max(1.0, float(self.fps))
        interval = 1.0 / capture_fps
        last_capture = 0
        frame_count = 0
        
        while self._running:
            now = time.time()
            if now - last_capture < interval:
                time.sleep(0.002)
                continue
            
            ret, frame = self._capture.read()
            if not ret:
                time.sleep(0.01)
                continue
            
            try:
                self._frame_queue.put_nowait(frame.copy())
            except queue.Full:
                try:
                    self._frame_queue.get_nowait()
                    self._frame_queue.put_nowait(frame.copy())
                except Exception:
                    pass
            
            last_capture = now
            frame_count += 1
            
            if frame_count % 30 == 0:
                print(f"📷 GStreamer captured {frame_count} frames")
        
        self._capture.release()
        print("🛑 GStreamer capture stopped")
    
    def _capture_loop_opencv(self):
        """OpenCV/ffmpeg backend - default, most compatible."""
        try:
            import cv2
        except ImportError:
            logger.error("OpenCV not available")
            return
        
        import os
        
        if self.transport == "udp":
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;udp|buffer_size;32768|max_delay;0|fflags;+nobuffer+discardcorrupt|flags;low_delay"
            )
        else:
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                "rtsp_transport;tcp|buffer_size;65536|max_delay;0|fflags;+nobuffer+discardcorrupt|flags;low_delay"
            )
        os.environ["OPENCV_LOG_LEVEL"] = "SILENT"
        
        self._suppress_stderr()
        self._capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self._capture.isOpened():
            self._restore_stderr()
            print(f"❌ Failed to open RTSP stream: {self.rtsp_url}")
            return
        
        self._restore_stderr()
        print(f"✅ OpenCV/ffmpeg connected")
        
        # Flush buffer
        self._suppress_stderr()
        for _ in range(30):
            self._capture.grab()
        self._restore_stderr()
        
        capture_fps = max(1.0, float(self.fps))
        interval = 1.0 / capture_fps
        
        self._suppress_stderr()
        last_capture = 0
        frame_count = 0
        reconnect_attempts = 0
        
        while self._running:
            now = time.time()
            if now - last_capture < interval:
                time.sleep(0.002)
                continue
            
            ret, frame = self._capture.read()
            
            if not ret:
                reconnect_attempts += 1
                if reconnect_attempts > 3:
                    self._restore_stderr()
                    print("⚠️ RTSP reconnecting...")
                    self._suppress_stderr()
                    time.sleep(0.5)
                    self._capture.release()
                    self._capture = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
                    self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    reconnect_attempts = 0
                continue
            
            reconnect_attempts = 0
            
            h, w = frame.shape[:2]
            if w != self.width or h != self.height:
                frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
            
            try:
                self._frame_queue.put_nowait(frame.copy())
            except queue.Full:
                try:
                    self._frame_queue.get_nowait()
                    self._frame_queue.put_nowait(frame.copy())
                except Exception:
                    pass
            
            last_capture = now
            frame_count += 1
            
            if frame_count % 30 == 0:
                self._restore_stderr()
                print(f"📷 Captured {frame_count} frames")
                self._suppress_stderr()
        
        self._restore_stderr()
        self._capture.release()
        print("🛑 Capture stopped")
