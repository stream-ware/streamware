# ByteTrack Integration Examples

This document provides practical examples of using the new ByteTrack integration in streamware for various real-world scenarios.

## Table of Contents

1. [Basic Person Tracking](#basic-person-tracking)
2. [Multi-Object Scene Monitoring](#multi-object-scene-monitoring)
3. [High-Traffic Area Surveillance](#high-traffic-area-surveillance)
4. [Wildlife Monitoring](#wildlife-monitoring)
5. [Vehicle Traffic Analysis](#vehicle-traffic-analysis)
6. [Security Alert System](#security-alert-system)
7. [Performance Optimization](#performance-optimization)
8. [Custom Event Handling](#custom-event-handling)

## Basic Person Tracking

### CLI Usage

```bash
# Monitor entrance with person detection and TTS alerts
sq live narrator \
  --url "rtsp://admin:password@192.168.1.100:554/stream1" \
  --mode track \
  --focus person \
  --tts \
  --duration 3600  # Run for 1 hour
```

### Configuration (.env)

```ini
# Optimized for person tracking
SQ_TRACK_MIN_STABLE_FRAMES=3     # Quick stability for people
SQ_TRACK_BUFFER=60               # Keep tracks for 2 seconds
SQ_MOTION_GATE_THRESHOLD=800     # Sensitive to human movement
SQ_PERIODIC_INTERVAL=20          # Check every 20 frames
SQ_STREAM_FOCUS=person
SQ_STREAM_MODE=track
```

### Python API

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
from streamware.smart_detector import SmartDetector
import time

class PersonMonitor:
    def __init__(self):
        self.tracker = ObjectTrackerByteTrack(
            focus="person",
            min_stable_frames=3,
            max_lost_frames=60,
            frame_rate=30,
        )
        
        self.detector = SmartDetector(
            motion_gate_threshold=800,
            periodic_interval=20,
        )
    
    def process_frame(self, frame_path, prev_frame_path):
        """Process a single frame"""
        # Get detections with motion gating
        detection_result = self.detector.analyze(frame_path, prev_frame_path)
        
        if detection_result.skip_reason:
            print(f"Skipped detection: {detection_result.skip_reason}")
            detections = []
        else:
            detections = detection_result.detections
        
        # Update tracker
        tracking_result = self.tracker.update(detections)
        
        # Handle events
        self.handle_events(tracking_result)
        
        return tracking_result
    
    def handle_events(self, result):
        """Handle entry/exit events"""
        if result.entries:
            for obj in result.entries:
                print(f"🚪 Person #{obj.id} entered the scene")
                # Send notification, log entry, etc.
        
        if result.exits:
            for obj in result.exits:
                print(f"🚪 Person #{obj.id} left the scene")
                # Log exit, cleanup, etc.

# Usage
monitor = PersonMonitor()
# Process frames in your main loop
```

## Multi-Object Scene Monitoring

### CLI Usage

```bash
# Monitor busy area with multiple object types
sq live narrator \
  --url "rtsp://camera/mall_entrance" \
  --mode track \
  --focus any \
  --tts \
  --verbose
```

### Configuration (.env)

```ini
# Multi-object tracking
SQ_TRACK_MIN_STABLE_FRAMES=5     # More stability for multiple objects
SQ_TRACK_BUFFER=120              # Keep tracks longer
SQ_MOTION_GATE_THRESHOLD=500     # More sensitive
SQ_PERIODIC_INTERVAL=15          # More frequent checks
SQ_DETECT=any                    # Detect all object types
```

### Python API

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
from collections import defaultdict
import json

class MultiObjectMonitor:
    def __init__(self):
        self.tracker = ObjectTrackerByteTrack(
            focus="any",
            min_stable_frames=5,
            max_lost_frames=120,
        )
        
        self.object_counts = defaultdict(int)
        self.total_entries = defaultdict(int)
        self.total_exits = defaultdict(int)
    
    def process_frame(self, detections):
        """Process frame with multiple object types"""
        result = self.tracker.update(detections)
        
        # Update statistics
        self.update_statistics(result)
        
        # Generate summary
        summary = self.generate_summary(result)
        
        return result, summary
    
    def update_statistics(self, result):
        """Update object statistics"""
        # Count current objects by type
        current_counts = defaultdict(int)
        for obj in result.objects:
            if obj.state.value == "tracked":  # Only count stable tracks
                current_counts[obj.object_type] += 1
        
        self.object_counts = current_counts
        
        # Track entries/exits
        for obj in result.entries:
            self.total_entries[obj.object_type] += 1
        
        for obj in result.exits:
            self.total_exits[obj.object_type] += 1
    
    def generate_summary(self, result):
        """Generate scene summary"""
        summary = {
            "active_objects": dict(self.object_counts),
            "total_active": result.active_count,
            "new_entries": len(result.entries),
            "recent_exits": len(result.exits),
        }
        
        # Add recent activity
        if result.entries:
            summary["recent_entries"] = [
                f"{obj.object_type} #{obj.id}" for obj in result.entries[:5]
            ]
        
        if result.exits:
            summary["recent_exits"] = [
                f"{obj.object_type} #{obj.id}" for obj in result.exits[:5]
            ]
        
        return summary
    
    def get_report(self):
        """Get comprehensive report"""
        return {
            "current_scene": dict(self.object_counts),
            "total_entries_today": dict(self.total_entries),
            "total_exits_today": dict(self.total_exits),
        }

# Usage
monitor = MultiObjectMonitor()

# Simulate processing
for frame in range(100):
    detections = get_multi_object_detections(frame)
    result, summary = monitor.process_frame(detections)
    
    if frame % 10 == 0:
        print(f"Frame {frame}: {summary}")
```

## High-Traffic Area Surveillance

### CLI Usage

```bash
# High-traffic area with optimized settings
SQ_MOTION_GATE_THRESHOLD=2000 \
SQ_PERIODIC_INTERVAL=45 \
SQ_TRACK_MIN_STABLE_FRAMES=2 \
sq live narrator \
  --url "rtsp://camera/station_platform" \
  --mode track \
  --focus person \
  --tts \
  --quiet
```

### Python API

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
import time
from datetime import datetime

class TrafficMonitor:
    def __init__(self):
        self.tracker = ObjectTrackerByteTrack(
            focus="person",
            min_stable_frames=2,      # Fast tracking for high traffic
            max_lost_frames=45,       # Quick cleanup
            frame_rate=30,
        )
        
        self.peak_count = 0
        self.total_people_seen = 0
        self.hourly_counts = {}
    
    def process_frame(self, detections):
        """Process frame in high-traffic environment"""
        result = self.tracker.update(detections)
        
        # Track peak occupancy
        if result.active_count > self.peak_count:
            self.peak_count = result.active_count
            print(f"📊 New peak: {self.peak_count} people")
        
        # Count unique people
        for obj in result.entries:
            self.total_people_seen += 1
        
        # Hourly statistics
        current_hour = datetime.now().hour
        if current_hour not in self.hourly_counts:
            self.hourly_counts[current_hour] = 0
        self.hourly_counts[current_hour] = max(
            self.hourly_counts[current_hour], 
            result.active_count
        )
        
        return result
    
    def get_traffic_report(self):
        """Generate traffic analysis report"""
        return {
            "peak_occupancy": self.peak_count,
            "total_unique_people": self.total_people_seen,
            "current_occupancy": self.tracker.object_count,
            "hourly_peaks": self.hourly_counts,
        }

# Usage
monitor = TrafficMonitor()

# Process high-traffic video stream
for frame in range(1000):
    detections = get_person_detections(frame)
    result = monitor.process_frame(detections)
    
    if frame % 100 == 0:
        report = monitor.get_traffic_report()
        print(f"Traffic Report: {report}")
```

## Wildlife Monitoring

### CLI Usage

```bash
# Wildlife camera with animal detection
sq live narrator \
  --url "rtsp://camera/wildlife_feeder" \
  --mode track \
  --focus animal \
  --tts \
  --duration 7200  # 2 hours
```

### Configuration (.env)

```ini
# Wildlife monitoring settings
SQ_TRACK_MIN_STABLE_FRAMES=8     # Animals move less predictably
SQ_TRACK_BUFFER=180              # Keep tracks longer
SQ_MOTION_GATE_THRESHOLD=300     # Very sensitive to small movements
SQ_PERIODIC_INTERVAL=10          # Frequent checks
SQ_ANIMAL_FOCUS=all              # Track all animals
SQ_DETECT=animal
```

### Python API

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
from datetime import datetime
import json

class WildlifeMonitor:
    def __init__(self):
        self.tracker = ObjectTrackerByteTrack(
            focus="animal",
            min_stable_frames=8,
            max_lost_frames=180,
        )
        
        self.sightings = {}
        self.activity_log = []
    
    def process_frame(self, detections):
        """Process wildlife camera frame"""
        result = self.tracker.update(detections)
        
        # Log wildlife sightings
        self.log_sightings(result)
        
        return result
    
    def log_sightings(self, result):
        """Log animal sightings with metadata"""
        timestamp = datetime.now()
        
        for obj in result.entries:
            sighting = {
                "timestamp": timestamp.isoformat(),
                "animal_type": obj.object_type,
                "track_id": obj.id,
                "position": {"x": obj.bbox.x, "y": obj.bbox.y},
                "duration": "ongoing",
            }
            
            self.sightings[obj.id] = sighting
            self.activity_log.append(sighting)
            
            print(f"🦁 {obj.object_type} #{obj.id} spotted at {obj.bbox.x:.2f}, {obj.bbox.y:.2f}")
        
        for obj in result.exits:
            if obj.id in self.sightings:
                sighting = self.sightings[obj.id]
                sighting["duration"] = time.time() - obj.first_seen
                sighting["end_time"] = timestamp.isoformat()
                
                print(f"🦁 {obj.object_type} #{obj.id} left after {sighting['duration']:.1f}s")
    
    def get_wildlife_report(self):
        """Generate wildlife activity report"""
        return {
            "total_sightings": len(self.sightings),
            "active_animals": self.tracker.object_count,
            "recent_activity": self.activity_log[-10:],  # Last 10 sightings
            "sightings_by_type": self.count_by_type(),
        }
    
    def count_by_type(self):
        """Count sightings by animal type"""
        counts = {}
        for sighting in self.sightings.values():
            animal_type = sighting["animal_type"]
            counts[animal_type] = counts.get(animal_type, 0) + 1
        return counts

# Usage
monitor = WildlifeMonitor()

# Process wildlife camera footage
for frame in range(500):
    detections = get_animal_detections(frame)
    result = monitor.process_frame(detections)
    
    if frame % 50 == 0:
        report = monitor.get_wildlife_report()
        print(f"Wildlife Report: {report}")
```

## Vehicle Traffic Analysis

### CLI Usage

```bash
# Traffic camera with vehicle counting
sq live narrator \
  --url "rtsp://traffic_camera/intersection" \
  --mode track \
  --focus vehicle \
  --tts \
  --verbose
```

### Python API

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
import math

class TrafficAnalyzer:
    def __init__(self):
        self.tracker = ObjectTrackerByteTrack(
            focus="vehicle",
            min_stable_frames=3,
            max_lost_frames=90,
        )
        
        self.vehicle_count = 0
        self.speed_data = {}
        self.direction_counts = {"north": 0, "south": 0, "east": 0, "west": 0}
    
    def process_frame(self, detections):
        """Process traffic camera frame"""
        result = self.tracker.update(detections)
        
        # Analyze vehicle movement
        self.analyze_traffic(result)
        
        return result
    
    def analyze_traffic(self, result):
        """Analyze vehicle traffic patterns"""
        for obj in result.objects:
            if obj.state.value == "tracked" and len(obj.positions) > 5:
                # Calculate speed (simplified)
                if len(obj.positions) >= 2:
                    pos1 = obj.positions[-2]
                    pos2 = obj.positions[-1]
                    
                    dt = pos2[2] - pos1[2]  # Time difference
                    dx = pos2[0] - pos1[0]  # X movement
                    dy = pos2[1] - pos1[1]  # Y movement
                    
                    if dt > 0:
                        speed = math.sqrt(dx**2 + dy**2) / dt
                        self.speed_data[obj.id] = speed
                
                # Determine direction
                if len(obj.positions) >= 10:
                    direction = self.calculate_direction(obj)
                    if direction:
                        self.direction_counts[direction] += 1
        
        # Count vehicles
        for obj in result.entries:
            self.vehicle_count += 1
    
    def calculate_direction(self, obj):
        """Calculate vehicle direction from position history"""
        if len(obj.positions) < 10:
            return None
        
        # Use first and last positions
        start_pos = obj.positions[0]
        end_pos = obj.positions[-1]
        
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        
        # Determine primary direction
        if abs(dx) > abs(dy):
            return "east" if dx > 0 else "west"
        else:
            return "north" if dy > 0 else "south"
    
    def get_traffic_report(self):
        """Generate traffic analysis report"""
        avg_speed = sum(self.speed_data.values()) / len(self.speed_data) if self.speed_data else 0
        
        return {
            "total_vehicles": self.vehicle_count,
            "current_vehicles": self.tracker.object_count,
            "average_speed": avg_speed,
            "direction_distribution": self.direction_counts,
            "peak_speed": max(self.speed_data.values()) if self.speed_data else 0,
        }

# Usage
analyzer = TrafficAnalyzer()

# Process traffic camera footage
for frame in range(1000):
    detections = get_vehicle_detections(frame)
    result = analyzer.process_frame(detections)
    
    if frame % 100 == 0:
        report = analyzer.get_traffic_report()
        print(f"Traffic Analysis: {report}")
```

## Security Alert System

### CLI Usage

```bash
# Security monitoring with alerts
sq live narrator \
  --url "rtsp://security_camera/perimeter" \
  --mode track \
  --focus person \
  --tts \
  --alert-threshold 2 \
  --duration 86400  # 24 hours
```

### Python API

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
import smtplib
from email.mime.text import MIMEText
import time

class SecuritySystem:
    def __init__(self, alert_threshold=2):
        self.tracker = ObjectTrackerByteTrack(
            focus="person",
            min_stable_frames=5,
            max_lost_frames=120,
        )
        
        self.alert_threshold = alert_threshold
        self.alert_cooldown = 300  # 5 minutes between alerts
        self.last_alert_time = 0
        
        self.security_log = []
    
    def process_frame(self, detections):
        """Process security camera frame"""
        result = self.tracker.update(detections)
        
        # Check for security events
        self.check_security_events(result)
        
        return result
    
    def check_security_events(self, result):
        """Check for security-relevant events"""
        current_time = time.time()
        
        # Multiple people detected
        if result.active_count >= self.alert_threshold:
            if current_time - self.last_alert_time > self.alert_cooldown:
                self.trigger_alert("multiple_people", result)
                self.last_alert_time = current_time
        
        # Unexpected entry (after hours)
        if result.entries:
            for obj in result.entries:
                self.log_security_event("entry", obj)
        
        # Suspicious behavior (lingering)
        for obj in result.objects:
            if obj.frames_tracked > 300:  # 10 seconds at 30fps
                self.log_security_event("lingering", obj)
    
    def trigger_alert(self, alert_type, result):
        """Trigger security alert"""
        alert_message = f"🚨 SECURITY ALERT: {alert_type.upper()}\n"
        alert_message += f"Active people: {result.active_count}\n"
        alert_message += f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Send email notification
        self.send_email_alert(alert_message)
        
        # Log alert
        self.security_log.append({
            "type": "alert",
            "alert_type": alert_type,
            "timestamp": time.time(),
            "active_count": result.active_count,
        })
        
        print(alert_message)
    
    def send_email_alert(self, message):
        """Send email alert (placeholder)"""
        # Implement email sending logic
        print(f"📧 Email alert sent: {message[:50]}...")
    
    def log_security_event(self, event_type, obj):
        """Log security event"""
        event = {
            "type": "security_event",
            "event_type": event_type,
            "object_id": obj.id,
            "object_type": obj.object_type,
            "position": {"x": obj.bbox.x, "y": obj.bbox.y},
            "timestamp": time.time(),
        }
        
        self.security_log.append(event)
        print(f"🔒 Security event: {event_type} - {obj.object_type} #{obj.id}")
    
    def get_security_report(self):
        """Generate security report"""
        recent_events = [e for e in self.security_log 
                        if time.time() - e["timestamp"] < 3600]  # Last hour
        
        return {
            "current_occupancy": self.tracker.object_count,
            "recent_events": len(recent_events),
            "total_alerts": len([e for e in self.security_log if e["type"] == "alert"]),
            "recent_activity": recent_events[-10:],
        }

# Usage
security = SecuritySystem(alert_threshold=3)

# Process security camera footage
for frame in range(2000):
    detections = get_person_detections(frame)
    result = security.process_frame(detections)
    
    if frame % 200 == 0:
        report = security.get_security_report()
        print(f"Security Report: {report}")
```

## Performance Optimization

### High-Performance Configuration

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
from streamware.smart_detector import SmartDetector
import time

class HighPerformanceTracker:
    def __init__(self):
        # Optimized tracker for speed
        self.tracker = ObjectTrackerByteTrack(
            min_stable_frames=2,      # Fast stability
            max_lost_frames=30,       # Quick cleanup
            frame_rate=60,            # High frame rate
        )
        
        # Optimized detector with aggressive motion gating
        self.detector = SmartDetector(
            motion_gate_threshold=2000,  # High threshold
            periodic_interval=45,        # Less frequent checks
        )
        
        self.performance_stats = {
            "total_frames": 0,
            "detection_time": 0,
            "tracking_time": 0,
            "gated_frames": 0,
        }
    
    def process_frame_optimized(self, frame_path, prev_frame_path):
        """Optimized frame processing"""
        start_time = time.time()
        
        # Detection with motion gating
        det_start = time.time()
        detection_result = self.detector.analyze(frame_path, prev_frame_path)
        det_time = time.time() - det_start
        
        if detection_result.skip_reason:
            detections = []
            self.performance_stats["gated_frames"] += 1
        else:
            detections = detection_result.detections
        
        # Tracking
        track_start = time.time()
        result = self.tracker.update(detections)
        track_time = time.time() - track_start
        
        # Update stats
        self.performance_stats["total_frames"] += 1
        self.performance_stats["detection_time"] += det_time
        self.performance_stats["tracking_time"] += track_time
        
        return result
    
    def get_performance_report(self):
        """Get performance statistics"""
        stats = self.performance_stats
        total_frames = stats["total_frames"]
        
        if total_frames == 0:
            return {}
        
        return {
            "avg_detection_time": stats["detection_time"] / total_frames * 1000,
            "avg_tracking_time": stats["tracking_time"] / total_frames * 1000,
            "total_processing_time": (stats["detection_time"] + stats["tracking_time"]) / total_frames * 1000,
            "gating_efficiency": stats["gated_frames"] / total_frames * 100,
            "estimated_fps": 1 / ((stats["detection_time"] + stats["tracking_time"]) / total_frames),
        }

# Usage
tracker = HighPerformanceTracker()

# Benchmark performance
for frame in range(1000):
    result = tracker.process_frame_optimized(f"frame_{frame}.jpg", f"frame_{frame-1}.jpg")
    
    if frame % 100 == 0:
        perf = tracker.get_performance_report()
        print(f"Performance: {perf}")
```

## Custom Event Handling

### Custom Event Processor

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
from abc import ABC, abstractmethod
import json

class EventHandler(ABC):
    """Base class for event handlers"""
    
    @abstractmethod
    def handle_entry(self, obj):
        pass
    
    @abstractmethod
    def handle_exit(self, obj):
        pass
    
    @abstractmethod
    def handle_update(self, obj):
        pass

class LoggingEventHandler(EventHandler):
    """Event handler that logs to file"""
    
    def __init__(self, log_file="tracking_events.json"):
        self.log_file = log_file
        self.events = []
    
    def handle_entry(self, obj):
        event = {
            "type": "entry",
            "object_id": obj.id,
            "object_type": obj.object_type,
            "timestamp": time.time(),
            "position": {"x": obj.bbox.x, "y": obj.bbox.y},
        }
        self.events.append(event)
        print(f"📝 Logged entry: {obj.object_type} #{obj.id}")
    
    def handle_exit(self, obj):
        event = {
            "type": "exit",
            "object_id": obj.id,
            "object_type": obj.object_type,
            "timestamp": time.time(),
            "duration": time.time() - obj.first_seen,
        }
        self.events.append(event)
        print(f"📝 Logged exit: {obj.object_type} #{obj.id}")
    
    def handle_update(self, obj):
        # Log significant updates only
        if obj.frames_tracked % 100 == 0:  # Every 100 frames
            event = {
                "type": "update",
                "object_id": obj.id,
                "frames_tracked": obj.frames_tracked,
                "timestamp": time.time(),
            }
            self.events.append(event)
    
    def save_events(self):
        """Save events to file"""
        with open(self.log_file, 'w') as f:
            json.dump(self.events, f, indent=2)

class CustomTrackingSystem:
    def __init__(self, event_handlers=None):
        self.tracker = ObjectTrackerByteTrack()
        self.event_handlers = event_handlers or []
    
    def add_event_handler(self, handler):
        """Add an event handler"""
        self.event_handlers.append(handler)
    
    def process_frame(self, detections):
        """Process frame with custom event handling"""
        result = self.tracker.update(detections)
        
        # Handle entries
        for obj in result.entries:
            for handler in self.event_handlers:
                handler.handle_entry(obj)
        
        # Handle exits
        for obj in result.exits:
            for handler in self.event_handlers:
                handler.handle_exit(obj)
        
        # Handle updates for all objects
        for obj in result.objects:
            for handler in self.event_handlers:
                handler.handle_update(obj)
        
        return result

# Usage
# Create custom event handlers
logger = LoggingEventHandler("security_log.json")

# Create tracking system with custom handlers
tracking_system = CustomTrackingSystem([logger])

# Process frames
for frame in range(500):
    detections = get_detections(frame)
    result = tracking_system.process_frame(detections)

# Save event logs
logger.save_events()
```

## Troubleshooting Examples

### Debug Track Loss Issues

```python
from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

class DebugTracker:
    def __init__(self):
        self.tracker = ObjectTrackerByteTrack(min_stable_frames=3)
        self.frame_count = 0
    
    def debug_process_frame(self, detections):
        """Process frame with detailed debugging"""
        self.frame_count += 1
        print(f"\n=== Frame {self.frame_count} ===")
        print(f"Input detections: {len(detections)}")
        
        result = self.tracker.update(detections)
        
        print(f"Active tracks: {result.active_count}")
        print(f"New entries: {len(result.entries)}")
        print(f"Recent exits: {len(result.exits)}")
        
        # Debug individual tracks
        for obj in result.objects:
            print(f"  Track {obj.id}: {obj.object_type}, state={obj.state.value}, "
                  f"frames={obj.frames_tracked}, lost={obj.frames_lost}")
        
        # Check for issues
        if result.exits:
            print("⚠️  Tracks lost this frame:")
            for obj in result.exits:
                print(f"    {obj.id}: tracked for {obj.frames_tracked} frames")
        
        return result

# Usage
debug_tracker = DebugTracker()

# Process with debugging
for frame in range(100):
    detections = get_detections(frame)
    result = debug_tracker.debug_process_frame(detections)
```

These examples demonstrate the flexibility and power of the ByteTrack integration in streamware. Choose the example that best matches your use case and adapt it to your specific requirements.
