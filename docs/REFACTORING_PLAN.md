# 🔧 Refactoring Plan: Tracking & Analysis Optimization

**Status:** Planning  
**Priority:** High  
**[← Back to Documentation](README.md)**

---

## 📋 Executive Summary

Plan refaktoryzacji systemu analizy ruchu i trackingu w celu:
1. Poprawy dokładności śledzenia obiektów
2. Optymalizacji wydajności DSL analysis
3. Lepszej izolacji procesów
4. Redukcji false positives

---

## 🔍 Current Issues Analysis

### 1. Tracking Accuracy Issues

| Problem | Impact | Priority |
|---------|--------|----------|
| Blob ID flickering | Obiekty tracą ID między klatkami | HIGH |
| False positives from static objects | Monitory, obrazy wykrywane jako ruch | HIGH |
| Poor velocity estimation | Kierunek ruchu nieprecyzyjny | MEDIUM |
| Edge detection inaccurate | ENTER/EXIT events błędne | MEDIUM |

### 2. Performance Bottlenecks

| Component | Current | Target | Issue |
|-----------|---------|--------|-------|
| Background subtraction | 5-15ms | 3-5ms | CPU-bound |
| Blob tracking | ~0.1ms | ~0.1ms | OK |
| Thumbnail generation | ~1ms | ~0.5ms | Redundant resizing |
| Frame capture | ~2ms | ~1ms | Queue overhead |

### 3. Architecture Issues

| Issue | Description |
|-------|-------------|
| Tight coupling | LiveNarrator zbyt duży (2200+ lines) |
| Process communication | Brak shared state między procesami |
| Memory usage | Duplicate frames in both processes |

---

## 🏗️ Refactoring Tasks

### Phase 1: Tracking Accuracy (Priority: HIGH)

#### Task 1.1: Improve Blob Matching Algorithm

**Current:**
```python
def _track_blobs(self, current_blobs, prev_blobs):
    # Simple nearest-neighbor matching
    for curr in current_blobs:
        for prev in prev_blobs:
            if distance(curr, prev) < threshold:
                curr.id = prev.id
```

**Proposed:**
```python
def _track_blobs(self, current_blobs, prev_blobs):
    # Hungarian algorithm for optimal matching
    # + Kalman filter for velocity prediction
    # + Appearance features (color histogram)
    
    cost_matrix = build_cost_matrix(current_blobs, prev_blobs)
    assignments = hungarian_algorithm(cost_matrix)
    
    for curr_idx, prev_idx in assignments:
        if cost_matrix[curr_idx, prev_idx] < threshold:
            current_blobs[curr_idx].id = prev_blobs[prev_idx].id
            # Update Kalman filter
            update_kalman(current_blobs[curr_idx])
```

**Files to modify:**
- `streamware/frame_diff_dsl.py` - `_track_blobs()` method

#### Task 1.2: Add Kalman Filter for Prediction

**New class:**
```python
class BlobTracker:
    """Kalman filter-based blob tracker."""
    
    def __init__(self, blob_id: int):
        self.id = blob_id
        self.kalman = cv2.KalmanFilter(4, 2)  # state: x,y,vx,vy
        self._init_kalman()
        self.age = 0
        self.hits = 0
        self.misses = 0
    
    def predict(self) -> Point2D:
        """Predict next position."""
        prediction = self.kalman.predict()
        return Point2D(prediction[0], prediction[1])
    
    def update(self, measurement: Point2D):
        """Update with actual measurement."""
        self.kalman.correct(np.array([[measurement.x], [measurement.y]]))
        self.hits += 1
        self.misses = 0
    
    def mark_missed(self):
        """Mark frame without detection."""
        self.misses += 1
```

**Files to create:**
- `streamware/blob_tracker.py` - New Kalman-based tracker

#### Task 1.3: Filter Static Objects

**Current issues:**
- Monitors detected as motion
- Pictures on walls
- Reflections

**Proposed solution:**
```python
class StaticObjectFilter:
    """Filter out consistently static regions."""
    
    def __init__(self, history_frames: int = 30):
        self.history = deque(maxlen=history_frames)
        self.static_mask = None
    
    def update(self, motion_mask: np.ndarray):
        self.history.append(motion_mask)
        if len(self.history) >= 10:
            # Regions that are "moving" in >80% of frames are static
            static = np.mean(self.history, axis=0) > 0.8
            self.static_mask = static
    
    def filter(self, blobs: List[MotionBlob]) -> List[MotionBlob]:
        if self.static_mask is None:
            return blobs
        return [b for b in blobs if not self._is_static(b)]
```

**Files to modify:**
- `streamware/frame_diff_dsl.py` - Add `StaticObjectFilter`

---

### Phase 2: Performance Optimization (Priority: MEDIUM)

#### Task 2.1: GPU-Accelerated Background Subtraction

**Current:** CPU-based `cv2.absdiff()`

