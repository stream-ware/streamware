"""
Service Component for Streamware

Simple service deployment without Docker/systemd.
Perfect for quick deployments on Linux machines.

# Menu:
- [Quick Start](#quick-start)
- [Service Management](#service-management)
- [Examples](#examples)
"""

from __future__ import annotations
import os
import signal
import subprocess
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None
from typing import Any, Dict, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("service")
@register("svc")
class ServiceComponent(Component):
    """
    Simple service management
    
    Operations:
    - start: Start a service
    - stop: Stop a service
    - restart: Restart a service
    - status: Check service status
    - install: Install as background service
    - uninstall: Remove service
    
    URI Examples:
        service://start?name=myapp&command=python app.py
        service://stop?name=myapp
        service://status?name=myapp
        service://install?name=myapp&command=python app.py&dir=/path
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    SERVICES_DIR = Path.home() / ".streamware" / "services"
    PIDS_DIR = Path.home() / ".streamware" / "pids"
    LOGS_DIR = Path.home() / ".streamware" / "logs"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "start"
        
        self.name = uri.get_param("name")
        self.command = uri.get_param("command") or uri.get_param("cmd")
        self.directory = uri.get_param("dir") or uri.get_param("directory", ".")
        self.env = uri.get_param("env", {})
        self.auto_restart = uri.get_param("auto_restart", False)
        
        # Ensure directories exist
        self.SERVICES_DIR.mkdir(parents=True, exist_ok=True)
        self.PIDS_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    def process(self, data: Any) -> Dict:
        """Process service operation"""
        if not self.name:
            raise ComponentError("Service name required")
        
        operations = {
            "start": self._start,
            "stop": self._stop,
            "restart": self._restart,
            "status": self._status,
            "install": self._install,
            "uninstall": self._uninstall,
            "list": self._list_services,
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        return operation_func(data)
    
    def _start(self, data: Any) -> Dict:
        """Start service"""
        if not self.command:
            # Try to load from installed service
            service_file = self.SERVICES_DIR / f"{self.name}.txt"
            if service_file.exists():
                config = self._load_service_config(service_file)
                self.command = config.get("command")
                self.directory = config.get("directory", ".")
            else:
                raise ComponentError("Command required to start service")
        
        # Check if already running
        if self._is_running():
            return {
                "success": False,
                "message": f"Service {self.name} is already running",
                "pid": self._get_pid()
            }
        
        # Start service in background
        log_file = self.LOGS_DIR / f"{self.name}.log"
        
        with open(log_file, 'a') as log:
            process = subprocess.Popen(
                self.command,
                shell=True,
                cwd=self.directory,
                stdout=log,
                stderr=log,
                env={**os.environ, **self.env},
                start_new_session=True
            )
        
        # Save PID
        pid_file = self.PIDS_DIR / f"{self.name}.pid"
        pid_file.write_text(str(process.pid))
        
        logger.info(f"Started service {self.name} with PID {process.pid}")
        
        return {
            "success": True,
            "message": f"Service {self.name} started",
            "pid": process.pid,
            "log_file": str(log_file)
        }
    
    def _stop(self, data: Any) -> Dict:
        """Stop service"""
        if not self._is_running():
            return {
                "success": False,
                "message": f"Service {self.name} is not running"
            }
        
        pid = self._get_pid()
        
        try:
            # Try graceful shutdown
            os.kill(pid, signal.SIGTERM)
            
            # Wait for process to stop
            import time
            for _ in range(10):
                if not self._is_running():
                    break
                time.sleep(0.5)
            
            # Force kill if still running
            if self._is_running():
                os.kill(pid, signal.SIGKILL)
            
            # Remove PID file
            pid_file = self.PIDS_DIR / f"{self.name}.pid"
            if pid_file.exists():
                pid_file.unlink()
            
            logger.info(f"Stopped service {self.name}")
            
            return {
                "success": True,
                "message": f"Service {self.name} stopped"
            }
            
        except ProcessLookupError:
            return {
                "success": False,
                "message": f"Process {pid} not found"
            }
    
    def _restart(self, data: Any) -> Dict:
        """Restart service"""
        self._stop(data)
        import time
        time.sleep(1)
        return self._start(data)
    
    def _status(self, data: Any) -> Dict:
        """Check service status"""
        running = self._is_running()
        pid = self._get_pid() if running else None
        
        status = {
            "service": self.name,
            "running": running,
            "pid": pid
        }
        
        if running and pid and psutil:
            try:
                process = psutil.Process(pid)
                status["cpu_percent"] = process.cpu_percent()
                status["memory_mb"] = process.memory_info().rss / 1024 / 1024
                status["uptime"] = psutil.boot_time()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        return status
    
    def _install(self, data: Any) -> Dict:
        """Install service"""
        if not self.command:
            raise ComponentError("Command required to install service")
        
        # Save service configuration
        service_file = self.SERVICES_DIR / f"{self.name}.txt"
        
        config = {
            "name": self.name,
            "command": self.command,
            "directory": self.directory,
            "env": self.env,
            "auto_restart": self.auto_restart
        }
        
        import json
        service_file.write_text(json.dumps(config, indent=2))
        
        # Optionally start immediately
        if data and data.get("start"):
            return self._start(data)
        
        return {
            "success": True,
            "message": f"Service {self.name} installed",
            "config_file": str(service_file)
        }
    
    def _uninstall(self, data: Any) -> Dict:
        """Uninstall service"""
        # Stop if running
        if self._is_running():
            self._stop(data)
        
        # Remove config
        service_file = self.SERVICES_DIR / f"{self.name}.txt"
        if service_file.exists():
            service_file.unlink()
        
        # Remove PID file
        pid_file = self.PIDS_DIR / f"{self.name}.pid"
        if pid_file.exists():
            pid_file.unlink()
        
        return {
            "success": True,
            "message": f"Service {self.name} uninstalled"
        }
    
    def _list_services(self, data: Any) -> Dict:
        """List all services"""
        services = []
        
        for service_file in self.SERVICES_DIR.glob("*.txt"):
            service_name = service_file.stem
            config = self._load_service_config(service_file)
            
            # Check if running
            self.name = service_name
            running = self._is_running()
            
            services.append({
                "name": service_name,
                "command": config.get("command"),
                "running": running,
                "pid": self._get_pid() if running else None
            })
        
        return {
            "services": services,
            "count": len(services)
        }
    
    # Helper methods
    def _is_running(self) -> bool:
        """Check if service is running"""
        pid = self._get_pid()
        if not pid:
            return False
        
        if psutil:
            try:
                process = psutil.Process(pid)
                return process.is_running()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        else:
            # Fallback: check if PID exists
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                return False
    
    def _get_pid(self) -> Optional[int]:
        """Get service PID"""
        pid_file = self.PIDS_DIR / f"{self.name}.pid"
        if not pid_file.exists():
            return None
        
        try:
            return int(pid_file.read_text().strip())
        except (ValueError, OSError):
            return None
    
    def _load_service_config(self, service_file: Path) -> Dict:
        """Load service configuration"""
        import json
        try:
            return json.loads(service_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}


# Quick helpers
def start_service(name: str, command: str, directory: str = ".") -> Dict:
    """Quick service start"""
    from ..core import flow
    uri = f"service://start?name={name}&command={command}&dir={directory}"
    return flow(uri).run()


def stop_service(name: str) -> Dict:
    """Quick service stop"""
    from ..core import flow
    uri = f"service://stop?name={name}"
    return flow(uri).run()


def service_status(name: str) -> Dict:
    """Quick service status"""
    from ..core import flow
    uri = f"service://status?name={name}"
    return flow(uri).run()
