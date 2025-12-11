# 🎯 Motion Analysis

DSL-based motion tracking and blob detection.

**[← Back to Documentation](README.md)**

---

## Overview

StreamWare uses a custom DSL (Domain Specific Language) for efficient motion analysis. The system detects, tracks, and classifies moving objects using OpenCV.

## How It Works

```text
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

## Configurable Motion Thresholds (NEW!)

All motion detection parameters are now configurable through environment variables:

### Core Motion Detection

```ini
# Motion Detection Sensitivity
SQ_MOTION_DIFF_THRESHOLD=25           # OpenCV threshold for motion detection
SQ_MOTION_BLUR_KERNEL=5               # Gaussian blur kernel size
SQ_MOTION_CONTOUR_MIN_AREA=100        # Minimum contour area for motion regions
SQ_MOTION_SCALE_WIDTH=320             # Max width for motion detection scaling
SQ_MOTION_SCALE_HEIGHT=240            # Max height for motion detection scaling
```

### Motion Classification

```ini
# Motion Percentage Thresholds
SQ_MOTION_MIN_PERCENT=0.5             # Minimum motion percent to consider
SQ_MOTION_LOW_PERCENT=1.0             # Low motion threshold
SQ_MOTION_MEDIUM_PERCENT=5.0          # Medium motion threshold
SQ_MOTION_HIGH_PERCENT=15.0           # High motion threshold
```

### Error Handling

```ini
# Error and Edge Cases
SQ_MOTION_FIRST_FRAME_PERCENT=100.0   # Assume motion percent for first frame
SQ_MOTION_ERROR_PERCENT=50.0          # Motion error handling percentage
```

**Threshold Tuning Guide:**

| Environment | Recommended Settings |
|-------------|---------------------|
| **Indoor/Low Noise** | `SQ_MOTION_DIFF_THRESHOLD=15`, `SQ_MOTION_CONTOUR_MIN_AREA=50` |
| **Outdoor/High Noise** | `SQ_MOTION_DIFF_THRESHOLD=30`, `SQ_MOTION_CONTOUR_MIN_AREA=200` |
| **High Sensitivity** | `SQ_MOTION_DIFF_THRESHOLD=10`, `SQ_MOTION_MIN_PERCENT=0.1` |
| **Low Sensitivity** | `SQ_MOTION_DIFF_THRESHOLD=40`, `SQ_MOTION_MIN_PERCENT=2.0` |

**Impact on Performance:**

- Lower thresholds = more motion detected, more processing
- Higher thresholds = less noise, but may miss subtle movements
- Smaller contour areas = detect smaller objects, more computational cost

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

## HOG Person Detection Configuration (NEW!)

HOG (Histogram of Oriented Gradients) person detection is now fully configurable:

```ini
# HOG Detection Parameters
SQ_HOG_SCALE=400                      # Max dimension for HOG detection
SQ_HOG_WINSTRIDE=8                    # HOG detection window stride
SQ_HOG_PADDING=4                      # HOG detection padding
SQ_HOG_SCALE_FACTOR=1.05              # HOG detection scale factor

# HOG Confidence Thresholds
SQ_HOG_CONFIDENT_NO_PERSON=0.8        # Confidence when no person detected
SQ_HOG_MIGHT_BE_PERSON=0.5            # Confidence when might be person
```

**HOG Parameter Impact:**

| Parameter | Effect | Recommended Range |
|-----------|--------|-------------------|
| **SQ_HOG_SCALE** | Detection resolution vs speed | 300-600 |
| **SQ_HOG_WINSTRIDE** | Detection granularity vs speed | 4-16 |
| **SQ_HOG_SCALE_FACTOR** | Multi-scale detection sensitivity | 1.03-1.10 |
| **SQ_HOG_PADDING** | Edge detection improvement | 0-8 |

**Environment-Specific Settings:**

```ini
# High Resolution (Good lighting, stationary camera)
SQ_HOG_SCALE=600
SQ_HOG_WINSTRIDE=4
SQ_HOG_SCALE_FACTOR=1.03

# Standard Resolution (Typical indoor)
SQ_HOG_SCALE=400
SQ_HOG_WINSTRIDE=8
SQ_HOG_SCALE_FACTOR=1.05

# Low Resolution (Poor lighting, moving camera)
SQ_HOG_SCALE=300
SQ_HOG_WINSTRIDE=12
SQ_HOG_SCALE_FACTOR=1.08
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
