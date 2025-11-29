"""
Tests for LLM-based components
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import json

from streamware import flow
from streamware.components.llm import LLMComponent
from streamware.components.text2streamware import Text2StreamwareComponent
from streamware.components.media import MediaComponent
from streamware.components.voice import VoiceComponent
from streamware.components.automation import AutomationComponent


class TestLLMComponent:
    """Test LLM component"""
    
    @patch('subprocess.run')
    def test_llm_component_creation(self, mock_run):
        """Test LLM component can be created"""
        # Mock pip install
        mock_run.return_value = Mock(returncode=0)
        
        f = flow("llm://generate?prompt=test")
        # Check that flow was created
        assert f is not None
        # Flow object exists
        assert hasattr(f, 'run')
    
    @patch('requests.post')
    def test_llm_generate_ollama(self, mock_post):
        """Test LLM generation with Ollama"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"response": "Generated text"}
        mock_post.return_value = mock_response
        
        result = flow("llm://generate?prompt=test&provider=ollama&model=llama3.2").run()
        
        assert "Generated text" in str(result)
    
    @patch('requests.post')
    def test_llm_to_sql(self, mock_post):
        """Test natural language to SQL conversion"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "response": "SELECT * FROM users WHERE age > 18"
        }
        mock_post.return_value = mock_response
        
        # Use generate with SQL-specific prompt
        result = flow("llm://generate?prompt=Convert to SQL: get all users older than 18&provider=ollama").run()
        
        assert "SELECT" in str(result) or "sql" in str(result).lower()
    
    def test_llm_invalid_provider(self):
        """Test LLM with invalid provider"""
        with pytest.raises(Exception):
            flow("llm://generate?prompt=test&provider=invalid").run()


class TestText2StreamwareComponent:
    """Test Text2Streamware component"""
    
    @patch('subprocess.run')
    def test_text2streamware_component_creation(self, mock_run):
        """Test Text2Streamware component can be created"""
        mock_run.return_value = Mock(returncode=0)
        
        f = flow("text2sq://convert?prompt=list files")
        assert f is not None
        assert hasattr(f, 'run')
    
    @patch('requests.post')
    def test_convert_to_sq(self, mock_post):
        """Test converting text to sq command"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "response": "sq file . --list"
        }
        mock_post.return_value = mock_response
        
        result = flow("text2sq://convert?prompt=list files in current directory").run()
        
        assert "sq file" in str(result) or "list" in str(result).lower()
    
    @patch('requests.post')
    def test_explain_command(self, mock_post):
        """Test explaining sq command"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "response": "This command lists all files in the current directory"
        }
        mock_post.return_value = mock_response
        
        result = flow("text2sq://explain?command=sq file . --list").run()
        
        assert "list" in str(result).lower() or "files" in str(result).lower()


class TestMediaComponent:
    """Test Media component"""
    
    @patch('subprocess.run')
    def test_media_component_creation(self, mock_run):
        """Test Media component can be created"""
        mock_run.return_value = Mock(returncode=0)
        
        f = flow("media://describe_image?file=test.jpg")
        assert f is not None
        assert hasattr(f, 'run')
    
    @patch('requests.post')
    def test_describe_image_mock(self, mock_post):
        """Test image description with mocked Ollama"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "response": "A beautiful sunset over the ocean"
        }
        mock_post.return_value = mock_response
        
        # Mock file existence
        with patch('pathlib.Path.exists', return_value=True):
            with patch('builtins.open', create=True):
                result = flow("media://describe_image?file=test.jpg&model=llava").run()
                
                assert result["success"] == True
                assert "file" in result
    
    @patch('subprocess.run')
    def test_transcribe_audio_mock(self, mock_run):
        """Test audio transcription"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Transcribed text"
        mock_run.return_value = mock_result
        
        with patch('pathlib.Path.exists', return_value=True):
            result = flow("media://transcribe?file=audio.mp3").run()
            
            # Should attempt transcription
            assert "success" in result


class TestVoiceComponent:
    """Test Voice component"""
    
    @patch('subprocess.run')
    def test_voice_component_creation(self, mock_run):
        """Test Voice component can be created"""
        mock_run.return_value = Mock(returncode=0)
        
        f = flow("voice://speak?text=hello")
        assert f is not None
        assert hasattr(f, 'run')
    
    @patch('subprocess.run')
    def test_speak_text_mock(self, mock_run):
        """Test text-to-speech without real pyttsx3 dependency"""
        mock_run.return_value = Mock(returncode=0)
        fake_pyttsx3 = MagicMock()
        fake_engine = MagicMock()
        fake_pyttsx3.init.return_value = fake_engine
        
        with patch.dict(sys.modules, {'pyttsx3': fake_pyttsx3}):
            result = flow("voice://speak?text=Hello World").run()
        
        assert result["success"] is True
        assert result["text"] == "Hello World"
        fake_pyttsx3.init.assert_called_once()
    
    @patch('subprocess.run')
    def test_voice_listen_no_mic(self, mock_run):
        """Test voice listen without microphone (should handle gracefully)"""
        mock_run.return_value = Mock(returncode=0)
        
        # This will fail without microphone, but shouldn't crash
        try:
            result = flow("voice://listen").run()
            # If it succeeds (has mic), check result
            assert "success" in result
        except Exception as e:
            # Expected if no microphone
            assert "speech_recognition" in str(e).lower() or "microphone" in str(e).lower()


class TestAutomationComponent:
    """Test Automation component"""
    
    @patch('subprocess.run')
    def test_automation_component_creation(self, mock_run):
        """Test Automation component can be created"""
        mock_run.return_value = Mock(returncode=0)
        
        f = flow("automation://click?x=100&y=200")
        assert f is not None
        assert hasattr(f, 'run')
    
    @patch('subprocess.run')
    def test_click_mock(self, mock_run):
        """Test mouse click using xdotool (primary) or pyautogui fallback"""
        mock_run.return_value = Mock(returncode=0)
        
        result = flow("automation://click?x=100&y=200").run()
        
        assert result["success"] is True
        assert result["x"] == 100
        assert result["y"] == 200
        assert result.get("method") == "xdotool"
    
    @patch('subprocess.run')
    def test_type_text_mock(self, mock_run):
        """Test typing text using xdotool (primary) or pyautogui fallback"""
        mock_run.return_value = Mock(returncode=0)
        
        result = flow("automation://type?text=Hello").run()
        
        assert result["success"] is True
        assert result["text"] == "Hello"
        assert result.get("method") == "xdotool"
    
    @patch('subprocess.run')
    def test_hotkey_mock(self, mock_run):
        """Test hotkey press using xdotool (primary) or pyautogui fallback"""
        mock_run.return_value = Mock(returncode=0)
        
        result = flow("automation://hotkey?keys=ctrl+c").run()
        
        assert result["success"] is True
        assert result["keys"] == ['ctrl', 'c']
        assert result.get("method") == "xdotool"


class TestLLMIntegration:
    """Integration tests for LLM components"""
    
    @patch('requests.post')
    def test_llm_to_automation_pipeline(self, mock_post):
        """Test LLM generating automation commands"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "response": "click(100, 200); type('hello'); press('enter')"
        }
        mock_post.return_value = mock_response
        
        # This would generate automation actions from natural language
        result = flow("automation://automate?task=click button and type hello").run()
        
        assert "success" in result
    
    @patch('requests.post')
    def test_voice_to_command_pipeline(self, mock_post):
        """Test voice command to sq execution"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {
            "response": "sq file . --list"
        }
        mock_post.return_value = mock_response
        
        # Voice command would convert to sq command
        # This tests the integration flow
        result = flow("text2sq://convert?prompt=list files").run()
        
        assert "sq" in str(result).lower() or "file" in str(result).lower()


class TestLLMProviders:
    """Test different LLM providers"""
    
    @patch('requests.post')
    def test_ollama_provider(self, mock_post):
        """Test Ollama provider"""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.json.return_value = {"response": "Ollama response"}
        mock_post.return_value = mock_response
        
        result = flow("llm://generate?prompt=test&provider=ollama").run()
        assert "response" in str(result).lower() or "ollama" in str(result).lower()
    
    @patch('subprocess.run')
    def test_openai_provider_no_key(self, mock_run):
        """Test OpenAI provider without API key"""
        mock_run.return_value = Mock(returncode=0)
        
        # Should handle missing API key gracefully
        try:
            result = flow("llm://generate?prompt=test&provider=openai").run()
            # May fail without API key
        except Exception as e:
            # Expected error
            assert "api" in str(e).lower() or "key" in str(e).lower()


class TestMediaAnalysis:
    """Test media analysis features"""
    
    @patch('subprocess.run')
    @patch('pathlib.Path.exists', return_value=True)
    def test_video_frame_extraction(self, mock_exists, mock_run):
        """Test video frame extraction"""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        # Test frame extraction process
        with patch('pathlib.Path.glob', return_value=[]):
            result = flow("media://describe_video?file=video.mp4").run()
            
            # Should attempt to process video
            assert "success" in result or "error" in result


class TestErrorHandling:
    """Test error handling in LLM components"""
    
    def test_llm_no_prompt(self):
        """Test LLM without prompt"""
        with pytest.raises(Exception):
            flow("llm://generate").run()
    
    def test_media_no_file(self):
        """Test media without file"""
        with pytest.raises(Exception):
            flow("media://describe_image").run()
    
    @patch('subprocess.run')
    def test_automation_invalid_coordinates(self, mock_run):
        """Test automation with invalid coordinates"""
        mock_run.return_value = Mock(returncode=0)
        
        # Should handle gracefully
        try:
            result = flow("automation://click").run()
            assert "success" in result or "error" in result
        except Exception:
            # Expected - missing coordinates
            pass


class TestQuickHelpers:
    """Test quick helper functions"""
    
    def test_llm_imports(self):
        """Test LLM helper imports"""
        from streamware.components.llm import generate_text
        assert callable(generate_text)
    
    def test_voice_imports(self):
        """Test voice helper imports"""
        from streamware.components.voice import listen, speak
        assert callable(listen)
        assert callable(speak)
    
    def test_automation_imports(self):
        """Test automation helper imports"""
        from streamware.components.automation import click, type_text, automate
        assert callable(click)
        assert callable(type_text)
        assert callable(automate)


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""
    
    @patch('requests.post')
    @patch('subprocess.run')
    def test_voice_controlled_automation(self, mock_run, mock_post):
        """Test voice-controlled desktop automation"""
        mock_run.return_value = Mock(returncode=0)
        
        # Mock voice recognition
        mock_post.return_value = Mock(
            ok=True,
            json=lambda: {"response": "click(100, 200)"}
        )
        
        # This simulates: voice -> LLM -> automation
        # 1. Voice listens (mocked)
        # 2. LLM converts to action
        # 3. Automation executes
        
        llm_result = flow("llm://generate?prompt=click the button&provider=ollama").run()
        assert llm_result is not None
    
    @patch('requests.post')
    def test_ai_video_description_workflow(self, mock_post):
        """Test AI video description workflow"""
        # Mock LLaVA response
        mock_post.return_value = Mock(
            ok=True,
            json=lambda: {"response": "A person walking in a park"}
        )
        
        # This would: extract frames -> analyze with LLaVA -> combine descriptions
        with patch('pathlib.Path.exists', return_value=True):
            with patch('subprocess.run'):
                with patch('pathlib.Path.glob', return_value=[]):
                    result = flow("media://describe_video?file=video.mp4").run()
                    
                    assert "success" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
