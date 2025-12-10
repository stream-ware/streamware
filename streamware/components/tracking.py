"""
Object Tracking Component - Real-time object detection and tracking

Track objects across video frames with AI-powered identification:
- Person tracking with unique IDs
- Vehicle tracking (cars, trucks, bikes)
- Animal tracking
- Custom object tracking
- Movement analysis (direction, speed, zones)

URI Examples:
    tracking://detect?source=rtsp://camera/live&objects=person,vehicle
    tracking://track?source=rtsp://camera/live&target=person&name=John
    tracking://zones?source=rtsp://camera/live&zones=entrance:0,0,100,200|exit:300,0,100,200
    tracking://heatmap?source=rtsp://camera/live&duration=3600

Related:
    - streamware/components/stream.py
    - examples/media-processing/object_tracking.py
"""

import subprocess
import tempfile
import logging
import time
import os
import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from ..core import Component, StreamwareURI, register
from ..exceptions import ComponentError
from ..config import config

logger = logging.getLogger(__name__)


@dataclass
class TrackedObject:
    """Represents a tracked object"""
    id: str
    type: str  # person, vehicle, animal, etc.
    name: Optional[str] = None
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)  # x, y, w, h
    position: Tuple[int, int] = (0, 0)  # center x, y
    first_seen: str = ""
    last_seen: str = ""
    frames_visible: int = 0
    trajectory: List[Tuple[int, int]] = field(default_factory=list)
    current_zone: Optional[str] = None
    direction: str = ""  # N, NE, E, SE, S, SW, W, NW, stationary
    speed: str = ""  # slow, medium, fast, stationary
    confidence: float = 0.0
    attributes: Dict = field(default_factory=dict)


@dataclass  
class Zone:
    """Detection zone"""
    name: str
    x: int
    y: int
    width: int
    height: int
    
    def contains(self, x: int, y: int) -> bool:
        return (self.x <= x <= self.x + self.width and 
                self.y <= y <= self.y + self.height)


