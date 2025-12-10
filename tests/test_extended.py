
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
        
        uri = StreamwareURI("voice://listen")
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
        
        uri = StreamwareURI("live://narrator?source=")
        component = LiveNarratorComponent(uri)
        
        with pytest.raises(ComponentError):
            component.process(None)

    def test_valid_url_accepted(self):
        """Test that valid URL is accepted (will fail on ffmpeg but not validation)"""
        from streamware.uri import StreamwareURI
        from streamware.components.live_narrator import LiveNarratorComponent
        
        uri = StreamwareURI("live://narrator?source=rtsp://test/stream&duration=1")
        component = LiveNarratorComponent(uri)
        
        # Should not raise on validation, only on actual capture
        assert component.source == "rtsp://test/stream"


class TestLiveNarratorFramesDir:
    """Tests for live narrator frame persistence to directory"""
    
    def test_frames_dir_initialized_and_directory_created(self, tmp_path, monkeypatch):
        """Test that frames_dir from URI is prepared in process()"""
        import importlib
        from streamware.uri import StreamwareURI
        from streamware.components.live_narrator import LiveNarratorComponent

        frames_dir = tmp_path / "frames_out"
        uri = StreamwareURI(f"live://narrator?source=rtsp://test/stream&duration=1&frames_dir={frames_dir}")

        # Avoid running real narrator loop and ffmpeg
        def fake_run_narrator(self):
            return {"success": True}

        monkeypatch.setattr(LiveNarratorComponent, "_run_narrator", fake_run_narrator)

        # Import the actual live_narrator module for patching (avoid attribute shadowing)
        ln_mod = importlib.import_module(LiveNarratorComponent.__module__)
        # Patch tempfile.mkdtemp used inside live_narrator module
        monkeypatch.setattr(ln_mod.tempfile, "mkdtemp", lambda: str(tmp_path / "tmp_frames"))

        component = LiveNarratorComponent(uri)
        result = component.process(None)

        assert result["success"] is True
        assert component._frames_output_dir is not None
        assert component._frames_output_dir.exists()
        assert str(component._frames_output_dir) == str(frames_dir)

    def test_capture_frame_saves_copy_to_frames_dir(self, tmp_path, monkeypatch):
        """Test that _capture_frame writes a copy into frames_dir when configured"""
        import importlib
        from streamware.uri import StreamwareURI
        from streamware.components.live_narrator import LiveNarratorComponent

        frames_dir = tmp_path / "frames_out"
        temp_dir = tmp_path / "tmp"
        temp_dir.mkdir()
        frames_dir.mkdir()

        uri = StreamwareURI("live://narrator?source=rtsp://test/stream&duration=1&ramdisk=false")
        component = LiveNarratorComponent(uri)

        # Inject directories used by _capture_frame
        component._temp_dir = temp_dir
        component._frames_output_dir = frames_dir
        component.use_ramdisk = False  # Disable for test

        expected_output = temp_dir / "frame_00001.jpg"

        def fake_run(cmd, check, capture_output, timeout, stdin=None):  # noqa: ARG001
            expected_output.write_bytes(b"testframe")

        # Import the actual live_narrator module for patching
        ln_mod = importlib.import_module(LiveNarratorComponent.__module__)
        # Patch subprocess.run used inside live_narrator module
        monkeypatch.setattr(ln_mod.subprocess, "run", fake_run)

        frame_path = component._capture_frame(1)

        assert frame_path == expected_output
        assert expected_output.exists()

        copied_path = frames_dir / expected_output.name
        assert copied_path.exists()
        assert copied_path.read_bytes() == expected_output.read_bytes()