**Proposed:**
```python
class GPUBackgroundSubtractor:
    """CUDA-accelerated background subtraction."""
    
    def __init__(self):
        if cv2.cuda.getCudaEnabledDeviceCount() > 0:
            self.use_gpu = True
            self.bg_subtractor = cv2.cuda.createBackgroundSubtractorMOG2()
        else:
            self.use_gpu = False
            self.bg_subtractor = cv2.createBackgroundSubtractorMOG2()
    
    def apply(self, frame: np.ndarray) -> np.ndarray:
        if self.use_gpu:
            gpu_frame = cv2.cuda_GpuMat()
            gpu_frame.upload(frame)
            gpu_mask = self.bg_subtractor.apply(gpu_frame)
            return gpu_mask.download()
        return self.bg_subtractor.apply(frame)
```

**Expected improvement:** 5-15ms → 2-5ms

#### Task 2.2: Optimize Frame Pipeline

**Current flow:**
```
FastCapture → Save to disk → Read from disk → Analyze
```

**Proposed flow:**
```
FastCapture → Shared memory → Analyze (zero-copy)
```

```python
class SharedFrameBuffer:
    """Zero-copy frame sharing between processes."""
    
    def __init__(self, width: int, height: int, buffer_size: int = 5):
        self.shape = (height, width, 3)
        self.shm = shared_memory.SharedMemory(
            create=True,
            size=np.prod(self.shape) * buffer_size
        )
        self.frames = np.ndarray(
            (buffer_size, *self.shape),
            dtype=np.uint8,
            buffer=self.shm.buf
        )
```

#### Task 2.3: Batch Processing for Multiple Cameras

```python
class MultiCameraAnalyzer:
    """Process multiple camera streams in parallel."""
    
    def __init__(self, camera_urls: List[str]):
        self.analyzers = {
            url: FrameDiffAnalyzer() for url in camera_urls
        }
        self.executor = ThreadPoolExecutor(max_workers=len(camera_urls))
    
    async def analyze_all(self, frames: Dict[str, Path]) -> Dict[str, FrameDelta]:
        futures = {
            url: self.executor.submit(self.analyzers[url].analyze, path)
            for url, path in frames.items()
        }
        return {url: f.result() for url, f in futures.items()}
```

---

### Phase 3: Architecture Refactoring (Priority: LOW)

#### Task 3.1: Split LiveNarratorComponent

**Current:** 2200+ lines monolith

**Proposed structure:**
```
streamware/
├── narrator/
│   ├── __init__.py
│   ├── core.py              # Main orchestrator (300 lines)
│   ├── capture.py           # Frame capture logic (200 lines)
│   ├── analysis.py          # DSL + LLM analysis (400 lines)
│   ├── streaming.py         # WebSocket streaming (200 lines)
│   ├── output.py            # TTS, webhooks, exports (300 lines)
│   └── config.py            # Configuration handling (100 lines)
```

#### Task 3.2: Event-Driven Architecture

```python
class NarratorEventBus:
    """Pub/sub for narrator events."""
    
    def __init__(self):
        self.subscribers = defaultdict(list)
    
    def subscribe(self, event_type: str, handler: Callable):
        self.subscribers[event_type].append(handler)
    
    def publish(self, event_type: str, data: Any):
        for handler in self.subscribers[event_type]:
            handler(data)

# Events:
# - frame_captured
# - motion_detected
# - blob_entered
# - blob_exited
# - llm_response
# - significant_change
```

#### Task 3.3: Unified Configuration

```python
@dataclass
class NarratorConfig:
    """Centralized configuration."""
    
    # Capture
    rtsp_url: str
    capture_fps: float = 5.0
    use_gpu: bool = True
    
    # Analysis
    motion_threshold: int = 25
    min_blob_area: int = 500
    filter_static: bool = True
    
    # Tracking
    use_kalman: bool = True
    max_blob_age: int = 30
    
    # LLM
    model: str = "llava:7b"
    async_llm: bool = True
    
    # Output
    realtime: bool = False
    tts: bool = False
    
    @classmethod
    def from_uri(cls, uri: str) -> 'NarratorConfig':
        """Parse from component URI."""
        ...
```

---

## 📅 Implementation Schedule

| Phase | Tasks | Estimated Time | Dependencies |
|-------|-------|----------------|--------------|
| **Phase 1** | Tracking accuracy | 2-3 days | None |
| 1.1 | Blob matching | 4h | - |
| 1.2 | Kalman filter | 4h | 1.1 |
| 1.3 | Static filter | 2h | - |
| **Phase 2** | Performance | 2-3 days | Phase 1 |
| 2.1 | GPU background | 4h | - |
| 2.2 | Shared memory | 6h | - |
| 2.3 | Multi-camera | 4h | 2.2 |
| **Phase 3** | Architecture | 3-4 days | Phase 2 |
| 3.1 | Split narrator | 8h | - |
| 3.2 | Event bus | 4h | 3.1 |
| 3.3 | Config | 2h | 3.1 |

---

## ✅ Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Blob ID stability | ~60% | >95% |
| False positive rate | ~30% | <5% |
| DSL analysis time | 10-15ms | 5-8ms |
| Memory usage | ~500MB | ~300MB |
| Code maintainability | Low | High |

---

## 🔗 Related Documentation

- [Motion Analysis](MOTION_ANALYSIS.md)
- [Performance](PERFORMANCE.md)
- [Architecture](ARCHITECTURE.md)
- [Back to Documentation](README.md)
