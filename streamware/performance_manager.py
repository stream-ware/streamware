"""
Performance Manager - Dynamic Resource Optimization

Automatically adjusts processing based on:
- Hardware capabilities (CPU, RAM, GPU)
- Current system load
- Processing times from previous frames
- Network latency

Features:
- Auto-selects optimal models based on hardware
- Parallel frame capture and processing
- Adaptive intervals based on activity
- Resolution scaling based on performance
- Process pooling for CPU-bound tasks
"""

import logging
import os
import platform
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Thread, Event
from queue import Queue, Empty
from typing import Dict, List, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

logger = logging.getLogger(__name__)


class HardwareProfile(Enum):
    """Hardware capability profiles."""
    LOW = "low"           # Raspberry Pi, old laptops
    MEDIUM = "medium"     # Standard laptops, desktops
    HIGH = "high"         # Gaming PCs, workstations
    GPU = "gpu"           # NVIDIA GPU available


@dataclass
class HardwareInfo:
    """Detected hardware information."""
    cpu_count: int = 1
    cpu_freq_mhz: float = 0
    ram_gb: float = 0
    has_gpu: bool = False
    gpu_name: str = ""
    gpu_vram_gb: float = 0
    profile: HardwareProfile = HardwareProfile.MEDIUM
    
    # Benchmark results
    cpu_benchmark_ms: float = 0
    opencv_benchmark_ms: float = 0
    
    def __str__(self):
        gpu_info = f", GPU: {self.gpu_name} ({self.gpu_vram_gb:.1f}GB)" if self.has_gpu else ""
        return f"CPU: {self.cpu_count} cores @ {self.cpu_freq_mhz:.0f}MHz, RAM: {self.ram_gb:.1f}GB{gpu_info}, Profile: {self.profile.value}"


@dataclass
class PerformanceConfig:
    """Configuration optimized for detected hardware."""
    # Model selection
    vision_model: str = "llava:7b"
    guarder_model: str = "gemma:2b"
    use_vision_model: bool = True
    
    # Processing settings
    capture_resolution: Tuple[int, int] = (640, 480)
    llm_image_size: int = 512
    jpeg_quality: int = 75
    
    # Timing
    base_interval: float = 3.0
    min_interval: float = 1.0
    max_interval: float = 10.0
    
    # Parallelism
    use_parallel_capture: bool = True
    max_workers: int = 2
    
    # Features
    use_hog_detection: bool = True
    use_ssim_cache: bool = True
    use_motion_gating: bool = True
    
    # Thresholds
    motion_threshold: float = 0.5
    ssim_threshold: float = 0.95


def detect_hardware() -> HardwareInfo:
    """Detect system hardware capabilities."""
    info = HardwareInfo()
    
    # CPU info
    info.cpu_count = os.cpu_count() or 1
    
    try:
        # Try to get CPU frequency
        if platform.system() == "Linux":
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if "cpu MHz" in line:
                        info.cpu_freq_mhz = float(line.split(":")[1].strip())
                        break
    except Exception:
        info.cpu_freq_mhz = 2000  # Assume 2GHz
    
    # RAM info
    try:
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if "MemTotal" in line:
                        kb = int(line.split()[1])
                        info.ram_gb = kb / 1024 / 1024
                        break
        else:
            import psutil
            info.ram_gb = psutil.virtual_memory().total / 1024 / 1024 / 1024
    except Exception:
        info.ram_gb = 4  # Assume 4GB
    
    # GPU detection (NVIDIA)
    try:
        import subprocess
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            if len(parts) >= 2:
                info.has_gpu = True
                info.gpu_name = parts[0].strip()
                info.gpu_vram_gb = float(parts[1].strip()) / 1024
    except Exception:
        pass
    
    # Run benchmarks
    info.cpu_benchmark_ms, info.opencv_benchmark_ms = _run_benchmarks()
    
    # Determine profile
    if info.has_gpu and info.gpu_vram_gb >= 4:
        info.profile = HardwareProfile.GPU
    elif info.cpu_count >= 8 and info.ram_gb >= 16:
        info.profile = HardwareProfile.HIGH
    elif info.cpu_count >= 4 and info.ram_gb >= 8:
        info.profile = HardwareProfile.MEDIUM
    else:
        info.profile = HardwareProfile.LOW
    
    return info


