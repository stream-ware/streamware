"""
Streamware Workflow DSL
Simple YAML-based configuration for video analysis pipelines.

Usage:
    from streamware.workflow import load_workflow, run_workflow
    
    # Load from file
    workflow = load_workflow("my_workflow.yaml")
    
    # Or use preset
    workflow = load_workflow(preset="track_person")
    
    # Run
    run_workflow(workflow, url="rtsp://...")
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from pathlib import Path
import yaml

# =============================================================================
# WORKFLOW PRESETS
# =============================================================================

PRESETS = {
    "track_person": {
        "fps": 1.0,
        "detect": {"classes": ["person"], "confidence": 0.3, "skip_llm_above": 0.5},
        "track": True,
        "llm": False,
        "tts": True,
        "tts_mode": "diff",
    },
    "track_animal": {
        "fps": 1.0,
        "detect": {"classes": ["cat", "dog", "bird"], "confidence": 0.3, "skip_llm_above": 0.5},
        "track": True,
        "llm": False,
        "tts": True,
        "tts_mode": "diff",
    },
    "security": {
        "fps": 1.0,
        "detect": {"classes": ["person", "car"], "confidence": 0.3, "skip_llm_above": 0.7},
        "track": True,
        "llm": True,
        "llm_model": "llava:7b",
        "guarder": True,
        "tts": True,
        "tts_mode": "diff",
    },
    "describe": {
        "fps": 0.2,
        "detect": {"classes": ["all"], "confidence": 0.3, "skip_llm_above": 1.0},
        "track": False,
        "llm": True,
        "llm_model": "llava:7b",
        "guarder": True,
        "tts": True,
        "tts_mode": "all",
    },
    "count": {
        "fps": 1.0,
        "detect": {"classes": ["person"], "confidence": 0.3, "skip_llm_above": 0.0},
        "track": True,
        "llm": False,
        "tts": True,
        "tts_mode": "diff",
        "output": "count",
    },
    "fast": {
        "fps": 5.0,
        "detect": {"classes": ["person"], "confidence": 0.3, "skip_llm_above": 0.0},
        "track": False,
        "llm": False,
        "tts": True,
        "tts_mode": "diff",
    },
    "patrol": {
        "fps": 0.1,
        "detect": {"classes": ["all"], "confidence": 0.3, "skip_llm_above": 0.5},
        "track": False,
        "llm": True,
        "llm_model": "llava:7b",
        "guarder": True,
        "tts": True,
        "tts_mode": "all",
        "force_periodic": True,
    },
}


@dataclass
class WorkflowConfig:
    """Parsed workflow configuration."""
    name: str = "default"
    fps: float = 1.0
    
    # Detection
    detect_classes: List[str] = field(default_factory=lambda: ["person"])
    detect_confidence: float = 0.3
    skip_llm_above: float = 0.5
    
    # Tracking
    track: bool = True
    reid: bool = True
    
    # LLM
    llm: bool = False
    llm_model: str = "llava:7b"
    guarder: bool = False
    guarder_model: str = "gemma:2b"
    
    # Output
    tts: bool = True
    tts_mode: str = "diff"  # diff, all, none
    log_format: str = "yaml"
    
    # Advanced
    motion_threshold: int = 500
    force_periodic: bool = False
    cache_ttl: int = 30
    
    # Triggers
    triggers: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    def to_env(self) -> Dict[str, str]:
        """Convert to .env format."""
        return {
            "SQ_STREAM_FPS": str(self.fps),
            "SQ_YOLO_CONFIDENCE_THRESHOLD": str(self.detect_confidence),
            "SQ_YOLO_SKIP_LLM_THRESHOLD": str(self.skip_llm_above),
            "SQ_USE_REID": str(self.reid).lower(),
            "SQ_MODEL": self.llm_model,
            "SQ_USE_GUARDER": str(self.guarder).lower(),
            "SQ_GUARDER_MODEL": self.guarder_model,
            "SQ_TTS_MODE": self.tts_mode,
            "SQ_MOTION_GATE_THRESHOLD": str(self.motion_threshold),
            "SQ_LLM_CACHE_TTL": str(self.cache_ttl),
        }
    
    def to_cli_args(self) -> List[str]:
        """Convert to CLI arguments."""
        args = [
            "--mode", "track" if self.track else "full",
            "--focus", self.detect_classes[0] if self.detect_classes else "person",
        ]
        if self.tts:
            args.append("--tts")
            if self.tts_mode == "diff":
                args.append("--tts-diff")
        return args


def load_workflow(path: Optional[str] = None, preset: Optional[str] = None) -> WorkflowConfig:
    """Load workflow from file or preset.
    
    Args:
        path: Path to workflow YAML file
        preset: Preset name (track_person, security, describe, count, fast)
        
    Returns:
        WorkflowConfig instance
    """
    config = WorkflowConfig()
    
    # Load preset first
    if preset and preset in PRESETS:
        p = PRESETS[preset]
        config.name = preset
        config.fps = p.get("fps", 1.0)
        config.detect_classes = p.get("detect", {}).get("classes", ["person"])
        config.detect_confidence = p.get("detect", {}).get("confidence", 0.3)
        config.skip_llm_above = p.get("detect", {}).get("skip_llm_above", 0.5)
        config.track = p.get("track", True)
        config.llm = p.get("llm", False)
        config.llm_model = p.get("llm_model", "llava:7b")
        config.guarder = p.get("guarder", False)
        config.tts = p.get("tts", True)
        config.tts_mode = p.get("tts_mode", "diff")
        config.force_periodic = p.get("force_periodic", False)
    
    # Load from file (overrides preset)
    if path:
        yaml_path = Path(path)
        if yaml_path.exists():
            with open(yaml_path) as f:
                data = yaml.safe_load(f)
            
            if data:
                # Check for preset in file
                if "preset" in data and data["preset"] in PRESETS:
                    return load_workflow(preset=data["preset"])
                
                # Parse pipeline
                if "pipeline" in data:
                    for step in data["pipeline"]:
                        if "capture" in step:
                            config.fps = step["capture"].get("fps", config.fps)
                        elif "detect" in step:
                            config.detect_classes = step["detect"].get("classes", config.detect_classes)
                            config.detect_confidence = step["detect"].get("confidence", config.detect_confidence)
                            config.skip_llm_above = step["detect"].get("skip_llm_above", config.skip_llm_above)
                        elif "track" in step:
                            config.track = True
                            config.reid = step["track"].get("reid", True)
                        elif "describe" in step:
                            config.llm = True
                            config.llm_model = step["describe"].get("model", config.llm_model)
                        elif "notify" in step:
                            config.tts = step["notify"].get("tts", True)
                            config.tts_mode = step["notify"].get("tts_mode", "diff")
                
                # Parse triggers
                if "triggers" in data:
                    config.triggers = data["triggers"]
    
    return config


def apply_workflow(workflow: WorkflowConfig):
    """Apply workflow config to streamware config."""
    from .config import config
    
    env_vars = workflow.to_env()
    for key, value in env_vars.items():
        config.set(key, value)
    
    print(f"✅ Applied workflow: {workflow.name}")
    print(f"   FPS: {workflow.fps}")
    print(f"   Detect: {', '.join(workflow.detect_classes)}")
    print(f"   LLM: {'✓' if workflow.llm else '✗'}")
    print(f"   Track: {'✓' if workflow.track else '✗'}")
    print(f"   TTS: {'✓' if workflow.tts else '✗'} ({workflow.tts_mode})")


def list_presets() -> str:
    """List available presets."""
    lines = ["Available workflow presets:\n"]
    for name, p in PRESETS.items():
        fps = p.get("fps", 1.0)
        llm = "LLM" if p.get("llm") else "YOLO"
        classes = p.get("detect", {}).get("classes", ["person"])
        lines.append(f"  {name:15} - {llm}, {fps} FPS, detect: {', '.join(classes)}")
    return "\n".join(lines)


# =============================================================================
# CLI INTEGRATION
# =============================================================================

def workflow_cli():
    """CLI for workflow management."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: sq workflow <command>")
        print()
        print("Commands:")
        print("  list              List available presets")
        print("  show <preset>     Show preset configuration")
        print("  apply <preset>    Apply preset to current config")
        print("  run <preset>      Run with preset")
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        print(list_presets())
    
    elif cmd == "show" and len(sys.argv) > 2:
        preset = sys.argv[2]
        if preset in PRESETS:
            workflow = load_workflow(preset=preset)
            print(f"Preset: {preset}")
            print()
            for key, value in workflow.to_env().items():
                print(f"  {key}={value}")
        else:
            print(f"Unknown preset: {preset}")
            print(list_presets())
    
    elif cmd == "apply" and len(sys.argv) > 2:
        preset = sys.argv[2]
        workflow = load_workflow(preset=preset)
        apply_workflow(workflow)
    
    elif cmd == "run" and len(sys.argv) > 2:
        preset = sys.argv[2]
        workflow = load_workflow(preset=preset)
        apply_workflow(workflow)
        # Run narrator with workflow settings
        args = workflow.to_cli_args()
        print(f"\nRunning: sq live narrator {' '.join(args)}")


if __name__ == "__main__":
    workflow_cli()
