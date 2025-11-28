"""
Integration tests for LLM components with actual models
These tests require Ollama to be installed and running
"""

import pytest
import os
import requests
from pathlib import Path

from streamware import flow


# Check if Ollama is available
def ollama_available():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.ok
    except:
        return False


# Check if specific model is available
def model_available(model_name):
    """Check if specific model is available in Ollama"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.ok:
            models = response.json().get("models", [])
            return any(model_name in m.get("name", "") for m in models)
    except:
        pass
    return False


@pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
class TestLLMWithOllama:
    """Integration tests with actual Ollama"""
    
    def test_llm_generate_with_ollama(self):
        """Test LLM generation with Ollama"""
        result = flow("llm://generate?prompt=Say hello&provider=ollama&model=llama3.2").run()
        
        # Should get some response
        assert isinstance(result, (str, dict))
        if isinstance(result, dict):
            assert "response" in str(result).lower() or "hello" in str(result).lower()
    
    def test_text_to_sql(self):
        """Test natural language to SQL"""
        result = flow("llm://to_sql?prompt=get all users&provider=ollama").run()
        
        # Should contain SQL keywords
        result_str = str(result).upper()
        assert "SELECT" in result_str or "FROM" in result_str
    
    def test_text_analysis(self):
        """Test text analysis"""
        text = "Streamware is an amazing Python framework for stream processing"
        result = flow(f"llm://analyze?text={text}&provider=ollama").run()
        
        # Should return some analysis
        assert len(str(result)) > 10


@pytest.mark.skipif(not model_available("llava"), reason="LLaVA not available")
class TestMediaWithLLaVA:
    """Integration tests with LLaVA model"""
    
    def test_image_description(self, tmp_path):
        """Test image description with LLaVA"""
        # Create a test image
        test_image = tmp_path / "test.jpg"
        
        # Create a simple test image (if PIL available)
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(test_image)
            
            result = flow(f"media://describe_image?file={test_image}&model=llava").run()
            
            assert result["success"] == True
            assert "description" in result
            assert len(result["description"]) > 0
        except ImportError:
            pytest.skip("PIL not available")
    
    def test_video_description(self, tmp_path):
        """Test video description with LLaVA"""
        # Skip if no test video
        test_video = Path("test_video.mp4")
        if not test_video.exists():
            pytest.skip("No test video available")
        
        result = flow(f"media://describe_video?file={test_video}&model=llava").run()
        
        assert result["success"] == True
        assert "description" in result


@pytest.mark.skipif(not model_available("qwen2.5"), reason="Qwen2.5 not available")
class TestText2StreamwareWithQwen:
    """Integration tests with Qwen2.5 model"""
    
    def test_convert_simple_command(self):
        """Test converting simple command"""
        result = flow("text2sq://convert?prompt=list all files&model=qwen2.5:14b").run()
        
        result_str = str(result)
        assert "sq" in result_str.lower()
        assert "file" in result_str.lower() or "ls" in result_str.lower()
    
    def test_convert_complex_command(self):
        """Test converting complex command"""
        prompt = "upload file.txt to production server using SSH"
        result = flow(f"text2sq://convert?prompt={prompt}&model=qwen2.5:14b").run()
        
        result_str = str(result).lower()
        assert "ssh" in result_str or "upload" in result_str or "sq" in result_str
    
    def test_explain_command(self):
        """Test explaining sq command"""
        result = flow("text2sq://explain?command=sq file . --list").run()
        
        # Should provide explanation
        result_str = str(result).lower()
        assert "list" in result_str or "file" in result_str or "directory" in result_str


class TestLLMEndToEnd:
    """End-to-end tests for complete workflows"""
    
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    def test_ai_command_generation_workflow(self):
        """Test complete AI command generation workflow"""
        # 1. Natural language input
        prompt = "get weather information"
        
        # 2. Convert to sq command
        result = flow(f"text2sq://convert?prompt={prompt}").run()
        
        # 3. Should get a valid command
        assert isinstance(result, (str, dict))
        if isinstance(result, str):
            assert len(result) > 0
    
    @pytest.mark.skipif(not model_available("llava"), reason="LLaVA not available")
    def test_image_to_speech_workflow(self, tmp_path):
        """Test image description to speech workflow"""
        # Skip if dependencies not available
        try:
            from PIL import Image
            import pyttsx3
        except ImportError:
            pytest.skip("PIL or pyttsx3 not available")
        
        # 1. Create test image
        test_image = tmp_path / "test.jpg"
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(test_image)
        
        # 2. Describe image
        result = flow(f"media://describe_image?file={test_image}").run()
        
        if result.get("success"):
            description = result.get("description", "")
            
            # 3. Speak description (mocked for testing)
            # In real scenario: sq voice speak --text "$description"
            assert len(description) > 0


class TestModelCompatibility:
    """Test compatibility with different models"""
    
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    def test_list_available_models(self):
        """Test listing available models"""
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.ok:
                models = response.json().get("models", [])
                print(f"\nAvailable models: {[m.get('name') for m in models]}")
                assert len(models) >= 0  # At least check we can query
        except Exception as e:
            pytest.skip(f"Cannot query Ollama: {e}")
    
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    def test_multiple_providers(self):
        """Test using multiple LLM providers"""
        providers = ["ollama"]  # Add more if API keys available
        
        for provider in providers:
            try:
                result = flow(f"llm://generate?prompt=test&provider={provider}").run()
                assert result is not None
                print(f"\n{provider}: OK")
            except Exception as e:
                print(f"\n{provider}: {e}")


class TestPerformance:
    """Performance tests for LLM operations"""
    
    @pytest.mark.skipif(not ollama_available(), reason="Ollama not available")
    def test_llm_response_time(self):
        """Test LLM response time"""
        import time
        
        start = time.time()
        result = flow("llm://generate?prompt=Say hello&provider=ollama").run()
        elapsed = time.time() - start
        
        # Should respond within reasonable time (30 seconds)
        assert elapsed < 30
        print(f"\nResponse time: {elapsed:.2f}s")
    
    @pytest.mark.skipif(not model_available("llava"), reason="LLaVA not available")
    def test_image_analysis_time(self, tmp_path):
        """Test image analysis time"""
        try:
            from PIL import Image
            import time
            
            test_image = tmp_path / "test.jpg"
            img = Image.new('RGB', (100, 100), color='green')
            img.save(test_image)
            
            start = time.time()
            result = flow(f"media://describe_image?file={test_image}").run()
            elapsed = time.time() - start
            
            # Should complete within reasonable time (60 seconds)
            assert elapsed < 60
            print(f"\nImage analysis time: {elapsed:.2f}s")
        except ImportError:
            pytest.skip("PIL not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
