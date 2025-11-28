"""
Registry Component for Streamware

Centralized registry for components, models, templates, and configurations.
Enables standardization and sharing of Streamware resources.

# Menu:
- [Overview](#overview)
- [Registration](#registration)
- [Discovery](#discovery)
- [Sharing](#sharing)
- [Examples](#examples)
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("registry")
class RegistryComponent(Component):
    """
    Registry for Streamware resources
    
    Resources:
    - components: Component definitions
    - models: AI model configurations
    - templates: Project templates
    - pipelines: Reusable pipelines
    - configs: Configuration presets
    
    Operations:
    - register: Register a resource
    - lookup: Find a resource
    - list: List all resources
    - remove: Remove a resource
    - export: Export registry
    - import: Import registry
    
    URI Examples:
        registry://register?type=component&name=mycomp
        registry://lookup?type=model&name=qwen2.5:14b
        registry://list?type=templates
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    REGISTRY_PATH = Path.home() / ".streamware" / "registry.json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "list"
        
        self.resource_type = uri.get_param("type", "component")
        self.name = uri.get_param("name")
        self.tags = uri.get_param("tags", "").split(",") if uri.get_param("tags") else []
        
        # Ensure registry exists
        self.REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not self.REGISTRY_PATH.exists():
            self._init_registry()
    
    def process(self, data: Any) -> Dict:
        """Process registry operation"""
        operations = {
            "register": self._register,
            "lookup": self._lookup,
            "list": self._list,
            "remove": self._remove,
            "export": self._export,
            "import": self._import,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _init_registry(self):
        """Initialize empty registry"""
        registry = {
            "version": "1.0",
            "components": self._get_builtin_components(),
            "models": self._get_builtin_models(),
            "templates": self._get_builtin_templates(),
            "pipelines": {},
            "configs": {}
        }
        self._save_registry(registry)
    
    def _get_builtin_components(self) -> Dict:
        """Get built-in components"""
        return {
            "video": {
                "description": "Video processing with RTSP, YOLO, OpenCV",
                "dependencies": ["opencv-python", "ultralytics"],
                "tags": ["video", "ai", "detection"]
            },
            "llm": {
                "description": "LLM operations with multiple providers",
                "dependencies": ["openai", "anthropic"],
                "tags": ["ai", "nlp", "generation"]
            },
            "text2streamware": {
                "description": "Natural language to sq commands",
                "dependencies": [],
                "tags": ["ai", "cli", "automation"]
            },
            "deploy": {
                "description": "Deployment to K8s, Compose, Swarm",
                "dependencies": ["pyyaml"],
                "tags": ["deployment", "kubernetes", "docker"]
            },
            "ssh": {
                "description": "SSH operations and file transfer",
                "dependencies": ["paramiko"],
                "tags": ["network", "deployment", "files"]
            }
        }
    
    def _get_builtin_models(self) -> Dict:
        """Get built-in models"""
        return {
            "qwen2.5:14b": {
                "provider": "ollama",
                "description": "Qwen 14B for code generation",
                "use_case": "text2streamware",
                "tags": ["code", "generation", "ollama"]
            },
            "llama3.2:latest": {
                "provider": "ollama",
                "description": "Llama 3.2 general purpose",
                "use_case": "general",
                "tags": ["general", "ollama"]
            },
            "yolov8n.pt": {
                "provider": "ultralytics",
                "description": "YOLO v8 nano for object detection",
                "use_case": "video",
                "tags": ["detection", "video", "fast"]
            }
        }
    
    def _get_builtin_templates(self) -> Dict:
        """Get built-in templates"""
        return {
            "video-captioning": {
                "description": "Real-time video captioning",
                "components": ["video", "llm"],
                "tags": ["video", "ai", "web"]
            },
            "text2streamware": {
                "description": "Natural language command generation",
                "components": ["text2streamware", "llm"],
                "tags": ["ai", "cli"]
            }
        }
    
    def _register(self, data: Any) -> Dict:
        """Register a resource"""
        if not self.name:
            raise ComponentError("Resource name required")
        
        registry = self._load_registry()
        
        if self.resource_type not in registry:
            registry[self.resource_type] = {}
        
        resource_data = data if isinstance(data, dict) else {"data": data}
        resource_data["tags"] = self.tags
        
        registry[self.resource_type][self.name] = resource_data
        self._save_registry(registry)
        
        return {
            "success": True,
            "type": self.resource_type,
            "name": self.name
        }
    
    def _lookup(self, data: Any) -> Dict:
        """Lookup a resource"""
        if not self.name:
            raise ComponentError("Resource name required")
        
        registry = self._load_registry()
        
        if self.resource_type not in registry:
            return {"found": False}
        
        resource = registry[self.resource_type].get(self.name)
        if not resource:
            return {"found": False}
        
        return {
            "found": True,
            "type": self.resource_type,
            "name": self.name,
            "data": resource
        }
    
    def _list(self, data: Any) -> Dict:
        """List resources"""
        registry = self._load_registry()
        
        if self.resource_type == "all":
            return registry
        
        return {
            "type": self.resource_type,
            "resources": registry.get(self.resource_type, {})
        }
    
    def _remove(self, data: Any) -> Dict:
        """Remove a resource"""
        if not self.name:
            raise ComponentError("Resource name required")
        
        registry = self._load_registry()
        
        if self.resource_type in registry and self.name in registry[self.resource_type]:
            del registry[self.resource_type][self.name]
            self._save_registry(registry)
            return {"success": True, "removed": self.name}
        
        return {"success": False, "error": "Resource not found"}
    
    def _export(self, data: Any) -> Dict:
        """Export registry"""
        registry = self._load_registry()
        return registry
    
    def _import(self, data: Any) -> Dict:
        """Import registry"""
        if not isinstance(data, dict):
            raise ComponentError("Invalid registry data")
        
        self._save_registry(data)
        return {"success": True}
    
    # Helper methods
    def _load_registry(self) -> Dict:
        """Load registry from disk"""
        with open(self.REGISTRY_PATH, 'r') as f:
            return json.load(f)
    
    def _save_registry(self, registry: Dict):
        """Save registry to disk"""
        with open(self.REGISTRY_PATH, 'w') as f:
            json.dump(registry, f, indent=2)


# Quick helpers
def lookup_component(name: str) -> Optional[Dict]:
    """Quick component lookup"""
    from ..core import flow
    result = flow(f"registry://lookup?type=component&name={name}").run()
    return result.get("data") if result.get("found") else None


def list_models() -> Dict:
    """List available models"""
    from ..core import flow
    return flow("registry://list?type=models").run()
