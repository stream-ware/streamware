# Count Objects Example

Count people, vehicles, or other objects using YOLO.

## Quick Start

```bash
# Count people
sq watch "count people"
sq watch "ile osób"

# Count cars
sq watch "count cars"
sq watch "ile samochodów"

# Count animals
sq watch "count animals"
```

## Features

- **YOLO-based counting**: Fast and accurate
- **Change notifications**: "Count increased to 3"
- **No LLM needed**: Pure computer vision

## Output Messages

| Event | Message |
|-------|---------|
| Initial count | "3 persons visible" |
| Increase | "Person count increased to 4" |
| Decrease | "Person count decreased to 2" |
| Zero | "No persons visible" |

## Configuration

```env
# .env settings for count mode
SQ_STREAM_FPS=1.0
SQ_YOLO_SKIP_LLM_THRESHOLD=0.2  # Always use YOLO
SQ_USE_GUARDER=false
```

## Python API

```python
from streamware.intent import parse_intent

intent = parse_intent("count people")
print(f"Action: {intent.action}")  # "count"
print(f"Target: {intent.target}")  # "person"
```

## Advanced: Multi-class Counting

```python
from streamware.yolo_detector import YOLODetector

detector = YOLODetector(confidence_threshold=0.3)
results = detector.detect("/path/to/frame.jpg")

# Count by class
counts = {}
for det in results:
    counts[det.class_name] = counts.get(det.class_name, 0) + 1

print(counts)  # {'person': 3, 'car': 2}
```
