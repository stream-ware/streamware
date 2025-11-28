"""
Setup Component for Streamware

Auto-install system dependencies, Python packages, and manage environments.
Makes `sq` self-contained and able to install dependencies on-the-fly.

# Menu:
- [Installation](#installation)
- [Usage](#usage)
- [Auto Install](#auto-install)
- [System Packages](#system-packages)
- [Python Packages](#python-packages)
- [Docker](#docker)
- [Examples](#examples)
"""

from __future__ import annotations
import os
import sys
import subprocess
import platform
from typing import Any, Dict, List, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("setup")
@register("install")
class SetupComponent(Component):
    """
    Setup and auto-install component
    
    Operations:
    - check: Check if dependencies are installed
    - install: Install dependencies
    - python: Install Python packages
    - system: Install system packages
    - docker: Setup Docker environment
    - ollama: Install and setup Ollama
    - all: Install all dependencies for a component
    
    URI Examples:
        setup://check?packages=opencv-python,numpy
        setup://install?packages=ultralytics
        setup://system?packages=ffmpeg,git
        setup://ollama?model=llama3.2
        setup://all?component=video
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    # Dependency registry
    COMPONENT_DEPS = {
        "video": {
            "python": ["opencv-python", "numpy", "ultralytics"],
            "system": {
                "apt": ["ffmpeg", "libopencv-dev"],
                "brew": ["opencv", "ffmpeg"],
            },
            "ollama": ["llama3.2:latest"]
        },
        "llm": {
            "python": ["openai", "anthropic"],
            "ollama": ["llama3.2:latest"]
        },
        "text2streamware": {
            "python": [],
            "ollama": ["qwen2.5:14b"]
        },
        "deploy": {
            "python": ["pyyaml"],
            "system": {
                "apt": ["kubectl"],
                "brew": ["kubectl"],
            }
        },
        "ssh": {
            "python": ["paramiko"],
            "system": {
                "apt": ["openssh-client"],
                "brew": ["openssh"],
            }
        }
    }
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "check"
        
        # Parameters
        self.packages = uri.get_param("packages", "").split(",") if uri.get_param("packages") else []
        self.component = uri.get_param("component")
        self.model = uri.get_param("model")
        self.force = uri.get_param("force", False)
        self.quiet = uri.get_param("quiet", False)
    
    def process(self, data: Any) -> Dict:
        """Process setup operation"""
        operations = {
            "check": self._check,
            "install": self._install_python,
            "python": self._install_python,
            "system": self._install_system,
            "docker": self._setup_docker,
            "ollama": self._setup_ollama,
            "all": self._install_all,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _check(self, data: Any) -> Dict:
        """Check if dependencies are installed"""
        missing_python = []
        missing_system = []
        
        # Check Python packages
        for pkg in self.packages:
            if not self._is_python_package_installed(pkg):
                missing_python.append(pkg)
        
        return {
            "installed": len(missing_python) == 0,
            "missing_python": missing_python,
            "missing_system": missing_system
        }
    
    def _install_python(self, data: Any) -> Dict:
        """Install Python packages"""
        installed = []
        failed = []
        
        for pkg in self.packages:
            if not self.force and self._is_python_package_installed(pkg):
                logger.info(f"Package {pkg} already installed")
                continue
            
            logger.info(f"Installing Python package: {pkg}")
            
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", pkg],
                    check=True,
                    capture_output=self.quiet,
                    text=True
                )
                installed.append(pkg)
                logger.info(f"✓ Installed {pkg}")
            except subprocess.CalledProcessError as e:
                failed.append(pkg)
                logger.error(f"✗ Failed to install {pkg}: {e}")
        
        return {
            "success": len(failed) == 0,
            "installed": installed,
            "failed": failed
        }
    
    def _install_system(self, data: Any) -> Dict:
        """Install system packages"""
        system = platform.system().lower()
        installed = []
        failed = []
        
        if system == "linux":
            # Detect package manager
            if self._command_exists("apt-get"):
                pm = "apt-get"
            elif self._command_exists("yum"):
                pm = "yum"
            elif self._command_exists("dnf"):
                pm = "dnf"
            else:
                return {"success": False, "error": "No supported package manager found"}
            
            for pkg in self.packages:
                logger.info(f"Installing system package: {pkg}")
                try:
                    subprocess.run(
                        ["sudo", pm, "install", "-y", pkg],
                        check=True,
                        capture_output=self.quiet
                    )
                    installed.append(pkg)
                except subprocess.CalledProcessError:
                    failed.append(pkg)
        
        elif system == "darwin":  # macOS
            for pkg in self.packages:
                try:
                    subprocess.run(
                        ["brew", "install", pkg],
                        check=True,
                        capture_output=self.quiet
                    )
                    installed.append(pkg)
                except subprocess.CalledProcessError:
                    failed.append(pkg)
        
        return {
            "success": len(failed) == 0,
            "installed": installed,
            "failed": failed
        }
    
    def _setup_docker(self, data: Any) -> Dict:
        """Setup Docker environment"""
        # Check if Docker is installed
        if not self._command_exists("docker"):
            logger.error("Docker not installed")
            return {"success": False, "error": "Docker not found"}
        
        # Check if Docker is running
        try:
            subprocess.run(
                ["docker", "ps"],
                check=True,
                capture_output=True
            )
            return {"success": True, "message": "Docker is running"}
        except subprocess.CalledProcessError:
            return {"success": False, "error": "Docker not running"}
    
    def _setup_ollama(self, data: Any) -> Dict:
        """Setup Ollama and pull model"""
        # Check if Ollama is installed
        if not self._command_exists("ollama"):
            logger.info("Installing Ollama...")
            try:
                subprocess.run(
                    "curl -fsSL https://ollama.ai/install.sh | sh",
                    shell=True,
                    check=True
                )
            except subprocess.CalledProcessError:
                return {"success": False, "error": "Failed to install Ollama"}
        
        # Pull model
        if self.model:
            logger.info(f"Pulling Ollama model: {self.model}")
            try:
                subprocess.run(
                    ["ollama", "pull", self.model],
                    check=True,
                    capture_output=self.quiet
                )
                return {"success": True, "model": self.model}
            except subprocess.CalledProcessError:
                return {"success": False, "error": f"Failed to pull model {self.model}"}
        
        return {"success": True}
    
    def _install_all(self, data: Any) -> Dict:
        """Install all dependencies for a component"""
        if not self.component:
            raise ComponentError("Component name required")
        
        deps = self.COMPONENT_DEPS.get(self.component)
        if not deps:
            return {"success": False, "error": f"Unknown component: {self.component}"}
        
        results = {"component": self.component}
        
        # Install Python packages
        if deps.get("python"):
            self.packages = deps["python"]
            results["python"] = self._install_python(data)
        
        # Install system packages
        if deps.get("system"):
            system = platform.system().lower()
            if system == "linux" and "apt" in deps["system"]:
                self.packages = deps["system"]["apt"]
            elif system == "darwin" and "brew" in deps["system"]:
                self.packages = deps["system"]["brew"]
            else:
                self.packages = []
            
            if self.packages:
                results["system"] = self._install_system(data)
        
        # Setup Ollama models
        if deps.get("ollama"):
            for model in deps["ollama"]:
                self.model = model
                results[f"ollama_{model}"] = self._setup_ollama(data)
        
        return results
    
    # Helper methods
    def _is_python_package_installed(self, package: str) -> bool:
        """Check if Python package is installed"""
        try:
            __import__(package.replace("-", "_"))
            return True
        except ImportError:
            return False
    
    def _command_exists(self, command: str) -> bool:
        """Check if command exists"""
        try:
            subprocess.run(
                ["which", command],
                check=True,
                capture_output=True
            )
            return True
        except subprocess.CalledProcessError:
            return False


# Quick helpers
def auto_install(component: str) -> Dict:
    """Auto-install dependencies for component"""
    from ..core import flow
    uri = f"setup://all?component={component}"
    return flow(uri).run()


def check_deps(packages: List[str]) -> Dict:
    """Check if packages are installed"""
    from ..core import flow
    uri = f"setup://check?packages={','.join(packages)}"
    return flow(uri).run()
