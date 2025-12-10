#!/usr/bin/env python3
"""
MQTT Integration Examples for Streamware

Demonstrates how to:
1. Publish motion detection to MQTT
2. Subscribe and process events
3. Integrate with Home Assistant
4. Build alerting systems
"""

import json
import time
from typing import Callable, Optional


# ============================================================================
# Example 1: Basic MQTT Publisher
# ============================================================================

def example_basic_publisher():
    """Start MQTT DSL publisher from Python."""
    from streamware.realtime_visualizer import MQTTDSLPublisher
    
    publisher = MQTTDSLPublisher(
        rtsp_url="rtsp://admin:password@camera:554/stream",
        mqtt_broker="localhost",
        mqtt_port=1883,
        topic_prefix="streamware/dsl",
        fps=5.0,
        width=320,
        height=240,
        motion_threshold=2.0,  # Publish events when motion > 2%
    )
    
    print("Starting MQTT publisher...")
    publisher.start()  # Blocks until Ctrl+C


# ============================================================================
# Example 2: MQTT Subscriber with Alerts
# ============================================================================

def example_subscriber_with_alerts():
    """Subscribe to motion events and send alerts."""
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        print("Install paho-mqtt: pip install paho-mqtt")
        return
    
    def on_connect(client, userdata, flags, rc):
        print(f"Connected to MQTT broker (rc={rc})")
        client.subscribe("streamware/dsl/#")
    
    def on_message(client, userdata, msg):
        topic = msg.topic
        
        if topic.endswith("/motion"):
            # Motion level (float)
            motion = float(msg.payload.decode())
            if motion > 20:
                print(f"⚠️ HIGH MOTION: {motion:.1f}%")
        
        elif topic.endswith("/events"):
            # Motion event (JSON)
            event = json.loads(msg.payload)
            level = event.get("level", "LOW")
            motion = event.get("motion_percent", 0)
            objects = len(event.get("objects", []))
            
            if level == "HIGH":
                print(f"🚨 ALERT: {motion:.1f}% motion, {objects} objects")
                # Here you could:
                # - Send push notification
                # - Trigger alarm
                # - Save snapshot
                # - Call webhook
        
        elif topic.endswith("/frame"):
            # Frame metadata (JSON)
            frame = json.loads(msg.payload)
            # Periodic status update
            if frame.get("frame", 0) % 100 == 0:
                print(f"📊 Frame {frame['frame']}: {frame['motion_percent']:.1f}%")
    
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("Connecting to MQTT broker...")
    client.connect("localhost", 1883, 60)
    
    print("Listening for events (Ctrl+C to stop)...")
    client.loop_forever()


# ============================================================================
# Example 3: Motion Event Processor
# ============================================================================

class MotionEventProcessor:
    """Process motion events with debouncing and aggregation."""
    
    def __init__(
        self,
        mqtt_broker: str = "localhost",
        mqtt_port: int = 1883,
        topic_prefix: str = "streamware/dsl",
        alert_callback: Optional[Callable] = None,
        debounce_seconds: float = 5.0,
        min_motion_threshold: float = 10.0,
    ):
        self.mqtt_broker = mqtt_broker
        self.mqtt_port = mqtt_port
        self.topic_prefix = topic_prefix
        self.alert_callback = alert_callback
        self.debounce_seconds = debounce_seconds
        self.min_motion_threshold = min_motion_threshold
        
        self._last_alert_time = 0
        self._motion_history = []
        self._client = None
    
    def start(self):
        """Start processing events."""
        import paho.mqtt.client as mqtt
        
        self._client = mqtt.Client()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        
        self._client.connect(self.mqtt_broker, self.mqtt_port, 60)
        self._client.loop_forever()
    
    def _on_connect(self, client, userdata, flags, rc):
        print(f"Connected to {self.mqtt_broker}")
        client.subscribe(f"{self.topic_prefix}/events")
        client.subscribe(f"{self.topic_prefix}/motion")
    
    def _on_message(self, client, userdata, msg):
        now = time.time()
        
        if msg.topic.endswith("/motion"):
            motion = float(msg.payload.decode())
            self._motion_history.append((now, motion))
            # Keep last 60 seconds
            self._motion_history = [
                (t, m) for t, m in self._motion_history
                if now - t < 60
            ]
        
        elif msg.topic.endswith("/events"):
            event = json.loads(msg.payload)
            motion = event.get("motion_percent", 0)
            
            # Check if we should alert
            if motion >= self.min_motion_threshold:
                if now - self._last_alert_time >= self.debounce_seconds:
                    self._trigger_alert(event)
                    self._last_alert_time = now
    
    def _trigger_alert(self, event):
        """Trigger alert for motion event."""
        print(f"🚨 Motion Alert: {event['motion_percent']:.1f}%")
        
        if self.alert_callback:
            self.alert_callback(event)
    
    def get_average_motion(self, seconds: float = 10.0) -> float:
        """Get average motion over last N seconds."""
        now = time.time()
        recent = [m for t, m in self._motion_history if now - t < seconds]
        return sum(recent) / len(recent) if recent else 0.0