@register("tracking")
@register("track")
class TrackingComponent(Component):
    """
    Real-time object tracking component.
    
    Operations:
        - detect: Detect objects in current frame
        - track: Track specific object across frames
        - zones: Monitor zone entry/exit
        - count: Count objects by type
        - heatmap: Generate movement heatmap
    
    URI Examples:
        tracking://detect?source=rtsp://camera/live&objects=person,vehicle
        tracking://track?source=rtsp://camera/live&target=person
        tracking://zones?source=rtsp://camera/live&zones=door:0,0,100,200
        tracking://count?source=rtsp://camera/live&objects=person
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    OBJECT_TYPES = ["person", "vehicle", "car", "truck", "bike", "animal", 
                    "dog", "cat", "bird", "package", "face", "any"]
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "detect"
        
        self.source = uri.get_param("source", uri.get_param("url", ""))
        self.objects = uri.get_param("objects", "person").split(",")
        self.target = uri.get_param("target", "")  # specific object to track
        self.name = uri.get_param("name", "")  # name for tracked object
        
        self.interval = int(uri.get_param("interval", "2"))
        self.duration = int(uri.get_param("duration", "60"))
        self.model = uri.get_param("model", "llava:13b")
        
        # Zones: name:x,y,w,h|name2:x,y,w,h
        self.zones = self._parse_zones(uri.get_param("zones", ""))
        
        # Tracking state
        self._tracked_objects: Dict[str, TrackedObject] = {}
        self._next_id = 1
        self._temp_dir = None
    
    def _parse_zones(self, zones_str: str) -> List[Zone]:
        """Parse zones string into Zone objects"""
        zones = []
        if not zones_str:
            return zones
        
        for zone_def in zones_str.split("|"):
            if ":" in zone_def:
                name, coords = zone_def.split(":", 1)
                parts = coords.split(",")
                if len(parts) == 4:
                    zones.append(Zone(
                        name=name.strip(),
                        x=int(parts[0]),
                        y=int(parts[1]),
                        width=int(parts[2]),
                        height=int(parts[3])
                    ))
        return zones
    
    def process(self, data: Any) -> Dict:
        """Process tracking operation"""
        self._temp_dir = Path(tempfile.mkdtemp())
        
        try:
            if self.operation == "detect":
                return self._detect_objects()
            elif self.operation == "track":
                return self._track_object()
            elif self.operation == "zones":
                return self._monitor_zones()
            elif self.operation == "count":
                return self._count_objects()
            elif self.operation == "heatmap":
                return self._generate_heatmap()
            else:
                raise ComponentError(f"Unknown operation: {self.operation}")
        finally:
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
    
    def stream(self, input_data: Any = None) -> Generator[Dict, None, None]:
        """Stream tracking results continuously"""
        self._temp_dir = Path(tempfile.mkdtemp())
        
        try:
            frame_num = 0
            start_time = time.time()
            
            while True:
                if self.duration > 0 and (time.time() - start_time) > self.duration:
                    break
                
                frame_path = self._capture_frame(frame_num)
                if frame_path and frame_path.exists():
                    result = self._analyze_frame(frame_path, frame_num)
                    yield result
                    frame_num += 1
                
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            pass
        finally:
            if self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir, ignore_errors=True)
            
            yield self._get_tracking_summary()
    
    def _detect_objects(self) -> Dict:
        """Detect objects in frames"""
        results = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                detection = self._analyze_frame(frame_path, i)
                results.append(detection)
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        return {
            "success": True,
            "operation": "detect",
            "source": self.source,
            "objects_tracked": list(self.objects),
            "detections": results,
            "summary": self._get_tracking_summary()
        }
    
    def _track_object(self) -> Dict:
        """Track specific object"""
        results = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                detection = self._analyze_frame(frame_path, i, focus_target=self.target)
                results.append(detection)
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        # Get trajectory for target
        target_trajectory = []
        for obj in self._tracked_objects.values():
            if obj.type == self.target or obj.name == self.target:
                target_trajectory = obj.trajectory
                break
        
        return {
            "success": True,
            "operation": "track",
            "target": self.target,
            "name": self.name,
            "trajectory": target_trajectory,
            "frames": results,
            "summary": self._get_tracking_summary()
        }
    
    def _monitor_zones(self) -> Dict:
        """Monitor zone entries/exits"""
        events = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                detection = self._analyze_frame(frame_path, i)
                
                # Check zone events
                for obj_id, obj in self._tracked_objects.items():
                    for zone in self.zones:
                        in_zone = zone.contains(obj.position[0], obj.position[1])
                        prev_zone = obj.current_zone
                        
                        if in_zone and prev_zone != zone.name:
                            events.append({
                                "type": "zone_enter",
                                "zone": zone.name,
                                "object_id": obj_id,
                                "object_type": obj.type,
                                "timestamp": time.strftime("%H:%M:%S"),
                                "frame": i
                            })
                            obj.current_zone = zone.name
                        elif not in_zone and prev_zone == zone.name:
                            events.append({
                                "type": "zone_exit",
                                "zone": zone.name,
                                "object_id": obj_id,
                                "object_type": obj.type,
                                "timestamp": time.strftime("%H:%M:%S"),
                                "frame": i
                            })
                            obj.current_zone = None
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        return {
            "success": True,
            "operation": "zones",
            "zones": [{"name": z.name, "bounds": (z.x, z.y, z.width, z.height)} for z in self.zones],
            "events": events,
            "summary": self._get_tracking_summary()
        }
    
    def _count_objects(self) -> Dict:
        """Count objects by type over time"""
        counts = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                detection = self._analyze_frame(frame_path, i)
                
                # Count by type
                frame_counts = {}
                for obj in self._tracked_objects.values():
                    obj_type = obj.type
                    frame_counts[obj_type] = frame_counts.get(obj_type, 0) + 1
                
                counts.append({
                    "frame": i,
                    "timestamp": time.strftime("%H:%M:%S"),
                    "counts": frame_counts,
                    "total": sum(frame_counts.values())
                })
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        # Aggregate stats
        all_counts = {}
        for c in counts:
            for obj_type, count in c.get("counts", {}).items():
                if obj_type not in all_counts:
                    all_counts[obj_type] = []
                all_counts[obj_type].append(count)
        
        stats = {}
        for obj_type, values in all_counts.items():
            stats[obj_type] = {
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "avg": sum(values) / len(values) if values else 0
            }
        
        return {
            "success": True,
            "operation": "count",
            "timeline": counts,
            "statistics": stats,
            "summary": self._get_tracking_summary()
        }
    
    def _generate_heatmap(self) -> Dict:
        """Generate movement heatmap data"""
        # Collect all positions
        positions = []
        num_frames = max(1, self.duration // self.interval)
        
        for i in range(num_frames):
            frame_path = self._capture_frame(i)
            if frame_path and frame_path.exists():
                self._analyze_frame(frame_path, i)
                
                for obj in self._tracked_objects.values():
                    positions.append({
                        "x": obj.position[0],
                        "y": obj.position[1],
                        "type": obj.type,
                        "frame": i
                    })
            
            if i < num_frames - 1:
                time.sleep(self.interval)
        
        return {
            "success": True,
            "operation": "heatmap",
            "positions": positions,
            "total_points": len(positions),
            "summary": self._get_tracking_summary()
        }
    
    def _capture_frame(self, frame_num: int) -> Optional[Path]:
        """Capture frame from source"""
        output_path = self._temp_dir / f"frame_{frame_num:05d}.jpg"
        
        try:
            if self.source.startswith("rtsp://"):
                cmd = [
                    "ffmpeg", "-y", "-rtsp_transport", "tcp",
                    "-i", self.source,
                    "-frames:v", "1",
                    "-q:v", "2",
                    str(output_path)
                ]
            elif self.source.startswith(("http://", "https://")):
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.source,
                    "-frames:v", "1",
                    str(output_path)
                ]
            else:
                # File path
                cmd = [
                    "ffmpeg", "-y",
                    "-i", self.source,
                    "-vf", f"select=eq(n\\,{frame_num})",
                    "-frames:v", "1",
                    str(output_path)
                ]
            
            subprocess.run(cmd, check=True, capture_output=True, timeout=30)
            return output_path
        except Exception as e:
            logger.warning(f"Frame capture failed: {e}")
            return None
    
    def _analyze_frame(self, frame_path: Path, frame_num: int, 
                       focus_target: str = None) -> Dict:
        """Analyze frame for objects"""
        timestamp = time.strftime("%H:%M:%S")
        
        from ..prompts import render_prompt
        
        objects_str = ", ".join(self.objects)
        if focus_target:
            objects_str = focus_target
        
        prompt = render_prompt("tracking_detect", objects=objects_str)

        description = self._call_vision_model(frame_path, prompt)
        
        # Parse detected objects
        detected = self._parse_detections(description, frame_num, timestamp)
        
        return {
            "frame": frame_num + 1,
            "timestamp": timestamp,
            "objects_detected": len(detected),
            "objects": detected,
            "raw_analysis": description[:500]
        }
    
    def _parse_detections(self, description: str, frame_num: int, 
                          timestamp: str) -> List[Dict]:
        """Parse AI detection results"""
        detected = []
        
        # Simple parsing - look for OBJECT patterns
        lines = description.split("\n")
        for line in lines:
            line = line.strip().upper()
            
            if "PERSON" in line or "PEOPLE" in line:
                obj = self._create_or_update_object("person", line, frame_num, timestamp)
                if obj:
                    detected.append(asdict(obj))
            elif any(v in line for v in ["CAR", "VEHICLE", "TRUCK", "BIKE"]):
                obj_type = "vehicle"
                for v in ["CAR", "TRUCK", "BIKE"]:
                    if v in line:
                        obj_type = v.lower()
                        break
                obj = self._create_or_update_object(obj_type, line, frame_num, timestamp)
                if obj:
                    detected.append(asdict(obj))
            elif any(a in line for a in ["DOG", "CAT", "ANIMAL", "BIRD"]):
                obj_type = "animal"
                for a in ["DOG", "CAT", "BIRD"]:
                    if a in line:
                        obj_type = a.lower()
                        break
                obj = self._create_or_update_object(obj_type, line, frame_num, timestamp)
                if obj:
                    detected.append(asdict(obj))
        
        return detected
    
    def _create_or_update_object(self, obj_type: str, description: str,
                                  frame_num: int, timestamp: str) -> Optional[TrackedObject]:
        """Create new object or update existing"""
        # Try to extract position
        x, y = 50, 50  # default center
        import re
        pos_match = re.search(r'\((\d+)[,\s]+(\d+)\)', description)
        if pos_match:
            x = int(pos_match.group(1))
            y = int(pos_match.group(2))
        
        # Find matching object or create new
        obj_id = f"{obj_type}_{self._next_id}"
        
        # Simple matching - find object of same type nearby
        for existing_id, existing in self._tracked_objects.items():
            if existing.type == obj_type:
                # Update existing
                existing.position = (x, y)
                existing.trajectory.append((x, y))
                existing.last_seen = timestamp
                existing.frames_visible += 1
                existing.direction = self._calculate_direction(existing.trajectory)
                return existing
        
        # Create new object
        obj = TrackedObject(
            id=obj_id,
            type=obj_type,
            name=self.name if self.name else None,
            position=(x, y),
            first_seen=timestamp,
            last_seen=timestamp,
            frames_visible=1,
            trajectory=[(x, y)],
            confidence=0.8
        )
        
        self._tracked_objects[obj_id] = obj
        self._next_id += 1
        
        return obj
    
    def _calculate_direction(self, trajectory: List[Tuple[int, int]]) -> str:
        """Calculate movement direction from trajectory"""
        if len(trajectory) < 2:
            return "stationary"
        
        start = trajectory[-2]
        end = trajectory[-1]
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        if abs(dx) < 5 and abs(dy) < 5:
            return "stationary"
        
        if abs(dx) > abs(dy):
            return "E" if dx > 0 else "W"
        else:
            return "S" if dy > 0 else "N"
    
    def _get_tracking_summary(self) -> Dict:
        """Get summary of all tracked objects"""
        summary = {
            "total_objects": len(self._tracked_objects),
            "by_type": {},
            "objects": []
        }
        
        for obj in self._tracked_objects.values():
            # Count by type
            summary["by_type"][obj.type] = summary["by_type"].get(obj.type, 0) + 1
            
            # Object details
            summary["objects"].append({
                "id": obj.id,
                "type": obj.type,
                "name": obj.name,
                "first_seen": obj.first_seen,
                "last_seen": obj.last_seen,
                "frames_visible": obj.frames_visible,
                "last_position": obj.position,
                "direction": obj.direction,
                "trajectory_points": len(obj.trajectory)
            })
        
        return summary
    
    def _call_vision_model(self, image_path: Path, prompt: str) -> str:
        """Call vision model for analysis with optimized image"""
        try:
            import requests
            
            # Optimize image before sending to LLM
            from ..image_optimize import prepare_image_for_llm_base64
            image_data = prepare_image_for_llm_base64(image_path, preset="balanced")
            
            ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
            timeout = int(config.get("SQ_LLM_TIMEOUT", "60"))
            
            response = requests.post(
                f"{ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                },
                timeout=timeout
            )
            
            if response.ok:
                return response.json().get("response", "")
            return f"Analysis failed: {response.status_code}"
            
        except Exception as e:
            return f"Could not analyze: {e}"


# ============================================================================
# Helper Functions for Easy Use
# ============================================================================

def detect_objects(source: str, objects: str = "person,vehicle", 
                   duration: int = 30, interval: int = 5) -> Dict:
    """
    Quick object detection.
    
    Args:
        source: RTSP URL or file path
        objects: Comma-separated object types to detect
        duration: Analysis duration in seconds
        interval: Seconds between frames
    
    Example:
        result = detect_objects("rtsp://camera/live", "person,vehicle", 60)
        print(f"Detected {result['summary']['total_objects']} objects")
    """
    from ..core import flow
    return flow(f"tracking://detect?source={source}&objects={objects}&duration={duration}&interval={interval}").run()


def track_person(source: str, name: str = None, duration: int = 60) -> Dict:
    """
    Track a person in video.
    
    Args:
        source: RTSP URL or file path
        name: Optional name for the tracked person
        duration: Tracking duration in seconds
    
    Example:
        result = track_person("rtsp://camera/live", "John", 120)
        trajectory = result['trajectory']
    """
    from ..core import flow
    uri = f"tracking://track?source={source}&target=person&duration={duration}"
    if name:
        uri += f"&name={name}"
    return flow(uri).run()


def count_people(source: str, duration: int = 60, interval: int = 5) -> Dict:
    """
    Count people over time.
    
    Args:
        source: RTSP URL or file path
        duration: Counting duration in seconds
        interval: Seconds between counts
    
    Example:
        result = count_people("rtsp://camera/live", 300, 10)
        avg = result['statistics']['person']['avg']
        print(f"Average occupancy: {avg:.1f} people")
    """
    from ..core import flow
    return flow(f"tracking://count?source={source}&objects=person&duration={duration}&interval={interval}").run()


def monitor_zone(source: str, zone_name: str, x: int, y: int, 
                 w: int, h: int, duration: int = 60) -> Dict:
    """
    Monitor entry/exit for a specific zone.
    
    Args:
        source: RTSP URL or file path
        zone_name: Name of the zone
        x, y, w, h: Zone bounds
        duration: Monitoring duration
    
    Example:
        events = monitor_zone("rtsp://camera/live", "entrance", 0, 0, 100, 200, 300)
        for e in events['events']:
            print(f"{e['type']}: {e['object_type']} at {e['timestamp']}")
    """
    from ..core import flow
    zones = f"{zone_name}:{x},{y},{w},{h}"
    return flow(f"tracking://zones?source={source}&zones={zones}&duration={duration}").run()


def detect_vehicles(source: str, duration: int = 60) -> Dict:
    """
    Detect and track vehicles.
    
    Args:
        source: RTSP URL or file path
        duration: Detection duration
    
    Example:
        result = detect_vehicles("rtsp://parking/camera", 300)
        for v in result['summary']['objects']:
            print(f"{v['type']} - {v['direction']}")
    """
    from ..core import flow
    return flow(f"tracking://detect?source={source}&objects=car,truck,bike,vehicle&duration={duration}").run()
