"""
Object Tracker for Streamware

Tracks objects (people, vehicles, etc.) across video frames.
Assigns persistent IDs and calculates movement trajectories.

Features:
- Object ID assignment and tracking
- Movement direction detection (entering, exiting, left, right, etc.)
- Speed estimation
- Zone-based alerts (crossed line, entered zone)
- Multi-object tracking

Usage:
    from streamware.object_tracker import ObjectTracker
    
    tracker = ObjectTracker(focus="person")
    
    # For each frame:
    result = tracker.update(frame_path, detections)
    
    for obj in result.objects:
        print(f"Object {obj.id}: {obj.direction} at ({obj.x}, {obj.y})")
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import math

logger = logging.getLogger(__name__)


class Direction(Enum):
    """Movement direction."""
    UNKNOWN = "unknown"
    STATIONARY = "stationary"
    ENTERING = "entering"
    EXITING = "exiting"
    MOVING_LEFT = "moving_left"
    MOVING_RIGHT = "moving_right"
    MOVING_UP = "moving_up"
    MOVING_DOWN = "moving_down"
    APPROACHING = "approaching"  # Moving toward camera
    LEAVING = "leaving"  # Moving away from camera


class ObjectState(Enum):
    """Object tracking state."""
    NEW = "new"  # Just appeared
    TRACKED = "tracked"  # Being tracked
    LOST = "lost"  # Temporarily lost
    GONE = "gone"  # Left the frame


@dataclass
class BoundingBox:
    """Bounding box for detected object."""
    x: float  # Center X (0-1 normalized)
    y: float  # Center Y (0-1 normalized)
    w: float  # Width (0-1 normalized)
    h: float  # Height (0-1 normalized)
    
    @property
    def area(self) -> float:
        return self.w * self.h
    
    @property
    def center(self) -> Tuple[float, float]:
        return (self.x, self.y)
    
    def distance_to(self, other: 'BoundingBox') -> float:
        """Euclidean distance to another box center."""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def iou(self, other: 'BoundingBox') -> float:
        """Intersection over Union with another box."""
        # Convert to corners
        x1_a, y1_a = self.x - self.w/2, self.y - self.h/2
        x2_a, y2_a = self.x + self.w/2, self.y + self.h/2
        x1_b, y1_b = other.x - other.w/2, other.y - other.h/2
        x2_b, y2_b = other.x + other.w/2, other.y + other.h/2
        
        # Intersection
        xi1 = max(x1_a, x1_b)
        yi1 = max(y1_a, y1_b)
        xi2 = min(x2_a, x2_b)
        yi2 = min(y2_a, y2_b)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        inter_area = (xi2 - xi1) * (yi2 - yi1)
        union_area = self.area + other.area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0


@dataclass
class TrackedObject:
    """A tracked object across frames."""
    id: int
    object_type: str  # person, vehicle, etc.
    bbox: BoundingBox
    state: ObjectState = ObjectState.NEW
    direction: Direction = Direction.UNKNOWN
    speed: float = 0.0  # pixels per second (normalized)
    
    # History
    positions: List[Tuple[float, float, float]] = field(default_factory=list)  # (x, y, timestamp)
    first_seen: float = 0.0
    last_seen: float = 0.0
    frames_tracked: int = 0
    frames_lost: int = 0
    
    # Zone info
    zone: str = ""  # left, center, right, top, bottom
    entry_zone: str = ""  # Where object entered
    
    @property
    def age(self) -> float:
        """Time since first seen (seconds)."""
        return self.last_seen - self.first_seen if self.first_seen else 0
    
    @property
    def is_moving(self) -> bool:
        return self.direction not in (Direction.STATIONARY, Direction.UNKNOWN)
    
    def update_position(self, x: float, y: float, timestamp: float):
        """Update object position and calculate direction."""
        self.positions.append((x, y, timestamp))
        
        # Keep last 30 positions for trajectory
        if len(self.positions) > 30:
            self.positions.pop(0)
        
        self.last_seen = timestamp
        self.frames_tracked += 1
        self.frames_lost = 0
        
        # Calculate direction and speed
        if len(self.positions) >= 2:
            self._calculate_movement()
        
        # Update zone
        self._update_zone(x, y)
    
    def _calculate_movement(self):
        """Calculate movement direction and speed from position history."""
        if len(self.positions) < 2:
            return
        
        # Use last few positions for smoothing
        n = min(5, len(self.positions))
        recent = self.positions[-n:]
        
        # Average velocity
        dx_total = recent[-1][0] - recent[0][0]
        dy_total = recent[-1][1] - recent[0][1]
        dt = recent[-1][2] - recent[0][2]
        
        if dt <= 0:
            return
        
        vx = dx_total / dt  # normalized units per second
        vy = dy_total / dt
        
        self.speed = math.sqrt(vx**2 + vy**2)
        
        # Minimum movement threshold (1% of frame per second)
        min_speed = 0.01
        
        if self.speed < min_speed:
            self.direction = Direction.STATIONARY
            return
        
        # Determine primary direction
        abs_vx = abs(vx)
        abs_vy = abs(vy)
        
        # Horizontal vs vertical dominant
        if abs_vx > abs_vy * 1.5:
            # Primarily horizontal
            if vx > 0:
                self.direction = Direction.MOVING_RIGHT
                # Check if exiting
                if recent[-1][0] > 0.85:
                    self.direction = Direction.EXITING
            else:
                self.direction = Direction.MOVING_LEFT
                if recent[-1][0] < 0.15:
                    self.direction = Direction.EXITING
        elif abs_vy > abs_vx * 1.5:
            # Primarily vertical
            if vy > 0:
                self.direction = Direction.MOVING_DOWN
                # Moving down = approaching camera (getting bigger)
                if recent[-1][1] > 0.85:
                    self.direction = Direction.APPROACHING
            else:
                self.direction = Direction.MOVING_UP
                # Moving up = leaving camera (getting smaller)
                if recent[-1][1] < 0.15:
                    self.direction = Direction.LEAVING
        else:
            # Diagonal movement - use zone position
            if recent[-1][0] > 0.8 or recent[-1][0] < 0.2:
                self.direction = Direction.EXITING
            elif recent[-1][1] > 0.8:
                self.direction = Direction.APPROACHING
            elif recent[-1][1] < 0.2:
                self.direction = Direction.LEAVING
    
    def _update_zone(self, x: float, y: float):
        """Update zone based on position."""
        # Horizontal zone
        if x < 0.33:
            h_zone = "left"
        elif x > 0.66:
            h_zone = "right"
        else:
            h_zone = "center"
        
        # Vertical zone
        if y < 0.33:
            v_zone = "top"
        elif y > 0.66:
            v_zone = "bottom"
        else:
            v_zone = "middle"
        
        self.zone = f"{h_zone}_{v_zone}"
        
        # Record entry zone
        if not self.entry_zone and self.state == ObjectState.NEW:
            self.entry_zone = self.zone
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        type_cap = self.object_type.title()
        
        if self.state == ObjectState.NEW:
            return f"{type_cap} appeared in {self.zone.replace('_', ' ')}"
        elif self.state == ObjectState.GONE:
            return f"{type_cap} left the frame"
        elif self.direction == Direction.STATIONARY:
            return f"{type_cap} stationary in {self.zone.replace('_', ' ')}"
        elif self.direction == Direction.ENTERING:
            return f"{type_cap} entering from {self.entry_zone.replace('_', ' ')}"
        elif self.direction == Direction.EXITING:
            return f"{type_cap} exiting to {self.zone.replace('_', ' ')}"
        elif self.direction == Direction.APPROACHING:
            return f"{type_cap} approaching camera"
        elif self.direction == Direction.LEAVING:
            return f"{type_cap} moving away from camera"
        elif self.direction == Direction.MOVING_LEFT:
            return f"{type_cap} moving left"
        elif self.direction == Direction.MOVING_RIGHT:
            return f"{type_cap} moving right"
        else:
            return f"{type_cap} in {self.zone.replace('_', ' ')}"


@dataclass
class TrackingResult:
    """Result of tracking update."""
    objects: List[TrackedObject]
    new_objects: List[TrackedObject]
    lost_objects: List[TrackedObject]
    
    # Events
    entries: List[TrackedObject] = field(default_factory=list)
    exits: List[TrackedObject] = field(default_factory=list)
    
    # Summary
    total_count: int = 0
    active_count: int = 0
    
    def get_summary(self) -> str:
        """Get human-readable summary of all tracked objects."""
        if not self.objects:
            return "No objects detected"
        
        summaries = [obj.get_summary() for obj in self.objects if obj.state != ObjectState.LOST]
        return ". ".join(summaries)
    
    def has_movement(self) -> bool:
        """Check if any object is moving."""
        return any(obj.is_moving for obj in self.objects)
    
    def has_entries(self) -> bool:
        return len(self.entries) > 0
    
    def has_exits(self) -> bool:
        return len(self.exits) > 0


class ObjectTracker:
    """
    Multi-object tracker for video frames.
    
    Uses simple IoU-based association to match detections across frames.
    More sophisticated trackers (DeepSORT, ByteTrack) could be plugged in.
    """
    
    def __init__(
        self,
        focus: str = "person",
        max_lost_frames: int = 10,
        iou_threshold: float = 0.3,
        distance_threshold: float = 0.2,
    ):
        """
        Initialize tracker.
        
        Args:
            focus: Object type to track (person, vehicle, etc.)
            max_lost_frames: Frames before marking object as gone
            iou_threshold: Minimum IoU for association
            distance_threshold: Max distance for association (normalized)
        """
        self.focus = focus
        self.max_lost_frames = max_lost_frames
        self.iou_threshold = iou_threshold
        self.distance_threshold = distance_threshold
        
        self._next_id = 1
        self._tracked_objects: Dict[int, TrackedObject] = {}
        self._total_tracked = 0
    
    def update(
        self,
        detections: List[Dict],
        timestamp: float = None,
    ) -> TrackingResult:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of detection dicts with keys:
                - x, y: Center position (0-1 normalized)
                - w, h: Width, height (0-1 normalized)
                - confidence: Detection confidence
                - type: Object type (optional)
            timestamp: Current timestamp (default: time.time())
            
        Returns:
            TrackingResult with all tracked objects
        """
        if timestamp is None:
            timestamp = time.time()
        
        # Convert detections to BoundingBox
        det_boxes = []
        for det in detections:
            bbox = BoundingBox(
                x=det.get("x", 0.5),
                y=det.get("y", 0.5),
                w=det.get("w", 0.1),
                h=det.get("h", 0.2),
            )
            det_boxes.append((bbox, det.get("type", self.focus)))
        
        # Match detections to existing tracks
        matched, unmatched_dets, unmatched_tracks = self._associate(det_boxes)
        
        new_objects = []
        lost_objects = []
        entries = []
        exits = []
        
        # Update matched tracks
        for track_id, det_idx in matched:
            obj = self._tracked_objects[track_id]
            bbox, obj_type = det_boxes[det_idx]
            
            obj.bbox = bbox
            obj.update_position(bbox.x, bbox.y, timestamp)
            
            if obj.state == ObjectState.LOST:
                obj.state = ObjectState.TRACKED
            elif obj.state == ObjectState.NEW:
                obj.state = ObjectState.TRACKED
                entries.append(obj)
        
        # Create new tracks for unmatched detections
        for det_idx in unmatched_dets:
            bbox, obj_type = det_boxes[det_idx]
            
            obj = TrackedObject(
                id=self._next_id,
                object_type=obj_type,
                bbox=bbox,
                state=ObjectState.NEW,
                first_seen=timestamp,
                last_seen=timestamp,
            )
            obj.update_position(bbox.x, bbox.y, timestamp)
            obj.direction = Direction.ENTERING
            
            self._tracked_objects[self._next_id] = obj
            self._next_id += 1
            self._total_tracked += 1
            
            new_objects.append(obj)
            entries.append(obj)
        
        # Handle unmatched tracks (lost)
        for track_id in unmatched_tracks:
            obj = self._tracked_objects[track_id]
            obj.frames_lost += 1
            
            if obj.frames_lost >= self.max_lost_frames:
                obj.state = ObjectState.GONE
                lost_objects.append(obj)
                exits.append(obj)
            else:
                obj.state = ObjectState.LOST
        
        # Remove gone objects
        for obj in lost_objects:
            if obj.id in self._tracked_objects:
                del self._tracked_objects[obj.id]
        
        # Build result
        active_objects = list(self._tracked_objects.values())
        
        return TrackingResult(
            objects=active_objects,
            new_objects=new_objects,
            lost_objects=lost_objects,
            entries=entries,
            exits=exits,
            total_count=self._total_tracked,
            active_count=len(active_objects),
        )
    
    def _associate(
        self,
        det_boxes: List[Tuple[BoundingBox, str]],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Associate detections with existing tracks.
        
        Uses IoU and distance-based matching.
        
        Returns:
            (matched_pairs, unmatched_det_indices, unmatched_track_ids)
        """
        if not det_boxes or not self._tracked_objects:
            unmatched_dets = list(range(len(det_boxes)))
            unmatched_tracks = list(self._tracked_objects.keys())
            return [], unmatched_dets, unmatched_tracks
        
        # Compute cost matrix (IoU + distance)
        track_ids = list(self._tracked_objects.keys())
        costs = []
        
        for track_id in track_ids:
            obj = self._tracked_objects[track_id]
            row = []
            for det_bbox, _ in det_boxes:
                iou = obj.bbox.iou(det_bbox)
                dist = obj.bbox.distance_to(det_bbox)
                
                # Combined score (higher is better)
                if iou > self.iou_threshold or dist < self.distance_threshold:
                    score = iou + (1 - dist)
                else:
                    score = 0
                
                row.append(score)
            costs.append(row)
        
        # Greedy matching (simple, could use Hungarian algorithm for optimal)
        matched = []
        used_dets = set()
        used_tracks = set()
        
        # Sort by score and match greedily
        candidates = []
        for i, track_id in enumerate(track_ids):
            for j in range(len(det_boxes)):
                if costs[i][j] > 0:
                    candidates.append((costs[i][j], track_id, j))
        
        candidates.sort(reverse=True)
        
        for score, track_id, det_idx in candidates:
            if track_id not in used_tracks and det_idx not in used_dets:
                matched.append((track_id, det_idx))
                used_tracks.add(track_id)
                used_dets.add(det_idx)
        
        unmatched_dets = [i for i in range(len(det_boxes)) if i not in used_dets]
        unmatched_tracks = [tid for tid in track_ids if tid not in used_tracks]
        
        return matched, unmatched_dets, unmatched_tracks
    
    def reset(self):
        """Reset tracker state."""
        self._tracked_objects.clear()
        self._next_id = 1
        self._total_tracked = 0
    
    @property
    def object_count(self) -> int:
        """Current number of tracked objects."""
        return len(self._tracked_objects)
    
    @property
    def total_tracked(self) -> int:
        """Total objects tracked since start."""
        return self._total_tracked
    
    def get_object(self, obj_id: int) -> Optional[TrackedObject]:
        """Get tracked object by ID."""
        return self._tracked_objects.get(obj_id)
    
    def get_all_objects(self) -> List[TrackedObject]:
        """Get all currently tracked objects."""
        return list(self._tracked_objects.values())


def extract_detections_from_regions(motion_regions: List[Dict]) -> List[Dict]:
    """
    Convert motion regions from SmartDetector to detection format for tracker.
    
    Args:
        motion_regions: List of dicts with x, y, w, h (pixel coords)
        
    Returns:
        List of detection dicts with normalized coordinates
    """
    detections = []
    
    for region in motion_regions:
        # Assume 1920x1080 if not specified
        frame_w = region.get("frame_width", 1920)
        frame_h = region.get("frame_height", 1080)
        
        # Normalize coordinates
        x = (region.get("x", 0) + region.get("w", 0) / 2) / frame_w
        y = (region.get("y", 0) + region.get("h", 0) / 2) / frame_h
        w = region.get("w", 100) / frame_w
        h = region.get("h", 200) / frame_h
        
        detections.append({
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "confidence": region.get("confidence", 0.5),
            "type": region.get("type", "person"),
        })
    
    return detections
