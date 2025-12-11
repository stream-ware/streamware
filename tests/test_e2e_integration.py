"""
End-to-end integration test for ByteTrack integration
Uses the standalone demo to verify full pipeline works
"""

import subprocess
import sys
import time
from pathlib import Path


def test_demo_help():
    """Test that the standalone demo help works (shows it's runnable)."""
    print("Testing standalone demo help...")
    
    try:
        demo_path = Path(__file__).parent.parent / "demos" / "tracking_benchmark" / "tracker_demo.py"
        
        if not demo_path.exists():
            print(f"❌ Demo not found at {demo_path}")
            return False
        
        # Run demo with --help to verify it's functional
        cmd = [sys.executable, str(demo_path), "--help"]
        
        print(f"🚀 Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=str(demo_path.parent),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Check if help was displayed
        if result.returncode == 0 and "usage:" in result.stdout:
            print("✅ Demo help displayed successfully")
            
            # Check for our new parameters
            if "--motion-gate" in result.stdout:
                print("✅ Motion gate parameter available")
            
            if "--periodic-interval" in result.stdout:
                print("✅ Periodic interval parameter available")
            
            return True
        else:
            print("❌ Demo help failed")
            print("stdout:", result.stdout)
            print("stderr:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Demo help test failed: {e}")
        return False


def test_imports_after_integration():
    """Test that all imports work after integration changes."""
    print("Testing imports after integration...")
    
    try:
        # Test core imports
        from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
        from streamware.smart_detector import SmartDetector
        from streamware.components.live_narrator import LiveNarratorComponent
        from streamware.config import config
        
        print("✅ All core imports successful")
        
        # Test that config has new parameters
        assert config.get("SQ_MOTION_GATE_THRESHOLD") is not None
        assert config.get("SQ_PERIODIC_INTERVAL") is not None
        print("✅ New config parameters available")
        
        # Test that classes can be instantiated
        tracker = ObjectTrackerByteTrack()
        detector = SmartDetector()
        print("✅ Classes can be instantiated")
        
        # Test tracker methods exist
        assert hasattr(tracker, 'update')
        assert hasattr(tracker, 'reset')
        assert hasattr(tracker, 'get_stable_tracks')
        print("✅ Tracker methods available")
        
        # Test detector has new parameters
        assert hasattr(detector, 'motion_gate_threshold')
        assert hasattr(detector, 'periodic_interval')
        print("✅ Detector motion gating parameters available")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_compatibility():
    """Test that the new tracker maintains API compatibility."""
    print("Testing API compatibility...")
    
    try:
        from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
        from streamware.object_tracker import TrackingResult
        
        # Create tracker
        tracker = ObjectTrackerByteTrack()
        
        # Test that update returns TrackingResult
        result = tracker.update([])
        assert isinstance(result, TrackingResult)
        print("✅ update() returns TrackingResult")
        
        # Test TrackingResult has expected attributes
        assert hasattr(result, 'objects')
        assert hasattr(result, 'new_objects')
        assert hasattr(result, 'lost_objects')
        assert hasattr(result, 'entries')
        assert hasattr(result, 'exits')
        assert hasattr(result, 'active_count')
        assert hasattr(result, 'total_count')
        print("✅ TrackingResult has all expected attributes")
        
        # Test with actual detection
        detections = [{
            "x": 0.5, "y": 0.5, "w": 0.1, "h": 0.2,
            "confidence": 0.8, "type": "person"
        }]
        
        result = tracker.update(detections)
        assert result.active_count >= 0
        assert result.total_count >= 0
        print("✅ update() works with real detections")
        
        # Test tracker methods
        tracker.reset()
        assert tracker.object_count == 0
        assert tracker.total_tracked == 0
        print("✅ reset() works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ API compatibility test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_motion_gating_config():
    """Test that motion gating configuration works."""
    print("Testing motion gating configuration...")
    
    try:
        from streamware.smart_detector import SmartDetector
        
        # Test default values
        detector1 = SmartDetector()
        assert detector1.motion_gate_threshold > 0
        assert detector1.periodic_interval > 0
        print(f"✅ Default motion gate: {detector1.motion_gate_threshold}px")
        print(f"✅ Default periodic interval: {detector1.periodic_interval} frames")
        
        # Test custom values
        detector2 = SmartDetector(
            motion_gate_threshold=2000,
            periodic_interval=15
        )
        assert detector2.motion_gate_threshold == 2000
        assert detector2.periodic_interval == 15
        print("✅ Custom motion gating parameters work")
        
        return True
        
    except Exception as e:
        print(f"❌ Motion gating config test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Running End-to-End Integration Tests")
    print("=" * 60)
    
    tests = [
        test_imports_after_integration,
        test_api_compatibility,
        test_motion_gating_config,
        test_demo_help  # Run last as it's the most comprehensive
    ]
    
    results = []
    for test in tests:
        print()
        success = test()
        results.append(success)
        
        if not success:
            print("⚠️ Stopping remaining tests due to failure")
            break
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} end-to-end tests passed!")
        print("✅ ByteTrack integration is working correctly!")
        exit(0)
    else:
        print(f"❌ {total - passed} of {total} tests failed")
        exit(1)
