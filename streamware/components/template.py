"""
Template Component for Streamware

Generate project templates and examples with one command.
Makes it easy to start new projects based on existing patterns.

# Menu:
- [Templates](#templates)
- [Generate](#generate)
- [Examples](#examples)
- [Customization](#customization)
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("template")
@register("scaffold")
class TemplateComponent(Component):
    """
    Project template generator
    
    Templates:
    - video-captioning: RTSP + YOLO + LLM + Web
    - api-pipeline: HTTP + Transform + Database
    - monitoring: Health checks + Alerts
    - data-etl: Extract + Transform + Load
    - deployment: K8s + CI/CD
    - text2streamware: LLM command generation
    
    Operations:
    - generate: Generate project from template
    - list: List available templates
    - info: Show template information
    
    URI Examples:
        template://generate?name=video-captioning&output=/path
        template://list
        template://info?name=api-pipeline
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    TEMPLATES = {
        "video-captioning": {
            "description": "Real-time video captioning with RTSP, YOLO, and LLM",
            "files": ["video_captioning_complete.py", "README.md", "install.sh"],
            "source": "projects/video-captioning",
            "dependencies": ["opencv-python", "ultralytics", "flask"],
            "components": ["video", "llm"]
        },
        "api-pipeline": {
            "description": "API data pipeline with transformation and storage",
            "dependencies": ["requests", "pandas"],
            "components": ["http", "transform", "postgres"]
        },
        "monitoring": {
            "description": "System monitoring with alerts",
            "dependencies": [],
            "components": ["ssh", "slack", "postgres"]
        },
        "text2streamware": {
            "description": "Natural language to sq commands",
            "source": "projects/text2streamware-demo",
            "dependencies": [],
            "components": ["text2streamware", "llm"]
        }
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "generate"
        
        self.template_name = uri.get_param("name") or uri.get_param("template")
        self.output_path = uri.get_param("output", ".")
        self.auto_install = uri.get_param("auto_install", True)
    
    def process(self, data: Any) -> Dict:
        """Process template operation"""
        operations = {
            "generate": self._generate,
            "list": self._list_templates,
            "info": self._info,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _generate(self, data: Any) -> Dict:
        """Generate project from template"""
        if not self.template_name:
            raise ComponentError("Template name required")
        
        template = self.TEMPLATES.get(self.template_name)
        if not template:
            raise ComponentError(f"Unknown template: {self.template_name}")
        
        output_dir = Path(self.output_path) / self.template_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Generating {self.template_name} in {output_dir}")
        
        # Copy template files if source exists
        if template.get("source"):
            source_dir = Path(__file__).parent.parent.parent / template["source"]
            if source_dir.exists():
                shutil.copytree(source_dir, output_dir, dirs_exist_ok=True)
        
        # Auto-install dependencies
        if self.auto_install:
            for component in template.get("components", []):
                logger.info(f"Installing dependencies for {component}")
                from .setup import auto_install
                auto_install(component)
        
        return {
            "success": True,
            "template": self.template_name,
            "output": str(output_dir),
            "dependencies_installed": self.auto_install
        }
    
    def _list_templates(self, data: Any) -> Dict:
        """List available templates"""
        return {
            "templates": [
                {
                    "name": name,
                    "description": info["description"]
                }
                for name, info in self.TEMPLATES.items()
            ]
        }
    
    def _info(self, data: Any) -> Dict:
        """Show template information"""
        if not self.template_name:
            raise ComponentError("Template name required")
        
        template = self.TEMPLATES.get(self.template_name)
        if not template:
            raise ComponentError(f"Unknown template: {self.template_name}")
        
        return {
            "name": self.template_name,
            **template
        }


# Quick helper
def generate_project(template: str, output: str = ".") -> Dict:
    """Quick project generation"""
    from ..core import flow
    uri = f"template://generate?name={template}&output={output}"
    return flow(uri).run()
