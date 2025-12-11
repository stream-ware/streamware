"""
Unit tests for ObjectTrackerByteTrack

Tests the ByteTrack-based tracker implementation.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import numpy as np

# Try importing, but handle gracefully if supervision is not available
try:
    import supervision as sv
    SUPERVISION_AVAILABLE = True
except ImportError:
    SUPERVISION_AVAILABLE = False
    sv = None

from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
from streamware.object_tracker import (
    Direction, ObjectState, BoundingBox, TrackedObject, 
    TrackingResult
)


class TestObjectTrackerByteTrack:
    """Test suite for ObjectTrackerByteTrack."""
    
    @pytest.fixture
    def tracker(self):
        """Create a tracker instance for testing."""
        with patch('supervision.ByteTrack') as mock_bytetrack, \
             patch('supervision.Detections') as mock_detections_class:
            
            # Mock ByteTrack instance
            mock_bt_instance = Mock()
            mock_bt_instance.reset = Mock()
            mock_bytetrack.return_value = mock_bt_instance
            
            # Mock Detections.empty()
            mock_empty_detections = Mock()
            mock_empty_detections.tracker_id = None
            mock_detections_class.empty.return_value = mock_empty_detections
            
            tracker = ObjectTrackerByteTrack(
                focus="person",
                max_lost_frames=5,
                min_stable_frames=2,
                frame_rate=30,
            )
            
            # Store mock for later use
            tracker._mock_bytetrack = mock_bt_instance
            tracker._mock_detections_class = mock_detections_class
            return tracker
    
    def test_init(self, tracker):
        """Test tracker initialization."""
        assert tracker.focus == "person"
        assert tracker.max_lost_frames == 5
        assert tracker.min_stable_frames == 2
        assert tracker.frame_rate == 30
        assert tracker._total_tracked == 0
        assert tracker._next_id == 1
        assert len(tracker._tracked_objects) == 0
        assert len(tracker._track_frames) == 0
        assert len(tracker._prev_track_ids) == 0
    
    def test_update_empty_detections(self, tracker):
        """Test updating with no detections."""
        # Mock empty detections
        mock_detections = Mock()
        mock_detections.tracker_id = None
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        result = tracker.update([])
        
        assert isinstance(result, TrackingResult)
        assert result.active_count == 0
        assert result.total_count == 0
        assert len(result.objects) == 0
        assert len(result.new_objects) == 0
        assert len(result.lost_objects) == 0
    
    def test_update_new_detection(self, tracker):
        """Test updating with a new detection."""
        # Mock ByteTrack response with new track
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1])
        mock_detections.xyxy = np.array([[100, 100, 200, 200]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        result = tracker.update([{
            "x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1,
            "confidence": 0.8, "type": "person"
        }])
        
        assert result.active_count == 1
        assert result.total_count == 1
        assert len(result.objects) == 1
        assert len(result.new_objects) == 1
        assert len(result.entries) == 1
        
        obj = result.objects[0]
        assert obj.id == 1
        assert obj.object_type == "person"
        assert obj.state == ObjectState.NEW
        assert obj.direction == Direction.ENTERING
    
    def test_update_existing_track(self, tracker):
        """Test updating an existing track."""
        # First update - create track
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1])
        mock_detections.xyxy = np.array([[100, 100, 200, 200]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        tracker.update([{
            "x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1,
            "confidence": 0.8, "type": "person"
        }])
        
        # Second update - same track
        result2 = tracker.update([{
            "x": 0.16, "y": 0.16, "w": 0.05, "h": 0.1,
            "confidence": 0.8, "type": "person"
        }])
        
        assert result2.active_count == 1
        assert result2.total_count == 1  # No new track created
        assert len(result2.new_objects) == 0
        assert len(result2.lost_objects) == 0
        
        obj = result2.objects[0]
        assert obj.id == 1
        assert obj.frames_tracked == 2
    
    def test_track_becomes_stable(self, tracker):
        """Test that tracks become stable after min_stable_frames."""
        # Mock detections for same track
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1])
        mock_detections.xyxy = np.array([[100, 100, 200, 200]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        # First frame - new track
        result1 = tracker.update([{
            "x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1,
            "confidence": 0.8, "type": "person"
        }])
        assert result1.objects[0].state == ObjectState.NEW
        
        # Second frame - should become stable (min_stable_frames=2)
        result2 = tracker.update([{
            "x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1,
            "confidence": 0.8, "type": "person"
        }])
        assert result2.objects[0].state == ObjectState.TRACKED
    
    def test_lost_track_handling(self, tracker):
        """Test handling of lost tracks."""
        # Create track first
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1])
        mock_detections.xyxy = np.array([[100, 100, 200, 200]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        tracker.update([{
            "x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1,
            "confidence": 0.8, "type": "person"
        }])
        
        # Now track is lost (no detections)
        mock_detections.tracker_id = None
        result = tracker.update([])
        
        assert result.active_count == 0
        assert len(result.lost_objects) == 1
        assert len(result.exits) == 1
        
        lost_obj = result.lost_objects[0]
        assert lost_obj.id == 1
        assert lost_obj.state == ObjectState.GONE
    
    def test_multiple_tracks(self, tracker):
        """Test handling multiple simultaneous tracks."""
        # Mock two tracks
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1, 2])
        mock_detections.xyxy = np.array([
            [100, 100, 200, 200],  # Track 1
            [300, 300, 400, 400]   # Track 2
        ])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        result = tracker.update([
            {"x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1, "confidence": 0.8, "type": "person"},
            {"x": 0.35, "y": 0.35, "w": 0.05, "h": 0.1, "confidence": 0.7, "type": "person"}
        ])
        
        assert result.active_count == 2
        assert result.total_count == 2
        assert len(result.new_objects) == 2
        assert len(result.entries) == 2
        
        # Check both tracks have different IDs
        track_ids = {obj.id for obj in result.objects}
        assert track_ids == {1, 2}
    
    def test_get_stable_tracks(self, tracker):
        """Test getting stable track IDs."""
        # Create track and update it enough times
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1])
        mock_detections.xyxy = np.array([[100, 100, 200, 200]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        # Update track 3 times (min_stable_frames=2)
        for _ in range(3):
            tracker.update([{
                "x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1,
                "confidence": 0.8, "type": "person"
            }])
        
        stable_ids = tracker.get_stable_tracks()
        assert 1 in stable_ids
    
    def test_reset(self, tracker):
        """Test resetting tracker state."""
        # Create some tracks first
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1, 2])
        mock_detections.xyxy = np.array([[100, 100, 200, 200], [300, 300, 400, 400]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        tracker.update([
            {"x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1, "confidence": 0.8, "type": "person"},
            {"x": 0.35, "y": 0.35, "w": 0.05, "h": 0.1, "confidence": 0.7, "type": "person"}
        ])
        
        assert tracker.object_count == 2
        assert tracker.total_tracked == 2
        
        # Reset
        tracker.reset()
        
        assert tracker.object_count == 0
        assert tracker.total_tracked == 0
        assert len(tracker._tracked_objects) == 0
        assert len(tracker._track_frames) == 0
        assert len(tracker._prev_track_ids) == 0
        tracker.tracker.reset.assert_called_once()
    
    def test_get_object(self, tracker):
        """Test getting tracked object by ID."""
        # Create track
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1])
        mock_detections.xyxy = np.array([[100, 100, 200, 200]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        tracker.update([{
            "x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1,
            "confidence": 0.8, "type": "person"
        }])
        
        # Get existing object
        obj = tracker.get_object(1)
        assert obj is not None
        assert obj.id == 1
        
        # Get non-existing object
        obj = tracker.get_object(999)
        assert obj is None
    
    def test_get_all_objects(self, tracker):
        """Test getting all tracked objects."""
        # Create two tracks
        mock_detections = Mock()
        mock_detections.tracker_id = np.array([1, 2])
        mock_detections.xyxy = np.array([[100, 100, 200, 200], [300, 300, 400, 400]])
        tracker.tracker.update_with_detections.return_value = mock_detections
        
        tracker.update([
            {"x": 0.15, "y": 0.15, "w": 0.05, "h": 0.1, "confidence": 0.8, "type": "person"},
            {"x": 0.35, "y": 0.35, "w": 0.05, "h": 0.1, "confidence": 0.7, "type": "person"}
        ])
        
        all_objects = tracker.get_all_objects()
        assert len(all_objects) == 2
        
        ids = {obj.id for obj in all_objects}
        assert ids == {1, 2}
    
    def test_convert_to_supervision_empty(self, tracker):
        """Test converting empty detections to Supervision format."""
        result = tracker._convert_to_supervision([])
        assert result is not None  # Should return empty Detections
    
    def test_convert_to_supervision_with_data(self, tracker):
        """Test converting detections to Supervision format."""
        detections = [
            {"x": 0.5, "y": 0.5, "w": 0.1, "h": 0.2, "confidence": 0.8},
            {"x": 0.3, "y": 0.4, "w": 0.05, "h": 0.15, "confidence": 0.6}
        ]
        
        result = tracker._convert_to_supervision(detections)
        
        assert result is not None
        assert len(result.xyxy) == 2
        assert len(result.confidence) == 2
        assert len(result.class_id) == 2
    
    def test_normalize_bbox(self, tracker):
        """Test bbox normalization."""
        # Test with known values
        bbox = np.array([960, 540, 1440, 810])  # Center at (1200, 675) in 1920x1080
        x, y, w, h = tracker._normalize_bbox(bbox)
        
        assert abs(x - 0.625) < 0.001  # 1200/1920
        assert abs(y - 0.625) < 0.001  # 675/1080
        assert abs(w - 0.25) < 0.001   # 480/1920
        assert abs(h - 0.25) < 0.001   # 270/1080
    
    def test_create_new_track(self, tracker):
        """Test creating a new tracked object."""
        timestamp = time.time()
        obj = tracker._create_new_track(1, 0.5, 0.5, 0.1, 0.2, timestamp)
        
        assert obj.id == 1
        assert obj.object_type == "person"
        assert obj.state == ObjectState.NEW  # Not yet stable (frames=1)
        assert obj.direction == Direction.ENTERING
        assert obj.first_seen == timestamp
        assert obj.last_seen == timestamp
    
    def test_handle_lost_track(self, tracker):
        """Test handling a lost track."""
        # Create a track first
        timestamp = time.time()
        obj = tracker._create_new_track(1, 0.5, 0.5, 0.1, 0.2, timestamp)
        tracker._tracked_objects[1] = obj
        tracker._track_frames[1] = 5
        
        # Handle lost track
        lost_obj = tracker._handle_lost_track(1)
        
        assert lost_obj is not None
        assert lost_obj.id == 1
        assert lost_obj.state == ObjectState.GONE
        assert 1 not in tracker._tracked_objects
        assert 1 not in tracker._track_frames
        
        # Handle non-existent track
        lost_obj = tracker._handle_lost_track(999)
        assert lost_obj is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
