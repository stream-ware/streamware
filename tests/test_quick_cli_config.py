
import pytest
from unittest.mock import patch, MagicMock
import argparse
from streamware.quick_cli import handle_llm, main
from streamware.config import config

class TestQuickCLIConfig:
    
    def setup_method(self):
        self.original_config = config.to_dict()
        config.set("SQ_LLM_PROVIDER", "ollama")
        config.set("SQ_MODEL", "llama3")

    def teardown_method(self):
        for key, value in self.original_config.items():
            config.set(key, value)

    @patch("streamware.quick_cli.flow")
    def test_llm_command_uses_config(self, mock_flow):
        """Test that 'sq llm' uses configured provider when not specified"""
        mock_flow.return_value.run.return_value = "Result"
        
        # Simulate args
        args = MagicMock()
        args.prompt = "test"
        args.provider = None  # Not specified
        args.model = None
        args.to_sql = False
        args.to_sq = False
        args.to_bash = False
        args.analyze = False
        args.summarize = False
        args.input = None
        args.execute = False
        
        handle_llm(args)
        
        # Verify flow was called with correct URI (NO provider param)
        # It should rely on LLMComponent default logic which I verified in previous tests
        expected_uri = "llm://generate?prompt=test" 
        mock_flow.assert_called_with(expected_uri)

    @patch("streamware.quick_cli.flow")
    def test_llm_command_overrides_config(self, mock_flow):
        """Test that 'sq llm --provider' overrides config"""
        mock_flow.return_value.run.return_value = "Result"
        
        args = MagicMock()
        args.prompt = "test"
        args.provider = "openai"  # Explicitly specified
        args.model = None
        args.to_sql = False
        args.to_sq = False
        args.to_bash = False
        args.analyze = False
        args.summarize = False
        args.input = None
        args.execute = False
        
        handle_llm(args)
        
        expected_uri = "llm://generate?prompt=test&provider=openai"
        mock_flow.assert_called_with(expected_uri)

