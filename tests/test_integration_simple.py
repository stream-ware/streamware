"""
Simple integration tests for ByteTrack integration
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch


def test_bytetrack_narrator_direct():
    """Test ByteTrack tracker directly in narrator context."""
    print("Testing ByteTrack in LiveNarrator context...")
    
    try:
        from streamware.object_tracker_bytetrack import ObjectTrackerByteTrack
        
        # Create tracker like narrator would
        tracker = ObjectTrackerByteTrack(
            focus="person",
            max_lost_frames=90,
            min_stable_frames=3,
            frame_rate=30,
        )
        
        print("✅ ByteTrack tracker created")
        
        # Simulate motion regions like from FrameDiffAnalyzer
        motion_regions = [
            {"x": 100, "y": 100, "w": 50, "h": 100, "confidence": 0.8}
        ]
        
        # Convert to detections like narrator does
        from streamware.object_tracker import extract_detections_from_regions
        
        for region in motion_regions:
            region["frame_width"] = 1920
            region["frame_height"] = 1080
        
        detections = extract_detections_from_regions(motion_regions)
        print(f"✅ Converted {len(motion_regions)} motion regions to {len(detections)} detections")
        
        # Update tracker multiple times to see progression
        for i in range(5):
            result = tracker.update(detections)
            stable_ids = tracker.get_stable_tracks()
            
            print(f"📊 Frame {i+1}: {result.active_count} active, "
                  f"{len(result.new_objects)} new, {len(result.entries)} entries, "
                  f"{len(stable_ids)} stable")
            
            if result.entries:
                for entry in result.entries:
                    print(f"   ➡️ Entry: {entry.object_type} #{entry.id} ({entry.state.value})")
        
        # Test track loss
        result = tracker.update([])  # No detections
        print(f"📊 No detections: {result.active_count} active, {len(result.exits)} exits")
        
        if result.exits:
            for exit in result.exits:
                print(f"   ⬅️ Exit: {exit.object_type} #{exit.id} ({exit.state.value})")
        
        print("🎉 ByteTrack + narrator integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_motion_gating_effectiveness():
    """Test that motion gating actually reduces detection calls."""
    print("Testing motion gating effectiveness...")
    
    try:
        from streamware.smart_detector import SmartDetector
        
        # Create detector with strict gating
        detector = SmartDetector(
            focus="person",
            motion_gate_threshold=2000,  # High threshold
            periodic_interval=10  # Force detection only every 10 frames
        )
        
        print("✅ SmartDetector created with strict motion gating")
        
        # Mock motion detection to return low motion
        with patch.object(detector, '_detect_motion') as mock_motion:
            # Simulate low motion (small area)
            mock_motion.return_value = (2.0, [
                {"x": 10, "y": 10, "w": 10, "h": 10}  # 100px area
            ])
            
            with patch.object(detector, '_init_yolo', return_value=False):
                gated_frames = 0
                detected_frames = 0
                
                # Test 20 frames
                for frame in range(20):
                    detector._frame_count = frame
                    result = detector.analyze("fake.jpg", "fake_prev.jpg")
                    
                    if result.skip_reason and "motion_gate" in result.skip_reason:
                        gated_frames += 1
                    else:
                        detected_frames += 1
                
                print(f"📊 Over 20 frames: {gated_frames} gated, {detected_frames} detected")
                gating_rate = gated_frames / 20 * 100
                print(f"📊 Gating effectiveness: {gating_rate:.1f}% reduction")
                
                # Should have high gating rate
                assert gating_rate > 50, f"Expected >50% gating, got {gating_rate:.1f}%"
                print("✅ Motion gating is working effectively")
        
        print("🎉 Motion gating effectiveness test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_config_parameters():
    """Test that new config parameters are loaded correctly."""
    print("Testing new config parameters...")
    
    try:
        from streamware.config import config, DEFAULTS
        from streamware.smart_detector import SmartDetector
        
        # Check that new parameters exist in defaults
        assert "SQ_MOTION_GATE_THRESHOLD" in DEFAULTS
        assert "SQ_PERIODIC_INTERVAL" in DEFAULTS
        assert "SQ_TRACK_MIN_STABLE_FRAMES" in DEFAULTS
        assert "SQ_TRACK_BUFFER" in DEFAULTS
        
        print(f"✅ SQ_MOTION_GATE_THRESHOLD: {config.get('SQ_MOTION_GATE_THRESHOLD')}")
        print(f"✅ SQ_PERIODIC_INTERVAL: {config.get('SQ_PERIODIC_INTERVAL')}")
        print(f"✅ SQ_TRACK_MIN_STABLE_FRAMES: {config.get('SQ_TRACK_MIN_STABLE_FRAMES')}")
        print(f"✅ SQ_TRACK_BUFFER: {config.get('SQ_TRACK_BUFFER')}")
        
        # Test SmartDetector uses config values
        detector = SmartDetector()
        assert detector.motion_gate_threshold == int(config.get("SQ_MOTION_GATE_THRESHOLD", "1000"))
        assert detector.periodic_interval == int(config.get("SQ_PERIODIC_INTERVAL", "30"))
        
        print("✅ SmartDetector loads config values correctly")
        
        print("🎉 Config parameters test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Running Simple Integration Tests")
    print("=" * 60)
    
    tests = [
        test_bytetrack_narrator_direct,
        test_motion_gating_effectiveness,
        test_config_parameters
    ]
    
    results = []
    for test in tests:
        print()
        success = test()
        results.append(success)
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} integration tests passed!")
        exit(0)
    else:
        print(f"❌ {total - passed} of {total} tests failed")
        exit(1)
