# MQTT DSL Publisher

Publish motion detection metadata to MQTT broker for IoT integration.

## Quick Start

```bash
# Start MQTT publisher
sq mqtt --url "rtsp://admin:password@camera:554/stream" --broker localhost

# Subscribe to events (in another terminal)
mosquitto_sub -h localhost -t "streamware/dsl/#" -v
```

## Published Topics

| Topic | Description | QoS | Format |
|-------|-------------|-----|--------|
| `{prefix}/status` | Online/offline status | retain | string |
| `{prefix}/motion` | Motion percentage | 0 | float |
| `{prefix}/frame` | Frame metadata | 0 | JSON |
| `{prefix}/dsl` | Full DSL text (when motion > threshold) | 1 | text |
| `{prefix}/events` | Motion events | 1 | JSON |
| `{prefix}/preview` | JPEG preview (every 5s) | 0 | binary |

## Options

```
sq mqtt --help

Options:
  --url, -u URL         RTSP stream URL (required)
  --broker, -b HOST     MQTT broker host (default: localhost)
  --mqtt-port PORT      MQTT broker port (default: 1883)
  --username USER       MQTT username
  --password PASS       MQTT password
  --topic, -t PREFIX    Topic prefix (default: streamware/dsl)
  --fps FPS             Frames per second (default: 5)
  --width WIDTH         Frame width (default: 320)
  --height HEIGHT       Frame height (default: 240)
  --threshold PERCENT   Motion threshold to publish events (default: 2.0)
  --transport TRANSPORT tcp, udp (default: tcp)
```

## Examples

### Basic Usage

```bash
# Local broker
sq mqtt --url "rtsp://camera/stream"

# Remote broker with auth
sq mqtt --url "rtsp://camera/stream" \
  --broker mqtt.example.com \
  --username user \
  --password secret

# Custom topic prefix
sq mqtt --url "rtsp://camera/stream" \
  --topic "home/cameras/front"
```

### High Sensitivity

```bash
# Publish events on any motion (threshold 0.5%)
sq mqtt --url "rtsp://camera/stream" \
  --threshold 0.5 \
  --fps 10
```

### Low Bandwidth

```bash
# Lower FPS, higher threshold
sq mqtt --url "rtsp://camera/stream" \
  --fps 2 \
  --threshold 10.0
```

## Message Formats

### Motion Level (`{prefix}/motion`)

```
15.72
```

### Frame Metadata (`{prefix}/frame`)

```json
{
  "frame": 1234,
  "timestamp": 1733864123.456,
  "timestamp_iso": "2025-12-10T23:15:23.456Z",
  "motion_percent": 15.72,
  "object_count": 3
}
```

### Motion Event (`{prefix}/events`)

```json
{
  "type": "motion_detected",
  "timestamp": 1733864123.456,
  "timestamp_iso": "2025-12-10T23:15:23.456Z",
  "frame": 1234,
  "motion_percent": 15.72,
  "objects": [
    {"x": 0.45, "y": 0.32, "w": 0.12, "h": 0.18},
    {"x": 0.78, "y": 0.65, "w": 0.08, "h": 0.10}
  ],
  "level": "MEDIUM"
}
```

### DSL Text (`{prefix}/dsl`)

```
FRAME 1234 @ 23:15:23.456
  MOTION 15.7% (MEDIUM)
  BLOB id=1 pos=(0.45,0.32) size=(0.12,0.18) area=2.16%
  BLOB id=2 pos=(0.78,0.65) size=(0.08,0.10) area=0.80%
```

## Integration Examples

### Home Assistant

```yaml
# configuration.yaml
mqtt:
  sensor:
    - name: "Camera Motion"
      state_topic: "streamware/dsl/motion"
      unit_of_measurement: "%"
      
    - name: "Camera Objects"
      state_topic: "streamware/dsl/frame"
      value_template: "{{ value_json.object_count }}"

  binary_sensor:
    - name: "Camera Motion Detected"
      state_topic: "streamware/dsl/events"
      value_template: "{{ 'ON' if value_json.motion_percent > 5 else 'OFF' }}"
```

### Node-RED

```json
[
  {
    "type": "mqtt in",
    "topic": "streamware/dsl/events",
    "broker": "localhost"
  },
  {
    "type": "json"
  },
  {
    "type": "switch",
    "property": "payload.level",
    "rules": [
      {"t": "eq", "v": "HIGH"}
    ]
  },
  {
    "type": "telegram sender",
    "msg": "High motion detected!"
  }
]
```

### Python Client

```python
import paho.mqtt.client as mqtt
import json

def on_message(client, userdata, msg):
    if msg.topic.endswith("/events"):
        event = json.loads(msg.payload)
        if event["level"] == "HIGH":
            print(f"ALERT: High motion at {event['timestamp_iso']}")
            # Send notification, trigger alarm, etc.

client = mqtt.Client()
client.on_message = on_message
client.connect("localhost", 1883)
client.subscribe("streamware/dsl/#")
client.loop_forever()
```

## Programmatic Usage

```python
from streamware.realtime_visualizer import MQTTDSLPublisher

publisher = MQTTDSLPublisher(
    rtsp_url="rtsp://camera/stream",
    mqtt_broker="localhost",
    mqtt_port=1883,
    topic_prefix="home/camera/front",
    fps=5.0,
    motion_threshold=2.0,
)
publisher.start()
```

## Requirements

```bash
pip install paho-mqtt opencv-python
```

## See Also

- [Real-time Visualizer](./REALTIME_VISUALIZER.md)
- [Examples](../examples/media-processing/)
