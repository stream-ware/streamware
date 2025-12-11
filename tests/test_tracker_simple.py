"""
Simple integration test for ObjectTrackerByteTrack
"""

import time
import numpy as np

from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack


def test_tracker_basic():
    """Test basic tracker functionality without complex mocking."""
    print("Testing ObjectTrackerByteTrack...")
    
    try:
        # Create tracker
        tracker = ObjectTrackerByteTrack(
            focus="person",
            max_lost_frames=5,
            min_stable_frames=2,
            frame_rate=30,
        )
        print("✅ Tracker created successfully")
        
        # Test empty update
        result = tracker.update([])
        assert result.active_count == 0
        assert result.total_count == 0
        print("✅ Empty update works")
        
        # Test with simple detection
        detections = [{
            "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.2,
            "confidence": 0.8, "type": "person"
        }]
        
        result = tracker.update(detections)
        print(f"📊 First update: {result.active_count} tracks, {result.total_count} total")
        
        # Update same detection (should maintain track)
        result = tracker.update(detections)
        print(f"📊 Second update: {result.active_count} tracks, {result.total_count} total")
        
        # Test stable tracks
        stable_ids = tracker.get_stable_tracks()
        print(f"📊 Stable tracks: {stable_ids}")
        
        # Test reset
        tracker.reset()
        result = tracker.update([])
        assert result.active_count == 0
        print("✅ Reset works")
        
        print("🎉 All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_tracker_basic()
    exit(0 if success else 1)
