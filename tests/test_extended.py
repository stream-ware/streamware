
import pytest
from unittest.mock import Mock, patch, MagicMock
from streamware import flow, Pipeline
from streamware.core import registry
from streamware.config import config


class TestExtendedPatterns:
    """Tests for additional patterns and components"""

    def test_branch_pattern(self):
        """Test branching logic"""
        pipeline = flow("split://") 
        assert pipeline is not None

    def test_aggregate_pattern(self):
        """Test aggregation logic"""
        pipeline = flow("aggregate://function=sum")
        assert pipeline is not None

    def test_filter_pattern(self):
        """Test filter pattern"""
        pipeline = flow("filter://predicate=x>10")
        assert pipeline is not None


class TestSetupModes:
    """Tests for setup wizard modes"""
    
    def setup_method(self):
        """Save original config before each test"""
        self.original_config = config.to_dict()
    
    def teardown_method(self):
        """Restore original config after each test"""
        for key, value in self.original_config.items():
            config.set(key, value)

    @patch("streamware.setup.verify_environment")
    def test_setup_eco_mode_whisper_tiny(self, mock_verify):
        """Test that eco mode sets whisper to tiny"""
        from streamware.setup import run_setup
        
        mock_verify.return_value = {
            "ollama": False,
            "ollama_url": "",
            "ollama_models": [],
            "api_keys": {"openai": True}
        }
        
        run_setup(interactive=False, mode="eco")
        
        assert config.get("SQ_WHISPER_MODEL") == "tiny"
        assert config.get("SQ_STT_PROVIDER") == "whisper_local"

    @patch("streamware.setup.verify_environment")
    def test_setup_balance_mode_whisper_base(self, mock_verify):
        """Test that balance mode sets whisper to base"""
        from streamware.setup import run_setup
        
        mock_verify.return_value = {
            "ollama": False,
            "ollama_url": "",
            "ollama_models": [],
            "api_keys": {"openai": True}
        }
        
        run_setup(interactive=False, mode="balance")
        
        assert config.get("SQ_WHISPER_MODEL") == "base"

    @patch("streamware.setup.verify_environment")
    def test_setup_performance_mode_whisper_large(self, mock_verify):
        """Test that performance mode sets whisper to large"""
        from streamware.setup import run_setup
        
        mock_verify.return_value = {
            "ollama": False,
            "ollama_url": "",
            "ollama_models": [],
            "api_keys": {"openai": True}
        }
        
        run_setup(interactive=False, mode="performance")
        
        assert config.get("SQ_WHISPER_MODEL") == "large"


class TestVoiceConfig:
    """Tests for voice configuration"""
    
    def test_stt_provider_in_defaults(self):
        """Test that STT provider is in config defaults"""
        from streamware.config import DEFAULTS
        assert "SQ_STT_PROVIDER" in DEFAULTS
        assert "SQ_WHISPER_MODEL" in DEFAULTS

    def test_voice_component_uses_config(self):
        """Test that VoiceComponent reads config values"""
        from streamware.uri import StreamwareURI
        from streamware.components.voice import VoiceComponent
        
        # Set config
        config.set("SQ_STT_PROVIDER", "whisper_local")
        config.set("SQ_WHISPER_MODEL", "small")
        
        uri = StreamwareURI.parse("voice://listen")
        component = VoiceComponent(uri)
        
        assert component.stt_provider == "whisper_local"
        assert component.whisper_model == "small"


class TestLiveNarratorValidation:
    """Tests for live narrator URL validation"""
    
    def test_empty_url_raises_error(self):
        """Test that empty URL raises ComponentError"""
        from streamware.uri import StreamwareURI
        from streamware.components.live_narrator import LiveNarratorComponent
        from streamware.exceptions import ComponentError
        
        uri = StreamwareURI.parse("live://narrator?source=")
        component = LiveNarratorComponent(uri)
        
        with pytest.raises(ComponentError):
            component.process(None)

    def test_valid_url_accepted(self):
        """Test that valid URL is accepted (will fail on ffmpeg but not validation)"""
        from streamware.uri import StreamwareURI
        from streamware.components.live_narrator import LiveNarratorComponent
        
        uri = StreamwareURI.parse("live://narrator?source=rtsp://test/stream&duration=1")
        component = LiveNarratorComponent(uri)
        
        # Should not raise on validation, only on actual capture
        assert component.source == "rtsp://test/stream"


class TestQuickCLILLM:
    """Tests for quick CLI LLM command configuration"""
    
    @patch("streamware.quick_cli.flow")
    def test_llm_no_provider_uses_config(self, mock_flow):
        """Test that sq llm uses config when no provider specified"""
        from streamware.quick_cli import handle_llm
        
        mock_flow.return_value.run.return_value = "Result"
        
        args = MagicMock()
        args.prompt = "test prompt"
        args.provider = None
        args.model = None
        args.to_sql = False
        args.to_sq = False
        args.to_bash = False
        args.analyze = False
        args.summarize = False
        args.input = None
        args.execute = False
        args.quiet = False
        
        handle_llm(args)
        
        # URI should NOT contain provider param
        call_args = mock_flow.call_args[0][0]
        assert "&provider=" not in call_args

    @patch("streamware.quick_cli.flow")
    def test_llm_explicit_provider_override(self, mock_flow):
        """Test that explicit --provider overrides config"""
        from streamware.quick_cli import handle_llm
        
        mock_flow.return_value.run.return_value = "Result"
        
        args = MagicMock()
        args.prompt = "test"
        args.provider = "anthropic"
        args.model = None
        args.to_sql = False
        args.to_sq = False
        args.to_bash = False
        args.analyze = False
        args.summarize = False
        args.input = None
        args.execute = False
        args.quiet = False
        
        handle_llm(args)
        
        call_args = mock_flow.call_args[0][0]
        assert "&provider=anthropic" in call_args