def _run_benchmarks() -> Tuple[float, float]:
    """Run quick benchmarks to assess actual performance."""
    # CPU benchmark
    start = time.perf_counter()
    total = 0
    for i in range(500000):
        total += i
    cpu_time = (time.perf_counter() - start) * 1000
    
    # OpenCV benchmark
    opencv_time = 0
    try:
        import cv2
        import numpy as np
        
        img = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        start = time.perf_counter()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        _ = cv2.Canny(blur, 50, 150)
        opencv_time = (time.perf_counter() - start) * 1000
    except ImportError:
        opencv_time = 100  # Assume slow if no OpenCV
    
    return cpu_time, opencv_time


def get_optimal_config(hardware: HardwareInfo) -> PerformanceConfig:
    """Get optimal configuration for detected hardware."""
    config = PerformanceConfig()
    
    if hardware.profile == HardwareProfile.GPU:
        # High-end with GPU
        config.vision_model = "llava:13b"
        config.capture_resolution = (1280, 720)
        config.llm_image_size = 768
        config.jpeg_quality = 85
        config.base_interval = 2.0
        config.min_interval = 0.5
        config.max_workers = 4
        
    elif hardware.profile == HardwareProfile.HIGH:
        # High-end CPU
        config.vision_model = "llava:7b"
        config.capture_resolution = (960, 540)
        config.llm_image_size = 512
        config.jpeg_quality = 75
        config.base_interval = 3.0
        config.min_interval = 1.0
        config.max_workers = 3
        
    elif hardware.profile == HardwareProfile.MEDIUM:
        # Medium hardware
        config.vision_model = "llava:7b"
        config.capture_resolution = (640, 480)
        config.llm_image_size = 384
        config.jpeg_quality = 70
        config.base_interval = 4.0
        config.min_interval = 2.0
        config.max_workers = 2
        
    else:  # LOW
        # Low-end hardware
        config.vision_model = "moondream"
        config.guarder_model = "qwen2.5:0.5b"
        config.capture_resolution = (480, 360)
        config.llm_image_size = 256
        config.jpeg_quality = 60
        config.base_interval = 6.0
        config.min_interval = 3.0
        config.max_workers = 1
        config.use_hog_detection = False  # Too slow on low-end
    
    # Adjust based on actual benchmark results
    if hardware.cpu_benchmark_ms > 100:  # Slow CPU
        config.base_interval *= 1.5
        config.use_hog_detection = False
    
    if hardware.opencv_benchmark_ms > 10:  # Slow OpenCV
        config.use_ssim_cache = False
    
    return config


class FrameBuffer:
    """Async frame capture buffer for parallel processing."""
    
    def __init__(self, capture_func: Callable, buffer_size: int = 3):
        self.capture_func = capture_func
        self.buffer_size = buffer_size
        self.queue: Queue = Queue(maxsize=buffer_size)
        self.stop_event = Event()
        self.capture_thread: Optional[Thread] = None
        self._frame_num = 0
    
    def start(self):
        """Start async capture thread."""
        self.stop_event.clear()
        self.capture_thread = Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def stop(self):
        """Stop capture thread."""
        self.stop_event.set()
        if self.capture_thread:
            self.capture_thread.join(timeout=2)
    
    def _capture_loop(self):
        """Background capture loop."""
        while not self.stop_event.is_set():
            try:
                self._frame_num += 1
                frame_path = self.capture_func(self._frame_num)
                if frame_path:
                    self.queue.put((self._frame_num, frame_path, time.time()), timeout=1)
            except Exception as e:
                logger.debug(f"Capture error: {e}")
                time.sleep(0.5)
    
    def get_frame(self, timeout: float = 5.0) -> Optional[Tuple[int, Path, float]]:
        """Get next frame from buffer."""
        try:
            return self.queue.get(timeout=timeout)
        except Empty:
            return None


