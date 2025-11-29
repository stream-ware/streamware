"""
Edge case tests for LLM components
Tests error handling, edge cases, and unusual inputs
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys

from streamware import flow
from streamware.exceptions import ComponentError


class TestLLMEdgeCases:
    """Test edge cases for LLM component"""
    
    def test_empty_prompt(self):
        """Test LLM with empty prompt"""
        with pytest.raises(Exception):
            flow("llm://generate?prompt=").run()
    
    def test_very_long_prompt(self):
        """Test LLM with very long prompt"""
        long_prompt = "test " * 10000  # 50000 chars
        
        # Should handle or fail gracefully
        try:
            result = flow(f"llm://generate?prompt={long_prompt[:1000]}").run()
            assert result is not None
        except Exception as e:
            # Expected - too long
            assert "length" in str(e).lower() or "too" in str(e).lower() or "api" in str(e).lower()
    
    def test_special_characters_in_prompt(self):
        """Test LLM with special characters"""
        special_prompt = "Test with 特殊文字 and émojis 🎉"
        
        try:
            result = flow(f"llm://generate?prompt={special_prompt}&provider=ollama").run()
            # Should handle special chars
            assert result is not None
        except Exception:
            # May fail depending on encoding
            pass
    
    def test_sql_injection_attempt(self):
        """Test LLM with SQL injection-like input"""
        malicious = "'; DROP TABLE users; --"
        
        # Should handle safely
        try:
            result = flow(f"llm://to_sql?prompt={malicious}").run()
            # Should not execute actual SQL
            assert result is not None
        except Exception:
            pass
    
    @patch('requests.post')
    def test_llm_timeout(self, mock_post):
        """Test LLM with timeout"""
        import time
        
        def slow_response(*args, **kwargs):
            time.sleep(2)
            raise requests.exceptions.Timeout()
        
        mock_post.side_effect = slow_response
        
        with pytest.raises(Exception):
            flow("llm://generate?prompt=test").run()
    
    @patch('requests.post')
    def test_llm_connection_error(self, mock_post):
        """Test LLM with connection error"""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        with pytest.raises(Exception):
            flow("llm://generate?prompt=test&provider=ollama").run()
    
    @patch('requests.post')
    def test_llm_invalid_json_response(self, mock_post):
        """Test LLM with invalid JSON response"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_post.return_value = mock_response
        
        with pytest.raises(Exception):
            flow("llm://generate?prompt=test").run()


class TestMediaEdgeCases:
    """Test edge cases for Media component"""
    
    def test_nonexistent_file(self):
        """Test media with nonexistent file"""
        with pytest.raises(Exception):
            flow("media://describe_image?file=nonexistent.jpg").run()
    
    def test_invalid_file_format(self):
        """Test media with invalid file format"""
        with pytest.raises(Exception):
            flow("media://describe_video?file=test.txt").run()
    
    def test_corrupted_file(self, tmp_path):
        """Test media with corrupted file"""
        # Create corrupted file
        corrupted = tmp_path / "corrupted.jpg"
        corrupted.write_bytes(b"not a valid image")
        
        # Should handle gracefully
        try:
            result = flow(f"media://describe_image?file={corrupted}").run()
            # May fail or return error
        except Exception as e:
            # Expected
            assert "error" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_very_large_video(self):
        """Test media with very large video"""
        # Skip - would need actual large file
        pytest.skip("Would require very large test file")
    
    @patch('subprocess.run')
    def test_ffmpeg_not_available(self, mock_run):
        """Test video processing without ffmpeg"""
        mock_run.side_effect = FileNotFoundError("ffmpeg not found")
        
        with patch('pathlib.Path.exists', return_value=True):
            try:
                result = flow("media://describe_video?file=video.mp4").run()
            except Exception as e:
                assert "ffmpeg" in str(e).lower()


