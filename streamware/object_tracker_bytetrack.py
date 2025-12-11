"""
Object Tracker using ByteTrack for Streamware

Replaces the simple IoU-based tracker with ByteTrack via Supervision.
Provides more stable tracking and better handling of occlusions.

Features:
- ByteTrack association via Supervision
- Track state management (new/stable/lost)
- Motion direction detection (preserved from original)
- Compatible API with existing ObjectTracker

Usage:
    from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
    
    tracker = ObjectTrackerByteTrack(focus="person")
    result = tracker.update(detections)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
import math
import numpy as np

logger = logging.getLogger(__name__)

# Import existing types from original tracker
from .object_tracker import (
    Direction, ObjectState, BoundingBox, TrackedObject, 
    TrackingResult, extract_detections_from_regions
)


class ObjectTrackerByteTrack:
    """
    Multi-object tracker using ByteTrack via Supervision.
    
    Provides more stable tracking than simple IoU association.
    Maintains compatibility with existing ObjectTracker API.
    """
    
    def __init__(
        self,
        focus: str = "person",
        max_lost_frames: int = 90,  # ~3 seconds at 30fps
        track_activation_threshold: float = 0.25,
        minimum_matching_threshold: float = 0.8,
        frame_rate: int = 30,
        min_stable_frames: int = 3,
    ):
        """
        Initialize ByteTrack-based tracker.
        
        Args:
            focus: Object type to track (person, vehicle, etc.)
            max_lost_frames: Frames before marking object as gone
            track_activation_threshold: Min confidence for new tracks
            minimum_matching_threshold: IoU threshold for matching
            frame_rate: Video frame rate for tracker
            min_stable_frames: Frames before considering track stable
        """
        self.focus = focus
        self.max_lost_frames = max_lost_frames
        self.min_stable_frames = min_stable_frames
        self.frame_rate = frame_rate
        
        # Initialize ByteTrack
        try:
            import supervision as sv
            self.tracker = sv.ByteTrack(
                track_activation_threshold=track_activation_threshold,
                lost_track_buffer=max_lost_frames,
                minimum_matching_threshold=minimum_matching_threshold,
                frame_rate=frame_rate,
            )
            self.sv = sv
            logger.info("ByteTrack initialized successfully")
        except ImportError:
            logger.error("supervision package not found. Install with: pip install supervision")
            raise
        
        # Track state management
        self._tracked_objects: Dict[int, TrackedObject] = {}
        self._track_frames: Dict[int, int] = {}  # track_id -> frames_seen
        self._prev_track_ids: Set[int] = set()
        self._next_id = 1
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
        
        # Convert detections to Supervision format
        sv_detections = self._convert_to_supervision(detections)
        
        # Update ByteTrack
        sv_detections = self.tracker.update_with_detections(sv_detections)
        
        # Detect state changes
        current_ids = self._get_current_ids(sv_detections)
        lost_tracks = self._prev_track_ids - current_ids
        self._prev_track_ids = current_ids
        
        # Update tracked objects
        new_objects, lost_objects, entries, exits = self._update_tracks(
            sv_detections, lost_tracks, timestamp
        )
        
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
    
    def _get_current_ids(self, sv_detections) -> set:
        """Extract current track IDs from Supervision detections."""
        if sv_detections.tracker_id is not None:
            return set(sv_detections.tracker_id)
        return set()
    
    def _update_tracks(self, sv_detections, lost_tracks: set, timestamp: float):
        """Update tracked objects and return event lists."""
        new_objects = []
        lost_objects = []
        entries = []
        exits = []
        
        # Update existing/new tracks
        if sv_detections.tracker_id is not None:
            for i, track_id in enumerate(sv_detections.tracker_id):
                obj = self._update_single_track(sv_detections, i, track_id, timestamp)
                if obj and obj.state == ObjectState.NEW:
                    new_objects.append(obj)
                    entries.append(obj)
        
        # Handle lost tracks
        for track_id in lost_tracks:
            obj = self._handle_lost_track(track_id)
            if obj:
                lost_objects.append(obj)
                exits.append(obj)
        
        return new_objects, lost_objects, entries, exits
    
    def _update_single_track(self, sv_detections, i: int, track_id: int, timestamp: float):
        """Update a single track and return the object if new."""
        # Update frame counter
        self._track_frames[track_id] = self._track_frames.get(track_id, 0) + 1
        
        # Get detection data and convert to normalized coordinates
        bbox = sv_detections.xyxy[i]
        x, y, w, h = self._normalize_bbox(bbox)
        
        # Create/update TrackedObject
        if track_id in self._tracked_objects:
            obj = self._tracked_objects[track_id]
            obj.bbox = BoundingBox(x=x, y=y, w=w, h=h)
            obj.update_position(x, y, timestamp)
            
            # Update state from NEW to TRACKED if stable enough
            if obj.state == ObjectState.NEW and self._track_frames[track_id] >= self.min_stable_frames:
                obj.state = ObjectState.TRACKED
                obj.direction = Direction.STATIC
            
            return None  # Not a new object
        else:
            # New track
            obj = self._create_new_track(track_id, x, y, w, h, timestamp)
            self._tracked_objects[track_id] = obj
            self._total_tracked += 1
            return obj
    
    def _normalize_bbox(self, bbox) -> tuple:
        """Convert pixel bbox to normalized coordinates."""
        frame_w, frame_h = 1920, 1080  # TODO: Get actual frame size from detector
        x = ((bbox[0] + bbox[2]) / 2) / frame_w
        y = ((bbox[1] + bbox[3]) / 2) / frame_h
        w = (bbox[2] - bbox[0]) / frame_w
        h = (bbox[3] - bbox[1]) / frame_h
        return x, y, w, h
    
    def _create_new_track(self, track_id: int, x: float, y: float, w: float, h: float, timestamp: float):
        """Create a new tracked object."""
        obj = TrackedObject(
            id=track_id,
            object_type=self.focus,
            bbox=BoundingBox(x=x, y=y, w=w, h=h),
            state=ObjectState.NEW,
            first_seen=timestamp,
            last_seen=timestamp,
        )
        obj.update_position(x, y, timestamp)
        obj.direction = Direction.ENTERING
        
        # Don't mark as stable immediately - let it be NEW for entry events
        # State will be updated to TRACKED in subsequent updates
        
        return obj
    
    def _handle_lost_track(self, track_id: int):
        """Handle a lost track and return the object."""
        if track_id in self._tracked_objects:
            obj = self._tracked_objects[track_id]
            obj.state = ObjectState.GONE
            del self._tracked_objects[track_id]
            self._track_frames.pop(track_id, None)
            return obj
        return None
    
    def _convert_to_supervision(self, detections: List[Dict]):
        """Convert detection dicts to Supervision Detections format."""
        if not detections:
            return self.sv.Detections.empty()
        
        # Convert to pixel coordinates (assuming 1920x1080)
        frame_w, frame_h = 1920, 1080
        
        xyxy = []
        confidence = []
        class_id = []
        
        for det in detections:
            x = det.get("x", 0.5) * frame_w
            y = det.get("y", 0.5) * frame_h
            w = det.get("w", 0.1) * frame_w
            h = det.get("h", 0.2) * frame_h
            
            # Convert center to corners
            x1 = x - w/2
            y1 = y - h/2
            x2 = x + w/2
            y2 = y + h/2
            
            xyxy.append([x1, y1, x2, y2])
            confidence.append(det.get("confidence", 0.5))
            class_id.append(0)  # Single class for now
        
        return self.sv.Detections(
            xyxy=np.array(xyxy),
            confidence=np.array(confidence),
            class_id=np.array(class_id),
        )
    
    def get_stable_tracks(self) -> List[int]:
        """Return track IDs that have been seen for min_stable_frames."""
        return [tid for tid, frames in self._track_frames.items()
                if frames >= self.min_stable_frames and tid in self._prev_track_ids]
    
    def reset(self):
        """Reset tracker state."""
        self._tracked_objects.clear()
        self._track_frames.clear()
        self._prev_track_ids.clear()
        self._next_id = 1
        self._total_tracked = 0
        self.tracker.reset()
    
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


# Factory function for easy migration
def create_object_tracker(
    use_bytetrack: bool = True,
    focus: str = "person",
    **kwargs
):
    """
    Create appropriate object tracker instance.
    
    Args:
        use_bytetrack: If True, use ByteTrack-based tracker
        focus: Object type to track
        **kwargs: Additional arguments passed to tracker
        
    Returns:
        ObjectTracker or ObjectTrackerByteTrack instance
    """
    if use_bytetrack:
        return ObjectTrackerByteTrack(focus=focus, **kwargs)
    else:
        from .object_tracker import ObjectTracker
        return ObjectTracker(focus=focus, **kwargs)
