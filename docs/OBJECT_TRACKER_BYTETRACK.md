# ObjectTrackerByteTrack API Documentation

## Overview

`ObjectTrackerByteTrack` is a high-performance multi-object tracker built on top of the [Supervision ByteTrack](https://github.com/roboflow/supervision) implementation. It provides stable object tracking with motion gating, entry/exit event detection, and seamless integration with the existing streamware tracking infrastructure.

## Key Features

- 🎯 **Stable Track IDs** - Objects maintain consistent identifiers across frames
- ⚡ **Motion Gating** - Reduces unnecessary YOLO detections by 45-90%
- 📢 **Entry/Exit Events** - Instant notifications when objects enter or leave the frame
- 🔄 **Track Lifecycle** - Complete state management (NEW → TRACKED → LOST → GONE)
- 🔧 **Configurable Parameters** - Fine-tune tracking behavior for your use case

## Installation

```bash
# Install streamware with tracking support
pip install streamware[tracking]

# Or install all features
pip install streamware[all]
```

## Quick Start

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack

# Create tracker
tracker = ObjectTrackerByteTrack(
    focus="person",
    max_lost_frames=90,
    min_stable_frames=3,
    frame_rate=30,
)

# Update with detections
detections = [
    {"x": 0.5, "y": 0.5, "w": 0.1, "h": 0.2, "confidence": 0.8, "type": "person"}
]
result = tracker.update(detections)

# Check results
print(f"Active tracks: {result.active_count}")
print(f"New entries: {len(result.entries)}")
print(f"Recent exits: {len(result.exits)}")
```

## API Reference

### Constructor

```python
ObjectTrackerByteTrack(
    focus: str = "person",
    max_lost_frames: int = 90,
    min_stable_frames: int = 3,
    frame_rate: int = 30,
)
```

**Parameters:**
- `focus` (str): Primary object type to track (default: "person")
- `max_lost_frames` (int): Frames before considering a track permanently lost (default: 90)
- `min_stable_frames` (int): Frames before a track is considered stable (default: 3)
- `frame_rate` (int): Video frame rate for timing calculations (default: 30)

### Core Methods

#### update()

```python
update(
    detections: List[Dict],
    timestamp: float = None,
) -> TrackingResult
```

Update the tracker with new detections and get tracking results.

**Parameters:**
- `detections` (List[Dict]): List of detection dictionaries with keys:
  - `x` (float): Center X position (0-1 normalized)
  - `y` (float): Center Y position (0-1 normalized)
  - `w` (float): Width (0-1 normalized)
  - `h` (float): Height (0-1 normalized)
  - `confidence` (float): Detection confidence (0-1)
  - `type` (str, optional): Object type/class
- `timestamp` (float, optional): Current timestamp (default: time.time())

**Returns:**
- `TrackingResult`: Complete tracking result with all tracked objects and events

#### reset()

```python
reset() -> None
```

Reset all tracking state and clear all tracks.

#### get_stable_tracks()

```python
get_stable_tracks() -> Set[int]
```

Get IDs of all currently stable tracks.

**Returns:**
- `Set[int]`: Set of stable track IDs

#### get_object()

```python
get_object(track_id: int) -> Optional[TrackedObject]
```

Get a specific tracked object by ID.

**Parameters:**
- `track_id` (int): Track ID to retrieve

**Returns:**
- `TrackedObject` or None: The tracked object if found

#### get_all_objects()

```python
get_all_objects() -> List[TrackedObject]
```

Get all currently tracked objects.

**Returns:**
- `List[TrackedObject]`: List of all tracked objects

### Properties

- `object_count` (int): Number of currently active tracks
- `total_tracked` (int): Total number of tracks created since reset

## Data Structures

### TrackingResult

```python
@dataclass
class TrackingResult:
    objects: List[TrackedObject]      # All active tracks
    new_objects: List[TrackedObject]  # Tracks created this frame
    lost_objects: List[TrackedObject] # Tracks lost this frame
    entries: List[TrackedObject]      # Objects that entered frame
    exits: List[TrackedObject]        # Objects that left frame
    total_count: int                  # Total tracks created
    active_count: int                 # Currently active tracks
```

### TrackedObject

```python
@dataclass
class TrackedObject:
    id: int                    # Unique track identifier
    object_type: str           # Object class/type
    bbox: BoundingBox          # Normalized bounding box
    state: ObjectState         # Current track state
    direction: Direction       # Movement direction
    first_seen: float          # Timestamp when first detected
    last_seen: float           # Timestamp of last update
    frames_tracked: int        # Number of frames tracked
    frames_lost: int           # Frames since last detection
    positions: List[Tuple]     # Position history (x, y, timestamp)
```

### ObjectState

```python
class ObjectState(Enum):
    NEW = "new"           # Just created, not yet stable
    TRACKED = "tracked"   # Stable and actively tracked
    LOST = "lost"         # Temporarily missing
    GONE = "gone"         # Permanently lost
```

### Direction

```python
class Direction(Enum):
    STATIC = "static"
    ENTERING = "entering"
    EXITING = "exiting"
    MOVING_LEFT = "moving_left"
    MOVING_RIGHT = "moving_right"
    MOVING_UP = "moving_up"
    MOVING_DOWN = "moving_down"
```

## Usage Examples

### Basic Person Tracking

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack

# Create tracker for person detection
tracker = ObjectTrackerByteTrack(
    focus="person",
    min_stable_frames=5,  # Require 5 frames for stability
)

# Simulate detection updates
for frame_id in range(10):
    # Mock detection (would come from YOLO/other detector)
    detections = [
        {"x": 0.5, "y": 0.5, "w": 0.1, "h": 0.2, "confidence": 0.8, "type": "person"}
    ]
    
    result = tracker.update(detections)
    
    # Check for new entries
    if result.entries:
        for obj in result.entries:
            print(f"Person #{obj.id} entered (frame {frame_id})")
    
    # Check stable tracks
    stable_ids = tracker.get_stable_tracks()
    if stable_ids:
        print(f"Stable tracks: {stable_ids}")
```

### Multi-Object Tracking

```python
# Track multiple object types
tracker = ObjectTrackerByteTrack(
    focus="any",  # Track all detected objects
    min_stable_frames=3,
)

# Multiple detections in same frame
detections = [
    {"x": 0.3, "y": 0.4, "w": 0.08, "h": 0.15, "confidence": 0.9, "type": "person"},
    {"x": 0.7, "y": 0.5, "w": 0.12, "h": 0.08, "confidence": 0.8, "type": "vehicle"},
]

result = tracker.update(detections)

print(f"Tracking {result.active_count} objects:")
for obj in result.objects:
    print(f"  - {obj.object_type} #{obj.id} at ({obj.bbox.x:.2f}, {obj.bbox.y:.2f})")
```

### Entry/Exit Event Handling

```python
tracker = ObjectTrackerByteTrack()

def handle_tracking_events(result):
    """Process entry/exit events"""
    
    # New objects entered
    if result.entries:
        for obj in result.entries:
            print(f"🟢 {obj.object_type.title()} #{obj.id} entered")
            # Trigger alarm, notification, etc.
    
    # Objects left the frame
    if result.exits:
        for obj in result.exits:
            print(f"🔴 {obj.object_type.title()} #{obj.id} left")
            # Log exit, clean up resources, etc.

# Simulation
for frame in range(20):
    detections = get_detections_for_frame(frame)  # Your detection logic
    result = tracker.update(detections)
    handle_tracking_events(result)
```

### Track State Monitoring

```python
tracker = ObjectTrackerByteTrack()

def analyze_track_states(result):
    """Analyze the state of all tracks"""
    
    state_counts = {}
    for obj in result.objects:
        state = obj.state.value
        state_counts[state] = state_counts.get(state, 0) + 1
    
    print(f"Track states: {state_counts}")
    
    # Find tracks that might be lost soon
    at_risk = [obj for obj in result.objects 
               if obj.state == ObjectState.LOST and obj.frames_lost > 30]
    
    if at_risk:
        print(f"⚠️  {len(at_risk)} tracks at risk of being lost")

result = tracker.update(detections)
analyze_track_states(result)
```

### Performance Monitoring

```python
import time

tracker = ObjectTrackerByteTrack()
total_updates = 0
total_time = 0

for frame_id in range(100):
    start_time = time.time()
    
    detections = get_detections_for_frame(frame_id)
    result = tracker.update(detections)
    
    update_time = time.time() - start_time
    total_time += update_time
    total_updates += 1
    
    if frame_id % 10 == 0:
        avg_time = total_time / total_updates
        fps = 1 / avg_time if avg_time > 0 else 0
        print(f"Frame {frame_id}: {avg_time*1000:.1f}ms avg, {fps:.1f} FPS")

print(f"Performance: {total_time/total_updates*1000:.1f}ms average per update")
```

## Integration with Live Narrator

The tracker is automatically integrated with `LiveNarratorComponent` when using `--mode track`:

```bash
# Enable ByteTrack tracking in live narrator
sq live narrator --url "rtsp://camera/stream" --mode track --focus person --tts
```

Configuration parameters:
```ini
# .env file
SQ_TRACK_MIN_STABLE_FRAMES=3
SQ_TRACK_BUFFER=90
SQ_MOTION_GATE_THRESHOLD=1000
SQ_PERIODIC_INTERVAL=30
```

## Motion Gating

When used with `SmartDetector`, the tracker enables motion gating to reduce unnecessary detections:

```python
from streamware.smart_detector import SmartDetector

# Detector with motion gating
detector = SmartDetector(
    motion_gate_threshold=1000,  # Min motion area in pixels
    periodic_interval=30,        # Force detection every N frames
)

# This will skip YOLO detection when motion is below threshold
result = detector.analyze(frame_path, prev_frame_path)
if result.skip_reason == "motion_gate":
    print("Skipped detection due to low motion")
```

## Best Practices

### 1. Choose Appropriate Stability Threshold

```python
# For fast-moving objects (vehicles, sports)
tracker = ObjectTrackerByteTrack(min_stable_frames=2)

# For slow-moving objects (people, surveillance)
tracker = ObjectTrackerByteTrack(min_stable_frames=5)

# For very stable scenes (static cameras)
tracker = ObjectTrackerByteTrack(min_stable_frames=10)
```

### 2. Handle Track Loss Gracefully

```python
def update_tracker(detections):
    result = tracker.update(detections)
    
    # Process stable tracks only
    stable_objects = [obj for obj in result.objects 
                     if obj.state == ObjectState.TRACKED]
    
    # Warn about lost tracks
    if result.lost_objects:
        print(f"Lost {len(result.lost_objects)} tracks")
    
    return stable_objects
```

### 3. Optimize for Performance

```python
# For real-time applications (>30 FPS)
tracker = ObjectTrackerByteTrack(
    min_stable_frames=2,  # Faster stability
    max_lost_frames=30,   # Faster cleanup
)

# For accuracy-critical applications
tracker = ObjectTrackerByteTrack(
    min_stable_frames=5,   # More stability
    max_lost_frames=120,   # Longer tracking
)
```

### 4. Use with Motion Gating

```python
# Configure motion gating for efficiency
detector = SmartDetector(
    motion_gate_threshold=500,   # Lower threshold = more sensitive
    periodic_interval=15,        # More frequent checks
)

tracker = ObjectTrackerByteTrack(
    min_stable_frames=3,
)

# Combined pipeline
detections = detector.analyze(frame_path, prev_frame_path)
if not detections:  # Gated out
    tracking_result = tracker.update([])  # Update with no detections
else:
    tracking_result = tracker.update(detections)
```

## Troubleshooting

### Common Issues

1. **Tracks flickering between IDs**
   - Increase `min_stable_frames`
   - Check detection quality/consistency
   - Ensure proper frame rate timing

2. **Too many false tracks**
   - Increase detection confidence threshold
   - Adjust `min_stable_frames` higher
   - Filter detections by size/area

3. **Missing real objects**
   - Decrease `min_stable_frames`
   - Lower detection confidence threshold
   - Check motion gating settings

4. **Performance issues**
   - Enable motion gating
   - Increase `periodic_interval`
   - Reduce detection frequency

### Debug Information

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Monitor tracker state
def debug_tracker_state(tracker):
    print(f"Active tracks: {tracker.object_count}")
    print(f"Total created: {tracker.total_tracked}")
    print(f"Stable IDs: {tracker.get_stable_tracks()}")
    
    # Check internal state
    print(f"Internal tracks: {len(tracker._tracked_objects)}")
    print(f"Frame counters: {len(tracker._track_frames)}")
```

## Performance Benchmarks

Based on RTSP stream testing with YOLO11n:

| Configuration | Detection FPS | Tracking FPS | Motion Gate Reduction |
|---------------|---------------|--------------|----------------------|
| Default       | 30            | 74+          | 45-86%               |
| High Sensitivity | 25        | 60+          | 30-50%               |
| Low Power     | 15            | 45+          | 70-90%               |

## See Also

- [Live Narrator Documentation](LIVE_NARRATOR_ARCHITECTURE.md)
- [Smart Detector Documentation](SMART_DETECTOR.md)
- [Tracking Benchmark Demo](../demos/tracking_benchmark/README.md)
- [Configuration Guide](CONFIGURATION.md)