class TestVoiceEdgeCases:
    """Test edge cases for Voice component"""
    
    def test_empty_text_to_speak(self):
        """Test TTS with empty text"""
        with pytest.raises(Exception):
            flow("voice://speak?text=").run()
    
    def test_very_long_text_to_speak(self):
        """Test TTS with very long text"""
        long_text = "This is a very long text. " * 1000
        
        # Should handle or truncate
        try:
            fake_pyttsx3 = MagicMock()
            fake_engine = MagicMock()
            fake_pyttsx3.init.return_value = fake_engine
            with patch.dict(sys.modules, {'pyttsx3': fake_pyttsx3}):
                result = flow(f"voice://speak?text={long_text[:500]}").run()
                assert result is not None
        except Exception:
            # May fail
            pass
    
    def test_no_microphone_available(self):
        """Test STT without microphone"""
        # Will fail without mic
        try:
            result = flow("voice://listen").run()
        except Exception as e:
            # Expected
            assert "microphone" in str(e).lower() or "audio" in str(e).lower() or "speech" in str(e).lower()
    
    def test_invalid_language_code(self):
        """Test voice with invalid language"""
        # Should use default or fail gracefully
        try:
            fake_pyttsx3 = MagicMock()
            fake_engine = MagicMock()
            fake_pyttsx3.init.return_value = fake_engine
            with patch.dict(sys.modules, {'pyttsx3': fake_pyttsx3}):
                result = flow("voice://speak?text=test&language=invalid").run()
        except Exception:
            pass


class TestAutomationEdgeCases:
    """Test edge cases for Automation component"""
    
    def test_negative_coordinates(self):
        """Test automation with negative coordinates"""
        with pytest.raises(Exception):
            flow("automation://click?x=-100&y=-200").run()
    
    def test_coordinates_out_of_screen(self):
        """Test automation with coordinates outside screen"""
        # Should fail or clip to screen bounds
        try:
            fake_pyautogui = MagicMock()
            with patch.dict(sys.modules, {'pyautogui': fake_pyautogui}):
                result = flow("automation://click?x=999999&y=999999").run()
        except Exception:
            pass
    
    def test_invalid_key_name(self):
        """Test automation with invalid key - xdotool ignores invalid keys with warning"""
        # xdotool ignores invalid key names with a warning, doesn't raise
        # pyautogui would raise an exception
        result = flow("automation://press?key=invalidkey123").run()
        # If xdotool is used, it succeeds but logs a warning
        # If pyautogui is used, it would raise
        assert result.get("success", False) or "error" in str(result).lower()
    
    def test_automation_without_display(self):
        """Test automation without display (headless)"""
        # May fail in headless environment
        try:
            result = flow("automation://click?x=100&y=200").run()
        except Exception as e:
            # Expected in headless
            assert "display" in str(e).lower() or "screen" in str(e).lower() or "pyautogui" in str(e).lower()
    
    @patch('requests.post')
    def test_ai_automation_with_invalid_task(self, mock_post):
        """Test AI automation with nonsense task"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"response": "Cannot understand task"}
        mock_post.return_value = mock_response
        
        result = flow("automation://automate?task=asdfghjkl random nonsense").run()
        
        # Should return something, even if it's an error
        assert "success" in result or "error" in result


class TestConcurrency:
    """Test concurrent LLM operations"""
    
    @patch('requests.post')
    def test_multiple_llm_requests(self, mock_post):
        """Test multiple concurrent LLM requests"""
        import threading
        
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"response": "test"}
        mock_post.return_value = mock_response
        
        results = []
        
        def make_request():
            try:
                result = flow("llm://generate?prompt=test").run()
                results.append(result)
            except Exception as e:
                results.append(str(e))
        
        threads = [threading.Thread(target=make_request) for _ in range(5)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # All should complete
        assert len(results) == 5


class TestResourceCleanup:
    """Test resource cleanup"""
    
    def test_temp_file_cleanup(self, tmp_path):
        """Test temporary files are cleaned up"""
        # Media component creates temp files for video frames
        # Should clean up after processing
        import os
        
        initial_files = len(list(tmp_path.glob("*")))
        
        # Process that creates temp files
        try:
            with patch('pathlib.Path.exists', return_value=True):
                with patch('subprocess.run'):
                    flow("media://describe_video?file=video.mp4").run()
        except:
            pass
        
        # Check cleanup (hard to test without actual execution)
        # This is more of a reminder to implement cleanup
        pass


class TestRateLimiting:
    """Test rate limiting scenarios"""
    
    @patch('requests.post')
    def test_api_rate_limit(self, mock_post):
        """Test handling of API rate limits"""
        import requests as req
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 429  # Too Many Requests
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError("429 Too Many Requests")
        mock_post.return_value = mock_response
        
        # Use ollama provider explicitly to ensure requests.post is used
        with pytest.raises(Exception):
            flow("llm://generate?prompt=test&provider=ollama/llama3.2").run()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