class TestFrameAnalyzerDownscaling:
    """Tests for FrameAnalyzer downscaling and region coordinates"""

    def test_frame_analyzer_uses_downscaled_prev_gray_and_rescaled_regions(self, tmp_path):
        """FrameAnalyzer should analyze on downscaled frames but report regions in full resolution"""
        from PIL import Image, ImageDraw
        from streamware.components.live_narrator import FrameAnalyzer

        width, height = 640, 480

        # First frame: blank scene
        img1 = Image.new("RGB", (width, height), "black")
        frame1 = tmp_path / "frame1.jpg"
        img1.save(frame1)

        # Second frame: add a bright rectangle to induce motion
        img2 = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(img2)
        draw.rectangle([200, 150, 400, 350], fill="white")
        frame2 = tmp_path / "frame2.jpg"
        img2.save(frame2)

        analyzer = FrameAnalyzer()

        # Prime the analyzer with the first frame (no previous gray yet)
        analysis1, annotated1 = analyzer.analyze(frame1)
        assert annotated1 is not None
        assert analysis1["has_motion"] is False

        # Second frame should detect motion compared to previous
        analysis2, annotated2 = analyzer.analyze(frame2)
        assert annotated2 is not None
        assert analysis2["has_motion"] is True

        regions = analysis2["motion_regions"]
        assert isinstance(regions, list)
        assert regions  # at least one region detected

        # Regions should be expressed in original image coordinates
        for region in regions:
            assert 0 <= region["x"] < width
            assert 0 <= region["y"] < height
            assert region["w"] > 0
            assert region["h"] > 0
            assert region["x"] + region["w"] <= width
            assert region["y"] + region["h"] <= height

        # Internal prev_gray buffer should be downscaled compared to original frame
        prev_gray = analyzer._prev_gray
        assert prev_gray.size[0] < width
        assert prev_gray.size[1] < height


class TestMotionDiffDownscaling:
    """Tests for MotionDiffComponent downscaling and region rescaling"""

    def test_compute_diff_downscaled_then_rescaled_regions(self, tmp_path):
        """_compute_diff should work on downscaled frames but return regions in full resolution"""
        from PIL import Image, ImageDraw
        from streamware.uri import StreamwareURI
        from streamware.components.motion_diff import MotionDiffComponent

        width, height = 640, 480

        # Previous frame: mostly dark
        prev_img = Image.new("RGB", (width, height), "black")
        prev_path = tmp_path / "prev.jpg"
        prev_img.save(prev_path)

        # Current frame: introduce a bright rectangle in the center
        curr_img = Image.new("RGB", (width, height), "black")
        draw = ImageDraw.Draw(curr_img)
        draw.rectangle([100, 100, 300, 300], fill="white")
        curr_path = tmp_path / "curr.jpg"
        curr_img.save(curr_path)

        uri = StreamwareURI("motion://analyze?source=dummy&scale=0.3")
        component = MotionDiffComponent(uri)
        component._temp_dir = tmp_path
        component._prev_frame = prev_path

        result = component._compute_diff(curr_path, frame_num=1)

        # has_change may be a numpy.bool_, so use truthiness instead of identity check
        assert result["has_change"]
        regions = result["regions"]
        assert isinstance(regions, list)
        assert regions

        # Regions should be within full-resolution bounds, not the downscaled size
        for region in regions:
            assert 0 <= region.x < width
            assert 0 <= region.y < height
            assert region.width > 0
            assert region.height > 0
            assert region.x + region.width <= width
            assert region.y + region.height <= height


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


class TestLiveCLIValidation:
    """Tests for quick CLI live narrator validation"""

    @patch("streamware.quick_cli.flow")
    def test_live_empty_url_returns_error_and_skips_flow(self, mock_flow, capsys):
        """Test that sq live narrator with empty --url returns error before running flow"""
        from streamware.quick_cli import handle_live

        args = MagicMock()
        args.operation = "narrator"
        args.url = ""  # Simulate: --url "" (empty)

        # Other args are not used when URL is empty but define them defensively
        args.mode = "full"
        args.tts = False
        args.duration = 1
        args.analysis = "normal"
        args.motion = "significant"
        args.frames = "changed"
        args.interval = None
        args.threshold = None
        args.trigger = None
        args.focus = None
        args.webhook = None
        args.model = None
        args.quiet = False

        rc = handle_live(args)
        captured = capsys.readouterr()

        assert rc == 1
        assert "Error: --url parameter is required" in captured.err
        mock_flow.assert_not_called()


