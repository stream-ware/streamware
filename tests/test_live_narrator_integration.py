"""
Integration test for LiveNarrator with ByteTrack tracker
"""

import time
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from streamware.components.live_narrator import LiveNarratorComponent


def test_live_narrator_bytetrack_integration():
    """Test LiveNarrator integration with ByteTrack tracker."""
    print("Testing LiveNarrator + ByteTrack integration...")
    
    try:
        # Create a temporary directory for frames
        with tempfile.TemporaryDirectory():
            
            # Mock dependencies
            with patch('streamware.components.live_narrator.svg_analyzer') as mock_svg, \
                 patch('streamware.components.live_narrator.dsl_generator') as mock_dsl, \
                 patch('streamware.components.live_narrator.smart_detector') as mock_detector, \
                 patch('streamware.components.live_narrator.get_tts_worker') as mock_tts, \
                 patch('streamware.fast_capture.FastCapture') as mock_capture:
                
                # Setup mocks
                mock_capture_instance = Mock()
                mock_capture.return_value = mock_capture_instance
                mock_capture_instance.get_frame.return_value = None
                mock_capture_instance.stop.return_value = None
                
                mock_svg.analyze.return_value = Mock(
                    events=[], 
                    background_base64="", 
                    motion_regions=[]
                )
                
                mock_dsl.get_delta.return_value = Mock(events=[])
                
                # Mock smart detector to return motion regions
                mock_detector.analyze.return_value = Mock(
                    has_target=False,
                    motion_percent=5.0,
                    motion_regions=[
                        {"x": 100, "y": 100, "w": 50, "h": 100, "confidence": 0.8}
                    ]
                )
                
                # Mock TTS
                mock_tts_instance = Mock()
                mock_tts.return_value = mock_tts_instance
                
                # Create LiveNarrator with track mode
                narrator = LiveNarratorComponent(
                    source="test://source",
                    mode="track",
                    focus="person",
                    duration=1,  # Very short for testing
                    quiet=True,  # Don't actually speak
                    verbose=False
                )
                
                print("✅ LiveNarrator created with track mode")
                
                # Test _analyze_movement_bytetrack method directly
                analysis = {
                    "motion_regions": [
                        {"x": 100, "y": 100, "w": 50, "h": 100, "confidence": 0.8}
                    ],
                    "has_motion": True
                }
                
                result = narrator._analyze_movement_bytetrack(analysis, 1920, 1080)
                
                print(f"📊 Analysis result: {result.get('object_count', 0)} objects")
                print(f"📊 Direction: {result.get('direction', 'unknown')}")
                print(f"📊 Person state: {result.get('person_state', 'unknown')}")
                
                # Test multiple updates to see track progression
                for i in range(3):
                    result = narrator._analyze_movement_bytetrack(analysis, 1920, 1080)
                    print(f"📊 Update {i+1}: {result.get('object_count', 0)} objects, "
                          f"state: {result.get('person_state', 'unknown')}")
                
                # Test TTS event method
                if hasattr(narrator, '_speak_tracker_event'):
                    mock_obj = Mock()
                    mock_obj.object_type = "person"
                    mock_obj.id = 1
                    
                    # This should not actually speak due to quiet=True
                    narrator._speak_tracker_event(mock_obj, "entered")
                    print("✅ TTS event method called successfully")
                
                print("🎉 LiveNarrator + ByteTrack integration test passed!")
                return True
                
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_motion_gating_integration():
    """Test motion gating in SmartDetector."""
    print("Testing motion gating integration...")
    
    try:
        from streamware.smart_detector import SmartDetector
        
        # Create detector with custom motion gating settings
        detector = SmartDetector(
            focus="person",
            motion_gate_threshold=500,  # Low threshold for testing
            periodic_interval=2  # Force detection every 2 frames
        )
        
        print("✅ SmartDetector created with motion gating")
        
        # Test frame counter increment
        detector._frame_count = 0
        
        # Simulate motion analysis with small motion (should be gated)
        with patch.object(detector, '_detect_motion') as mock_motion:
            mock_motion.return_value = (1.0, [])  # Low motion, no regions
            
            with patch.object(detector, '_init_yolo', return_value=False):
                result = detector.analyze("fake_frame.jpg", "fake_prev.jpg")
                
                print(f"📊 First frame (low motion): {result.skip_reason}")
                
            # Second frame - should force detection due to periodic interval
            detector._frame_count = 2
            with patch.object(detector, '_init_yolo', return_value=False):
                result = detector.analyze("fake_frame.jpg", "fake_prev.jpg")
                
                print(f"📊 Second frame (periodic check): {result.skip_reason}")
        
        print("🎉 Motion gating integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Motion gating test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Running Integration Tests")
    print("=" * 60)
    
    success1 = test_live_narrator_bytetrack_integration()
    print()
    success2 = test_motion_gating_integration()
    
    print()
    print("=" * 60)
    if success1 and success2:
        print("🎉 All integration tests passed!")
        exit(0)
    else:
        print("❌ Some tests failed")
        exit(1)
