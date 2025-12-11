"""
DSL Streamer Process

Separate process for real-time DSL streaming.
Runs completely independently from LLM processing.

Architecture:
  [Main Process]           [DSL Streamer Process]
       │                          │
       │                    ┌─────┴─────┐
       │                    │ FastCapture│
       │                    │ (10+ FPS)  │
       │                    └─────┬─────┘
       │                          │
       │                    ┌─────┴─────┐
       │                    │DSL Analysis│
       │                    │ (~10ms)    │
       │                    └─────┬─────┘
       │                          │
       │                    ┌─────┴─────┐
       │                    │ WebSocket │
       │                    │ :8766     │
       │                    └───────────┘
       │                          │
       └──── LLM (async) ─────────┘

Usage:
    from streamware.dsl_streamer_process import start_dsl_streamer, stop_dsl_streamer
    
    # Start in separate process
    process = start_dsl_streamer(rtsp_url, fps=10)
    
    # ... main process does LLM work ...
    
    # Stop when done
    stop_dsl_streamer(process)
"""

import multiprocessing as mp
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _run_dsl_streamer(
    rtsp_url: str,
    fps: float,
    ws_port: int,
    http_port: int,
    stop_event: mp.Event,
):
    """
    Run DSL streamer in separate process.
    
    This function runs in its own process, completely isolated from LLM.
    """
    import signal
    
    # Ignore SIGINT in child process (parent handles it)
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    
    print(f"🎬 DSL Streamer started (PID={mp.current_process().pid}, {fps} FPS)", flush=True)
    
    try:
        # Import here to avoid issues with multiprocessing
        from .fast_capture import FastCapture
        from .frame_diff_dsl import FrameDiffAnalyzer
        from .realtime_dsl_server import RealtimeDSLServer
        
        # Start WebSocket server
        server = RealtimeDSLServer(port=ws_port, http_port=http_port)
        server.start()
        print(f"🌐 DSL Viewer: http://localhost:{http_port}", flush=True)
        
        # Use separate directory for DSL streamer to avoid conflicts with main process
        import os
        dsl_frame_dir = "/dev/shm/streamware_dsl"
        os.makedirs(dsl_frame_dir, exist_ok=True)
        
        # Start FastCapture with separate directory
        capture = FastCapture(
            rtsp_url=rtsp_url,
            fps=min(30, fps),
            use_gpu=True,
            buffer_size=10,
            output_dir=dsl_frame_dir,  # Separate from main process
        )
        capture.start()
        time.sleep(0.5)  # Wait for first frame
        
        # DSL Analyzer
        analyzer = FrameDiffAnalyzer()
        
        frame_num = 0
        interval = 1.0 / fps
        
        print(f"📹 DSL streaming at {fps} FPS (interval={interval:.2f}s)", flush=True)
        
        while not stop_event.is_set():
            try:
                # Get frame
                frame_info = capture.get_frame(timeout=2.0)
                if not frame_info:
                    time.sleep(0.1)
                    continue
                
                frame_num += 1
                frame_path = frame_info.path
                
                # Analyze frame
                delta = analyzer.analyze(frame_path)
                
                # Stream to WebSocket
                bg = delta.background_base64 if hasattr(delta, 'background_base64') else ""
                server.add_frame(delta, bg)
                
                # Log occasionally
                if frame_num % 20 == 0:
                    print(f"   📊 DSL F{frame_num}: {delta.motion_percent:.1f}% motion, {len(delta.blobs)} blobs", flush=True)
                
                # Maintain target FPS
                time.sleep(max(0.02, interval))
                
            except Exception as e:
                logger.debug(f"DSL frame error: {e}")
                time.sleep(0.1)
        
        # Cleanup
        capture.stop()
        server.stop()
        print("🛑 DSL Streamer stopped", flush=True)
        
    except Exception as e:
        print(f"❌ DSL Streamer error: {e}", flush=True)


class DSLStreamerProcess:
    """Manager for DSL streamer process."""
    
    def __init__(
        self,
        rtsp_url: str,
        fps: float = 10,
        ws_port: int = 8765,
        http_port: int = 8766,
    ):
        self.rtsp_url = rtsp_url
        self.fps = fps
        self.ws_port = ws_port
        self.http_port = http_port
        
        self._process: Optional[mp.Process] = None
        self._stop_event: Optional[mp.Event] = None
    
    def start(self) -> bool:
        """Start DSL streamer in separate process."""
        if self._process and self._process.is_alive():
            return True
        
        self._stop_event = mp.Event()
        self._process = mp.Process(
            target=_run_dsl_streamer,
            args=(
                self.rtsp_url,
                self.fps,
                self.ws_port,
                self.http_port,
                self._stop_event,
            ),
            daemon=True,
        )
        self._process.start()
        
        # Wait for server to start
        time.sleep(1.0)
        return self._process.is_alive()
    
    def stop(self):
        """Stop DSL streamer process."""
        if self._stop_event:
            self._stop_event.set()
        
        if self._process:
            self._process.join(timeout=2.0)
            if self._process.is_alive():
                self._process.terminate()
            self._process = None
    
    def is_alive(self) -> bool:
        """Check if process is running."""
        return self._process is not None and self._process.is_alive()


# Global instance
_streamer: Optional[DSLStreamerProcess] = None


def start_dsl_streamer(
    rtsp_url: str,
    fps: float = 10,
    ws_port: int = 8765,
    http_port: int = 8766,
) -> DSLStreamerProcess:
    """Start DSL streamer in separate process."""
    global _streamer
    
    if _streamer and _streamer.is_alive():
        return _streamer
    
    _streamer = DSLStreamerProcess(
        rtsp_url=rtsp_url,
        fps=fps,
        ws_port=ws_port,
        http_port=http_port,
    )
    _streamer.start()
    return _streamer


def stop_dsl_streamer():
    """Stop DSL streamer process."""
    global _streamer
    if _streamer:
        _streamer.stop()
        _streamer = None