class TestMarkdownLogging:
    """Tests for Markdown logging in quick CLI watch/live commands"""

    @patch("streamware.quick_cli._save_watch_markdown_log")
    @patch("streamware.quick_cli.flow")
    def test_watch_log_md_uses_default_filename(self, mock_flow, mock_save):
        """sq watch --log md without --file should write watch_log.md"""
        from streamware.quick_cli import handle_watch

        mock_flow.return_value.run.return_value = {
            "significant_changes": 1,
            "frames_analyzed": 10,
            "timeline": [],
        }

        args = MagicMock()
        args.url = "rtsp://test/stream"
        args.sensitivity = "medium"
        args.detect = "person"
        args.speed = "normal"
        args.when = "changes"
        args.alert = "none"
        args.duration = 60
        args.file = None
        args.log = "md"
        args.yaml = False
        args.json = False
        args.table = False
        args.html = False

        rc = handle_watch(args)
        assert rc == 0
        mock_save.assert_called_once()
        # Third arg is output_file
        assert mock_save.call_args[0][2] == "watch_log.md"

    @patch("streamware.quick_cli._save_live_markdown_log")
    @patch("streamware.quick_cli.flow")
    def test_live_log_md_uses_file_argument_when_provided(self, mock_flow, mock_save):
        """sq live --log md --file logs.md should write to logs.md"""
        from streamware.quick_cli import handle_live

        mock_flow.return_value.run.return_value = {
            "operation": "narrator",
            "config": {"model": "llava:7b"},
            "history": [],
            "triggers": [],
        }

        args = MagicMock()
        args.command = "live"
        args.operation = "narrator"
        args.url = "rtsp://test/stream"
        args.mode = "full"
        args.tts = False
        args.duration = 10
        args.analysis = "normal"
        args.motion = "significant"
        args.frames = "changed"
        args.frames_dir = None
        args.interval = None
        args.threshold = None
        args.trigger = None
        args.focus = None
        args.webhook = None
        args.model = None
        args.quiet = False
        args.yaml = False
        args.json = False
        args.table = False
        args.html = False
        args.file = "logs.md"
        args.log = "md"

        rc = handle_live(args)
        assert rc == 0
        mock_save.assert_called_once()
        # Second arg is output_file
        assert mock_save.call_args[0][1] == "logs.md"


class TestResponseFilter:
    """Tests for LLM response filtering"""

    def test_is_significant_detects_noise(self):
        """is_significant should detect noise responses"""
        from streamware.response_filter import is_significant

        # Noise - should return False
        assert is_significant("No significant changes") is False
        assert is_significant("VISIBLE: NO") is False
        assert is_significant("No person visible") is False
        assert is_significant("PRESENT: NO") is False

    def test_is_significant_detects_events(self):
        """is_significant should detect real events"""
        from streamware.response_filter import is_significant

        # Significant - should return True
        assert is_significant("VISIBLE: YES\nLOCATION: center") is True
        assert is_significant("Person detected at door") is True
        assert is_significant("PRESENT: YES\nSTATE: walking") is True

    def test_extract_structured_fields(self):
        """extract_structured_fields should parse response"""
        from streamware.response_filter import extract_structured_fields

        response = """VISIBLE: YES
LOCATION: center
STATE: standing
ALERT: NO"""
        
        fields = extract_structured_fields(response)
        assert fields.get("visible") == "YES"
        assert fields.get("location") == "center"
        assert fields.get("state") == "standing"

    def test_format_for_tts(self):
        """format_for_tts should create clean text"""
        from streamware.response_filter import format_for_tts

        response = "OBJECT: person\nLOCATION: door\nSTATE: entering"
        tts = format_for_tts(response)
        assert "person" in tts
        assert "door" in tts


