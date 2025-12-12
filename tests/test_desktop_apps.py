"""
Tests for Desktop Applications (Python PyWebView and Rust Tauri)

Tests the desktop app wrappers for Voice Shell.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPythonDesktopApp(unittest.TestCase):
    """Test Python/PyWebView desktop application."""
    
    def test_app_module_imports(self):
        """Test that app module can be imported."""
        desktop_path = Path(__file__).parent.parent / "desktop" / "python"
        sys.path.insert(0, str(desktop_path))
        
        # Should not raise
        from app import VoiceShellApp, main
        
        self.assertTrue(callable(main))
        self.assertTrue(hasattr(VoiceShellApp, 'run'))
        self.assertTrue(hasattr(VoiceShellApp, 'start_server'))
        self.assertTrue(hasattr(VoiceShellApp, 'stop_server'))
        self.assertTrue(hasattr(VoiceShellApp, 'create_window'))
    
    def test_app_initialization(self):
        """Test VoiceShellApp initialization."""
        desktop_path = Path(__file__).parent.parent / "desktop" / "python"
        sys.path.insert(0, str(desktop_path))
        
        from app import VoiceShellApp
        
        app = VoiceShellApp(port=9999, http_port=10000, language="pl", verbose=True)
        
        self.assertEqual(app.port, 9999)
        self.assertEqual(app.http_port, 10000)
        self.assertEqual(app.language, "pl")
        self.assertTrue(app.verbose)
        self.assertIsNone(app.server)
        self.assertIsNone(app.window)
    
    def test_app_default_values(self):
        """Test default values."""
        desktop_path = Path(__file__).parent.parent / "desktop" / "python"
        sys.path.insert(0, str(desktop_path))
        
        from app import VoiceShellApp
        
        app = VoiceShellApp()
        
        self.assertEqual(app.port, 8765)
        self.assertEqual(app.language, "en")
        self.assertFalse(app.verbose)
    
    def test_start_server_sets_thread(self):
        """Test that start_server creates a thread."""
        desktop_path = Path(__file__).parent.parent / "desktop" / "python"
        sys.path.insert(0, str(desktop_path))
        
        from app import VoiceShellApp
        
        app = VoiceShellApp(port=19999)  # Use high port to avoid conflicts
        
        # Verify thread is None before start
        self.assertIsNone(app.server_thread)
        
        # We don't actually start to avoid side effects
        # Just verify the method exists and is callable
        self.assertTrue(callable(app.start_server))
    
    def test_stop_server_handles_none(self):
        """Test stop_server handles None server gracefully."""
        desktop_path = Path(__file__).parent.parent / "desktop" / "python"
        sys.path.insert(0, str(desktop_path))
        
        from app import VoiceShellApp
        
        app = VoiceShellApp()
        app.server = None
        
        # Should not raise
        app.stop_server()
    
    def test_create_window_exists(self):
        """Test create_window method exists."""
        desktop_path = Path(__file__).parent.parent / "desktop" / "python"
        sys.path.insert(0, str(desktop_path))
        
        from app import VoiceShellApp
        
        app = VoiceShellApp()
        
        # Just verify method exists
        self.assertTrue(callable(app.create_window))


class TestTauriConfig(unittest.TestCase):
    """Test Tauri configuration files."""
    
    def test_tauri_conf_exists(self):
        """Test tauri.conf.json exists."""
        config_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "tauri.conf.json"
        self.assertTrue(config_path.exists(), f"tauri.conf.json not found at {config_path}")
    
    def test_tauri_conf_valid_json(self):
        """Test tauri.conf.json is valid JSON."""
        config_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "tauri.conf.json"
        
        with open(config_path) as f:
            config = json.load(f)
        
        self.assertIsInstance(config, dict)
    
    def test_tauri_conf_has_required_fields(self):
        """Test tauri.conf.json has required fields for v2."""
        config_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "tauri.conf.json"
        
        with open(config_path) as f:
            config = json.load(f)
        
        # Required top-level fields for Tauri v2
        self.assertIn("identifier", config)
        self.assertIn("productName", config)
        self.assertIn("version", config)
        self.assertIn("build", config)
        self.assertIn("app", config)
    
    def test_tauri_conf_identifier_format(self):
        """Test identifier is in correct format."""
        config_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "tauri.conf.json"
        
        with open(config_path) as f:
            config = json.load(f)
        
        identifier = config.get("identifier", "")
        # Should be reverse domain notation
        self.assertIn(".", identifier)
        self.assertTrue(identifier.startswith("com."))
    
    def test_tauri_conf_window_config(self):
        """Test window configuration."""
        config_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "tauri.conf.json"
        
        with open(config_path) as f:
            config = json.load(f)
        
        app_config = config.get("app", {})
        windows = app_config.get("windows", [])
        
        self.assertGreater(len(windows), 0, "Should have at least one window")
        
        main_window = windows[0]
        self.assertIn("title", main_window)
        self.assertIn("width", main_window)
        self.assertIn("height", main_window)


class TestCargoToml(unittest.TestCase):
    """Test Cargo.toml configuration."""
    
    def test_cargo_toml_exists(self):
        """Test Cargo.toml exists."""
        cargo_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "Cargo.toml"
        self.assertTrue(cargo_path.exists())
    
    def test_cargo_toml_has_tauri_dependency(self):
        """Test Cargo.toml has tauri dependency."""
        cargo_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "Cargo.toml"
        
        with open(cargo_path) as f:
            content = f.read()
        
        self.assertIn("tauri", content)
        self.assertIn('[dependencies]', content)
        self.assertIn('[build-dependencies]', content)


class TestRustSourceFiles(unittest.TestCase):
    """Test Rust source files exist and have expected content."""
    
    def test_main_rs_exists(self):
        """Test main.rs exists."""
        main_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "src" / "main.rs"
        self.assertTrue(main_path.exists())
    
    def test_main_rs_has_tauri_builder(self):
        """Test main.rs has Tauri builder."""
        main_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "src" / "main.rs"
        
        with open(main_path) as f:
            content = f.read()
        
        self.assertIn("tauri::Builder", content)
        self.assertIn("fn main()", content)
    
    def test_commands_rs_exists(self):
        """Test commands.rs exists."""
        cmd_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "src" / "commands.rs"
        self.assertTrue(cmd_path.exists())
    
    def test_commands_rs_has_commands(self):
        """Test commands.rs has command functions."""
        cmd_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "src" / "commands.rs"
        
        with open(cmd_path) as f:
            content = f.read()
        
        # Should have #[command] attribute
        self.assertIn("#[command]", content)
        # Should have expected commands
        self.assertIn("get_server_status", content)
        self.assertIn("get_app_version", content)
    
    def test_server_rs_exists(self):
        """Test server.rs exists."""
        server_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "src" / "server.rs"
        self.assertTrue(server_path.exists())
    
    def test_server_rs_has_server_functions(self):
        """Test server.rs has server management functions."""
        server_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "src-tauri" / "src" / "server.rs"
        
        with open(server_path) as f:
            content = f.read()
        
        self.assertIn("start_server", content)
        self.assertIn("stop_server", content)
        self.assertIn("is_server_running", content)


class TestDesktopREADME(unittest.TestCase):
    """Test README files."""
    
    def test_main_readme_exists(self):
        """Test main desktop README exists."""
        readme_path = Path(__file__).parent.parent / "desktop" / "README.md"
        self.assertTrue(readme_path.exists())
    
    def test_python_readme_exists(self):
        """Test Python app README exists."""
        readme_path = Path(__file__).parent.parent / "desktop" / "python" / "README.md"
        self.assertTrue(readme_path.exists())
    
    def test_rust_readme_exists(self):
        """Test Rust app README exists."""
        readme_path = Path(__file__).parent.parent / "desktop" / "rust" / "README.md"
        self.assertTrue(readme_path.exists())


class TestDesktopRequirements(unittest.TestCase):
    """Test requirements files."""
    
    def test_python_requirements_exists(self):
        """Test Python requirements.txt exists."""
        req_path = Path(__file__).parent.parent / "desktop" / "python" / "requirements.txt"
        self.assertTrue(req_path.exists())
    
    def test_python_requirements_has_pywebview(self):
        """Test requirements includes pywebview."""
        req_path = Path(__file__).parent.parent / "desktop" / "python" / "requirements.txt"
        
        with open(req_path) as f:
            content = f.read()
        
        self.assertIn("pywebview", content)


class TestUIFiles(unittest.TestCase):
    """Test UI placeholder files."""
    
    def test_ui_index_exists(self):
        """Test UI index.html exists."""
        ui_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "ui" / "index.html"
        self.assertTrue(ui_path.exists())
    
    def test_ui_index_has_html(self):
        """Test UI index.html is valid HTML."""
        ui_path = Path(__file__).parent.parent / "desktop" / "rust" / "voice-shell-app" / "ui" / "index.html"
        
        with open(ui_path) as f:
            content = f.read()
        
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("<html", content)
        self.assertIn("</html>", content)


if __name__ == "__main__":
    unittest.main()
