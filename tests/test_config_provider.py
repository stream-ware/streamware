
import pytest
from unittest.mock import patch, MagicMock
import os
from streamware.components.llm import LLMComponent
from streamware.uri import StreamwareURI
from streamware.config import config
from streamware.setup import check_providers, run_setup

class TestConfigProviderFallback:
    
    def setup_method(self):
        # Reset config before each test
        self.original_config = config.to_dict()
        # clear specific keys
        for key in ["SQ_LLM_PROVIDER", "SQ_MODEL", "SQ_OLLAMA_URL", "OPENAI_API_KEY", "SQ_OPENAI_API_KEY"]:
            if key in os.environ:
                del os.environ[key]
            config.set(key, "")

    def teardown_method(self):
        # Restore config
        for key, value in self.original_config.items():
            config.set(key, value)

    def test_configured_openai_provider(self):
        """Test correct behavior when configured for OpenAI"""
        # Set config to OpenAI
        config.set("SQ_LLM_PROVIDER", "openai")
        config.set("SQ_MODEL", "gpt-4o-mini")
        
        # Provide dummy key to prevent fallback to Ollama
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-dummy"}):
            uri = StreamwareURI("llm://generate")
            component = LLMComponent(uri)
            
            assert component.provider == "openai"
            assert component.model == "gpt-4o-mini"

    def test_config_provider_ollama(self):
        """Test picking up Ollama from config"""
        config.set("SQ_LLM_PROVIDER", "ollama")
        config.set("SQ_MODEL", "llama3")
        
        uri = StreamwareURI("llm://generate")
        component = LLMComponent(uri)
        
        assert component.provider == "ollama"
        assert component.model == "llama3"

    def test_config_provider_anthropic(self):
        """Test picking up Anthropic from config"""
        config.set("SQ_LLM_PROVIDER", "anthropic")
        config.set("SQ_MODEL", "claude-3-opus")
        
        # Provide dummy key
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-dummy"}):
            uri = StreamwareURI("llm://generate")
            component = LLMComponent(uri)
            
            assert component.provider == "anthropic"
            assert component.model == "claude-3-opus"

    def test_uri_override_config(self):
        """Test URI parameters override config"""
        config.set("SQ_LLM_PROVIDER", "ollama")
        config.set("SQ_MODEL", "llama3")
        
        # Override in URI - provide dummy key
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-dummy"}):
            uri = StreamwareURI("llm://generate?provider=openai&model=gpt-4")
            component = LLMComponent(uri)
            
            assert component.provider == "openai"
            assert component.model == "gpt-4"

    def test_setup_provider_detection(self):
        """Test setup script provider detection logic"""
        
        # Mock environment keys
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test123"}):
            providers = check_providers()
            assert providers["groq"] is True
            assert providers["openai"] is False
            
        with patch.dict(os.environ, {"SQ_OPENAI_API_KEY": "sk-test123"}):
            providers = check_providers()
            assert providers["openai"] is True


    @patch("streamware.setup.check_ollama")
    @patch("streamware.setup.check_providers")
    @patch("streamware.config.Config.save")
    def test_run_setup_auto_selection(self, mock_save, mock_providers, mock_ollama):
        """Test run_setup automatic selection logic"""
        
        # Case 1: Ollama available with vision model
        mock_ollama.return_value = (True, ["llava:13b", "llama3"], "http://localhost:11434")
        mock_providers.return_value = {"openai": False, "anthropic": False, "groq": False, "gemini": False, "deepseek": False, "mistral": False}
        
        # Capture print output or check config changes
        # We'll check config changes via side effects or inspection if we could, 
        # but since run_setup modifies the global config object, we can check that.
        
        # Reset config
        config.set("SQ_LLM_PROVIDER", "")
        
        run_setup(interactive=False)
        
        assert config.get("SQ_LLM_PROVIDER") == "ollama"
        assert config.get("SQ_MODEL") == "llava:13b"
        assert config.get("SQ_OLLAMA_URL") == "http://localhost:11434"

    @patch("streamware.setup.check_ollama")
    @patch("streamware.setup.check_providers")
    @patch("streamware.config.Config.save")
    def test_run_setup_cloud_fallback(self, mock_save, mock_providers, mock_ollama):
        """Test run_setup fallback to cloud provider if Ollama missing"""
        
        # Case 2: No Ollama, but OpenAI key present
        mock_ollama.return_value = (False, [], "")
        mock_providers.return_value = {
            "openai": True, 
            "anthropic": False, 
            "groq": False, 
            "gemini": False, 
            "deepseek": False, 
            "mistral": False
        }
        
        config.set("SQ_LLM_PROVIDER", "")
        
        run_setup(interactive=False)
        
        assert config.get("SQ_LLM_PROVIDER") == "openai"
        assert config.get("SQ_MODEL") == "gpt-4o"