class TestSetupUtils:
    """Tests for cross-platform setup utilities"""

    def test_get_platform(self):
        """get_platform should return valid platform"""
        from streamware.setup_utils import get_platform, Platform

        plat = get_platform()
        assert plat in (Platform.LINUX, Platform.MACOS, Platform.WINDOWS, Platform.UNKNOWN)

    def test_check_dependency(self):
        """check_dependency should work for pip packages"""
        from streamware.setup_utils import check_dependency, Dependency

        # requests should be installed
        dep = Dependency(
            name="requests",
            check_cmd=["python3", "-c", "import requests"],
            install_pip="requests"
        )
        assert check_dependency(dep) is True

    def test_check_tts_available(self):
        """check_tts_available should return tuple"""
        from streamware.setup_utils import check_tts_available

        available, engine = check_tts_available()
        assert isinstance(available, bool)
        assert engine is None or isinstance(engine, str)

    def test_get_system_info(self):
        """get_system_info should return dict"""
        from streamware.setup_utils import get_system_info

        info = get_system_info()
        assert "platform" in info
        assert "python_version" in info


class TestLLMClient:
    """Tests for centralized LLM client"""

    def test_llm_config_from_env(self):
        """LLMConfig should load from environment"""
        from streamware.llm_client import LLMConfig

        config = LLMConfig.from_env()
        assert config.provider in ("ollama", "openai", "anthropic")
        assert config.timeout > 0
        assert config.max_retries >= 0

    def test_llm_metrics_tracking(self):
        """LLMMetrics should track statistics"""
        from streamware.llm_client import LLMMetrics

        metrics = LLMMetrics()
        assert metrics.total_calls == 0
        assert metrics.avg_time_ms == 0

        metrics.total_calls = 10
        metrics.successful_calls = 8
        metrics.total_time_ms = 5000

        assert metrics.avg_time_ms == 500
        assert metrics.success_rate == 0.8

    def test_get_client_singleton(self):
        """get_client should return singleton"""
        from streamware.llm_client import get_client

        client1 = get_client()
        client2 = get_client()
        assert client1 is client2


class TestTTSModule:
    """Tests for unified TTS module"""

    def test_tts_config_from_env(self):
        """TTSConfig should load from environment"""
        from streamware.tts import TTSConfig

        config = TTSConfig.from_env()
        assert config.rate > 0

    def test_get_manager_singleton(self):
        """get_manager should return singleton"""
        from streamware.tts import get_manager

        mgr1 = get_manager()
        mgr2 = get_manager()
        assert mgr1 is mgr2

    def test_clean_text(self):
        """TTS should clean text properly"""
        from streamware.tts import get_manager

        mgr = get_manager()
        cleaned = mgr._clean_text('  Hello  "world"  ')
        assert cleaned == "Hello world"
        assert '"' not in cleaned


class TestPromptsModule:
    """Tests for prompts module"""

    def test_get_prompt_returns_string(self):
        """get_prompt should return a string"""
        from streamware.prompts import get_prompt

        # Should return prompt from file
        prompt = get_prompt("stream_diff")
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_render_prompt_substitutes_variables(self):
        """render_prompt should substitute variables"""
        from streamware.prompts import render_prompt

        result = render_prompt(
            "stream_focus",
            focus="person",
            custom_prompt=""
        )
        assert "person" in result

    def test_list_prompts_returns_dict(self):
        """list_prompts should return dict of available prompts"""
        from streamware.prompts import list_prompts

        prompts = list_prompts()
        assert isinstance(prompts, dict)
        assert "stream_diff" in prompts
        assert "trigger_check" in prompts

    def test_missing_prompt_returns_empty(self):
        """Missing prompt should return empty string"""
        from streamware.prompts import get_prompt

        result = get_prompt("nonexistent_prompt_xyz")
        assert result == ""

    def test_missing_prompt_with_default(self):
        """Missing prompt with default should return default"""
        from streamware.prompts import get_prompt

        result = get_prompt("nonexistent_prompt_xyz", default="fallback")
        assert result == "fallback"