# ============================================================================
# Example 4: Webhook Integration
# ============================================================================

def example_webhook_integration():
    """Send motion events to webhook."""
    import paho.mqtt.client as mqtt
    import urllib.request
    
    WEBHOOK_URL = "https://your-webhook.example.com/motion"
    
    def send_webhook(event):
        """Send event to webhook."""
        data = json.dumps(event).encode('utf-8')
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            print(f"Webhook sent: {event['motion_percent']:.1f}%")
        except Exception as e:
            print(f"Webhook failed: {e}")
    
    def on_message(client, userdata, msg):
        if msg.topic.endswith("/events"):
            event = json.loads(msg.payload)
            if event.get("level") == "HIGH":
                send_webhook(event)
    
    client = mqtt.Client()
    client.on_message = on_message
    client.connect("localhost", 1883)
    client.subscribe("streamware/dsl/events")
    client.loop_forever()


# ============================================================================
# Example 5: Home Assistant Integration
# ============================================================================

HOME_ASSISTANT_CONFIG = """
# Add to configuration.yaml

mqtt:
  sensor:
    - name: "Camera Motion Level"
      state_topic: "streamware/dsl/motion"
      unit_of_measurement: "%"
      icon: mdi:motion-sensor
      
    - name: "Camera Object Count"
      state_topic: "streamware/dsl/frame"
      value_template: "{{ value_json.object_count }}"
      icon: mdi:account-multiple

  binary_sensor:
    - name: "Camera Motion Detected"
      state_topic: "streamware/dsl/events"
      value_template: "{{ 'ON' if value_json.motion_percent > 5 else 'OFF' }}"
      device_class: motion
      
  camera:
    - name: "Camera Preview"
      topic: "streamware/dsl/preview"

# Automation example
automation:
  - alias: "Motion Alert"
    trigger:
      - platform: mqtt
        topic: "streamware/dsl/events"
    condition:
      - condition: template
        value_template: "{{ trigger.payload_json.level == 'HIGH' }}"
    action:
      - service: notify.mobile_app
        data:
          title: "Motion Detected"
          message: "{{ trigger.payload_json.motion_percent }}% motion"
"""


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys
    
    examples = {
        "publisher": example_basic_publisher,
        "subscriber": example_subscriber_with_alerts,
        "webhook": example_webhook_integration,
    }
    
    if len(sys.argv) < 2:
        print("MQTT Integration Examples")
        print()
        print("Usage: python mqtt_integration.py <example>")
        print()
        print("Examples:")
        print("  publisher   - Start MQTT DSL publisher")
        print("  subscriber  - Subscribe and process events")
        print("  webhook     - Send events to webhook")
        print()
        print("Home Assistant config:")
        print(HOME_ASSISTANT_CONFIG)
        sys.exit(0)
    
    example = sys.argv[1]
    if example in examples:
        examples[example]()
    else:
        print(f"Unknown example: {example}")
        print(f"Available: {', '.join(examples.keys())}")
