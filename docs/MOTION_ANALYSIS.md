# 🎯 Motion Analysis

DSL-based motion tracking and blob detection.

**[← Back to Documentation](README.md)**

---

## Overview

StreamWare uses a custom DSL (Domain Specific Language) for efficient motion analysis. The system detects, tracks, and classifies moving objects using OpenCV.

## How It Works

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Frame N   │    │  Frame N-1  │    │   Motion    │
│   (current) │ -> │  (previous) │ -> │    Mask     │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Events    │ <- │   Tracking  │ <- │   Contours  │
│ ENTER/EXIT  │    │   (IDs)     │    │   (Blobs)   │
└─────────────┘    └─────────────┘    └─────────────┘
```

## DSL Data Structure

### FrameDelta

```python
@dataclass
class FrameDelta:
    frame_num: int
    timestamp: str
    motion_percent: float      # 0-100%
    blobs: List[MotionBlob]    # Detected objects
    events: List[MotionEvent]  # ENTER/EXIT/MOVE
```

### MotionBlob

```python
@dataclass
class MotionBlob:
    id: int                    # Unique tracking ID
    center: Point              # (x, y) normalized 0-1
    size: Point                # (width, height) normalized
    velocity: Point            # Movement vector
    edge: str                  # "top", "bottom", "left", "right", ""
```

### MotionEvent

```python
@dataclass
class MotionEvent:
    type: EventType            # ENTER, EXIT, APPEAR, DISAPPEAR
    blob_id: int
    direction: Direction       # UP, DOWN, LEFT, RIGHT
```

## Detection Pipeline

### 1. Frame Capture
```python
frame = fast_capture.get_frame()  # ~2ms
```

### 2. Preprocessing
```python
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)  # ~0.2ms
blurred = cv2.GaussianBlur(gray, (5, 5), 0)     # ~0.3ms
```

### 3. Background Subtraction
```python
diff = cv2.absdiff(prev_gray, gray)             # ~5-15ms
mask = cv2.threshold(diff, threshold, 255)
```

### 4. Contour Detection
```python
contours = cv2.findContours(mask, ...)          # ~0.2ms
blobs = filter_contours(contours, min_area)
```

### 5. Tracking
```python
for blob in blobs:
    matched_id = find_nearest_previous(blob)    # ~0.1ms
    update_velocity(blob, matched_id)
```

## Configuration

### Detection Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `motion_threshold` | 25 | Pixel diff threshold |
| `min_blob_area` | 500 | Minimum contour area |
| `max_blobs` | 10 | Maximum tracked objects |
| `blur_size` | 5 | Gaussian blur kernel |

### Filtering Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_velocity` | 0.01 | Filter static objects |
| `max_blob_size_ratio` | 0.7 | Filter background blobs |
| `min_moving_frames` | 2 | Persistence threshold |
| `filter_static` | True | Enable static filtering |

## Events

### Event Types

| Type | Trigger |
|------|---------|
| `ENTER` | Blob enters from edge |
| `EXIT` | Blob leaves through edge |
| `APPEAR` | Blob appears in center |
| `DISAPPEAR` | Blob disappears from center |

### Direction Detection

```python
if blob.edge == "left":
    direction = RIGHT if velocity.x > 0 else LEFT
elif blob.edge == "top":
    direction = DOWN if velocity.y > 0 else UP
```

## Output Formats

### HTML Visualization

```bash
# Generates: motion_analysis_*.html
sq live narrator --url "rtsp://..." --dsl-only
```

### CSV Timing Log

```bash
# Generates: dsl_timing_*.csv
sq live narrator --url "rtsp://..." --realtime
```

### WebSocket Stream

```javascript
// Browser receives JSON frames
{
  "type": "frame",
  "data": {
    "frame_num": 42,
    "motion_percent": 5.2,
    "blobs": [...],
    "events": [...]
  }
}
```

## Usage Examples

### Basic Motion Detection

```bash
sq live narrator --url "rtsp://..." --dsl-only --fps 10
```

### With Real-time Viewer

```bash
sq live narrator --url "rtsp://..." --dsl-only --realtime --fps 20
open http://localhost:8766
```

### With LLM Analysis

```bash
sq live narrator --url "rtsp://..." --mode track --realtime
```

---

**Related:**
- [Real-time Streaming](REALTIME_STREAMING.md)
- [Performance Optimization](PERFORMANCE.md)
- [Back to Documentation](README.md)