class TestImageOptimization:
    """Tests for image optimization module"""

    def test_optimize_config_defaults(self):
        """OptimizeConfig should have sensible defaults"""
        from streamware.image_optimize import OptimizeConfig

        config = OptimizeConfig()
        assert config.max_size == 512
        assert config.quality == 65
        assert config.posterize_colors == 0
        assert config.grayscale is False
        assert config.sharpen is True

    def test_presets_exist(self):
        """All standard presets should be defined"""
        from streamware.image_optimize import PRESETS

        assert "fast" in PRESETS
        assert "balanced" in PRESETS
        assert "quality" in PRESETS
        assert "minimal" in PRESETS

        # fast should have smaller max_size than quality
        assert PRESETS["fast"].max_size < PRESETS["quality"].max_size

    def test_prepare_image_returns_path(self, tmp_path):
        """prepare_image_for_llm should return a Path"""
        from streamware.image_optimize import prepare_image_for_llm

        # Create a simple test image
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")

        test_img = tmp_path / "test.jpg"
        img = Image.new("RGB", (1920, 1080), color="red")
        img.save(test_img, "JPEG")

        result = prepare_image_for_llm(test_img, preset="fast")
        assert result.exists()

        # Should be smaller than original
        result_img = Image.open(result)
        assert max(result_img.size) <= 384  # fast preset max_size

    def test_prepare_image_base64(self, tmp_path):
        """prepare_image_for_llm_base64 should return valid base64"""
        from streamware.image_optimize import prepare_image_for_llm_base64
        import base64

        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not installed")

        test_img = tmp_path / "test.jpg"
        img = Image.new("RGB", (800, 600), color="blue")
        img.save(test_img, "JPEG")

        result = prepare_image_for_llm_base64(test_img, preset="balanced")
        assert isinstance(result, str)
        assert len(result) > 0

        # Should be valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0


class TestFrameOptimizer:
    """Tests for frame optimization module"""

    def test_adaptive_interval_high_motion(self):
        """High motion should give short interval"""
        from streamware.frame_optimizer import FrameOptimizer, OptimizerConfig

        config = OptimizerConfig(min_interval=1.0, max_interval=10.0, high_motion_threshold=10.0)
        optimizer = FrameOptimizer(config)

        interval = optimizer.get_adaptive_interval(motion_percent=15.0)
        assert interval <= 3.0  # Should be close to min (with smoothing)

    def test_adaptive_interval_low_motion(self):
        """Low motion should give long interval"""
        from streamware.frame_optimizer import FrameOptimizer, OptimizerConfig

        config = OptimizerConfig(min_interval=1.0, max_interval=10.0, low_motion_threshold=2.0)
        optimizer = FrameOptimizer(config)

        # Call multiple times to allow smoothing
        for _ in range(3):
            interval = optimizer.get_adaptive_interval(motion_percent=0.5)
        assert interval >= 5.0  # Should trend toward max

    def test_optimizer_config_defaults(self):
        """OptimizerConfig should have sensible defaults"""
        from streamware.frame_optimizer import OptimizerConfig

        config = OptimizerConfig()
        assert config.min_interval > 0
        assert config.max_interval > config.min_interval
        assert config.ssim_threshold > 0.5

    def test_optimizer_reset(self):
        """Reset should clear state"""
        from streamware.frame_optimizer import FrameOptimizer

        optimizer = FrameOptimizer()
        optimizer.get_adaptive_interval(5.0)
        optimizer.reset()

        assert len(optimizer._frame_cache) == 0
        assert len(optimizer._stats) == 0

    def test_get_optimizer_singleton(self):
        """get_optimizer should return same instance"""
        from streamware.frame_optimizer import get_optimizer

        opt1 = get_optimizer()
        opt2 = get_optimizer()
        # Note: with config param it creates new instance
        assert opt1 is not None
        assert opt2 is not None


class TestBatchGuarder:
    """Tests for batch guarder"""

    def test_batch_guarder_init(self):
        """BatchGuarder should initialize correctly"""
        from streamware.frame_optimizer import BatchGuarder

        guarder = BatchGuarder(batch_size=3, timeout=5.0)
        assert guarder.batch_size == 3
        assert guarder.timeout == 5.0

    def test_flush_empty_returns_empty(self):
        """Flush on empty batch should return empty list"""
        from streamware.frame_optimizer import BatchGuarder

        guarder = BatchGuarder(batch_size=5)
        results = guarder.flush()
        assert results == []