@dataclass
class PerformanceStats:
    """Track processing performance over time."""
    capture_times: List[float] = field(default_factory=list)
    detect_times: List[float] = field(default_factory=list)
    llm_times: List[float] = field(default_factory=list)
    guarder_times: List[float] = field(default_factory=list)
    
    frames_processed: int = 0
    frames_skipped: int = 0
    
    def add_timing(self, stage: str, time_ms: float):
        """Record timing for a stage."""
        times_map = {
            "capture": self.capture_times,
            "detect": self.detect_times,
            "llm": self.llm_times,
            "guarder": self.guarder_times,
        }
        if stage in times_map:
            times_map[stage].append(time_ms)
            # Keep only last 20 samples
            if len(times_map[stage]) > 20:
                times_map[stage] = times_map[stage][-20:]
    
    def get_avg(self, stage: str) -> float:
        """Get average time for a stage."""
        times_map = {
            "capture": self.capture_times,
            "detect": self.detect_times,
            "llm": self.llm_times,
            "guarder": self.guarder_times,
        }
        times = times_map.get(stage, [])
        return sum(times) / len(times) if times else 0
    
    def get_recommended_interval(self) -> float:
        """Calculate recommended interval based on actual performance."""
        # Total processing time
        total = self.get_avg("capture") + self.get_avg("detect") + self.get_avg("llm") + self.get_avg("guarder")
        
        # Add 20% buffer
        recommended = (total / 1000) * 1.2
        
        # Clamp to reasonable range
        return max(1.0, min(15.0, recommended))
    
    def get_skip_rate(self) -> float:
        """Get frame skip rate."""
        total = self.frames_processed + self.frames_skipped
        if total == 0:
            return 0
        return self.frames_skipped / total
    
    def summary(self) -> str:
        """Get performance summary."""
        return (
            f"Frames: {self.frames_processed} processed, {self.frames_skipped} skipped ({self.get_skip_rate():.0%})\n"
            f"Avg times: capture={self.get_avg('capture'):.0f}ms, detect={self.get_avg('detect'):.0f}ms, "
            f"llm={self.get_avg('llm'):.0f}ms, guarder={self.get_avg('guarder'):.0f}ms\n"
            f"Recommended interval: {self.get_recommended_interval():.1f}s"
        )


class PerformanceManager:
    """Central performance management."""
    
    def __init__(self):
        self.hardware: Optional[HardwareInfo] = None
        self.config: Optional[PerformanceConfig] = None
        self.stats = PerformanceStats()
        self._executor: Optional[ThreadPoolExecutor] = None
    
    def initialize(self) -> PerformanceConfig:
        """Detect hardware and get optimal config."""
        print("🔍 Detecting hardware capabilities...", flush=True)
        self.hardware = detect_hardware()
        print(f"   {self.hardware}", flush=True)
        
        self.config = get_optimal_config(self.hardware)
        print(f"   Recommended model: {self.config.vision_model}", flush=True)
        print(f"   Recommended interval: {self.config.base_interval}s", flush=True)
        print(f"   Resolution: {self.config.capture_resolution}", flush=True)
        
        # Initialize thread pool
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        return self.config
    
    def should_process_frame(self, motion_pct: float, time_since_last: float) -> Tuple[bool, str]:
        """Decide if frame should be processed based on performance."""
        # If system is slow (high avg times), be more selective
        avg_total = (
            self.stats.get_avg("capture") +
            self.stats.get_avg("llm") +
            self.stats.get_avg("guarder")
        )
        
        if avg_total > 10000:  # >10s total processing
            # System is slow, skip low-motion frames
            if motion_pct < 2.0:
                return False, "slow_system_low_motion"
        
        # If skip rate is too high, process more frames
        if self.stats.get_skip_rate() > 0.8:
            return True, "high_skip_rate"
        
        # Default motion-based decision
        if motion_pct < self.config.motion_threshold:
            return False, f"low_motion_{motion_pct:.1f}%"
        
        return True, "process"
    
    def get_adaptive_interval(self, motion_pct: float) -> float:
        """Get adaptive interval based on motion and performance."""
        base = self.config.base_interval
        
        # Adjust based on motion
        if motion_pct > 20:
            base *= 0.5  # High motion - faster
        elif motion_pct < 1:
            base *= 2.0  # Low motion - slower
        
        # Adjust based on actual performance
        recommended = self.stats.get_recommended_interval()
        if recommended > base * 1.5:
            base = recommended  # System is slower than expected
        
        return max(self.config.min_interval, min(self.config.max_interval, base))
    
    def submit_task(self, func: Callable, *args) -> None:
        """Submit task to thread pool."""
        if self._executor:
            self._executor.submit(func, *args)
    
    def shutdown(self):
        """Shutdown thread pool."""
        if self._executor:
            self._executor.shutdown(wait=False)
    
    def get_summary(self) -> str:
        """Get performance summary."""
        return self.stats.summary()


# Global instance
_manager: Optional[PerformanceManager] = None


def get_performance_manager() -> PerformanceManager:
    """Get or create performance manager."""
    global _manager
    if _manager is None:
        _manager = PerformanceManager()
    return _manager


def auto_configure() -> PerformanceConfig:
    """Auto-configure based on hardware detection."""
    manager = get_performance_manager()
    return manager.initialize()
