"""
Deployment Component for Streamware

Deploy applications to various platforms: Kubernetes, Docker Compose, Docker Swarm, etc.
"""

from __future__ import annotations
import os
import json
import yaml
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)


@register("deploy")
@register("k8s")
@register("kubernetes")
class DeployComponent(Component):
    """
    Deployment operations for various platforms
    
    Platforms:
    - kubernetes (k8s): Deploy to Kubernetes cluster
    - compose: Docker Compose deployment
    - swarm: Docker Swarm deployment
    - docker: Direct Docker deployment
    
    Operations:
    - apply: Apply deployment
    - delete: Remove deployment
    - update: Update deployment
    - scale: Scale replicas
    - status: Check deployment status
    - logs: Get logs
    - rollback: Rollback to previous version
    
    URI Examples:
        deploy://k8s?manifest=app.yaml&namespace=production
        deploy://compose?file=docker-compose.yml&project=myapp
        deploy://swarm?stack=myapp&compose=docker-compose.yml
        k8s://apply?file=deployment.yaml&namespace=default
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "apply"
        self.platform = uri.scheme if uri.scheme in ["k8s", "kubernetes"] else uri.get_param("platform", "k8s")
        
        # Common parameters
        self.manifest_file = uri.get_param("manifest") or uri.get_param("file")
        self.namespace = uri.get_param("namespace", "default")
        self.name = uri.get_param("name")
        
        # Kubernetes specific
        self.context = uri.get_param("context")
        self.kubeconfig = uri.get_param("kubeconfig", os.environ.get("KUBECONFIG"))
        
        # Docker Compose specific
        self.compose_file = uri.get_param("compose") or uri.get_param("file", "docker-compose.yml")
        self.project_name = uri.get_param("project")
        
        # Docker Swarm specific
        self.stack_name = uri.get_param("stack")
        
        # Scaling
        self.replicas = uri.get_param("replicas")
        
        # Image
        self.image = uri.get_param("image")
        self.tag = uri.get_param("tag", "latest")
        
        # Options
        self.dry_run = uri.get_param("dry_run", False)
        self.wait = uri.get_param("wait", True)
    
    def process(self, data: Any) -> Dict:
        """Process deployment operation"""
        logger.info(f"Deployment: {self.operation} on {self.platform}")
        
        operations = {
            "apply": self._apply,
            "delete": self._delete,
            "update": self._update,
            "scale": self._scale,
            "status": self._status,
            "logs": self._logs,
            "rollback": self._rollback,
            "create": self._apply,  # Alias
            "remove": self._delete,  # Alias
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown operation: {self.operation}")
        
        # Platform-specific execution
        if self.platform in ["k8s", "kubernetes"]:
            return self._execute_k8s(operation_func, data)
        elif self.platform == "compose":
            return self._execute_compose(operation_func, data)
        elif self.platform == "swarm":
            return self._execute_swarm(operation_func, data)
        elif self.platform == "docker":
            return self._execute_docker(operation_func, data)
        else:
            raise ComponentError(f"Unknown platform: {self.platform}")
    
    # Kubernetes Operations
    def _execute_k8s(self, operation_func, data):
        """Execute Kubernetes operation"""
        return operation_func(data)
    
    def _apply(self, data: Any) -> Dict:
        """Apply deployment"""
        if self.platform in ["k8s", "kubernetes"]:
            return self._k8s_apply(data)
        elif self.platform == "compose":
            return self._compose_up(data)
        elif self.platform == "swarm":
            return self._swarm_deploy(data)
    
    def _k8s_apply(self, data: Any) -> Dict:
        """Apply Kubernetes manifest"""
        cmd = ["kubectl", "apply"]
        
        # Context
        if self.context:
            cmd.extend(["--context", self.context])
        
        # Kubeconfig
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        
        # Namespace
        cmd.extend(["-n", self.namespace])
        
        # Manifest file or data
        if self.manifest_file:
            cmd.extend(["-f", self.manifest_file])
        elif data:
            # Write data to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                if isinstance(data, dict):
                    yaml.dump(data, f)
                else:
                    f.write(str(data))
                temp_file = f.name
            cmd.extend(["-f", temp_file])
        else:
            raise ComponentError("No manifest file or data provided")
        
        # Dry run
        if self.dry_run:
            cmd.append("--dry-run=client")
        
        # Execute
        result = self._run_command(cmd)
        
        logger.info(f"Applied to Kubernetes: {result['stdout']}")
        
        return {
            "success": result["returncode"] == 0,
            "platform": "kubernetes",
            "operation": "apply",
            "namespace": self.namespace,
            "output": result["stdout"],
            "error": result["stderr"]
        }
    
    def _delete(self, data: Any) -> Dict:
        """Delete deployment"""
        if self.platform in ["k8s", "kubernetes"]:
            return self._k8s_delete(data)
        elif self.platform == "compose":
            return self._compose_down(data)
        elif self.platform == "swarm":
            return self._swarm_remove(data)
    
    def _k8s_delete(self, data: Any) -> Dict:
        """Delete Kubernetes resources"""
        cmd = ["kubectl", "delete"]
        
        if self.context:
            cmd.extend(["--context", self.context])
        
        if self.kubeconfig:
            cmd.extend(["--kubeconfig", self.kubeconfig])
        
        cmd.extend(["-n", self.namespace])
        
        if self.manifest_file:
            cmd.extend(["-f", self.manifest_file])
        elif self.name:
            cmd.extend(["deployment", self.name])
        else:
            raise ComponentError("No manifest or name specified")
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "kubernetes",
            "operation": "delete",
            "output": result["stdout"]
        }
    
    def _update(self, data: Any) -> Dict:
        """Update deployment"""
        if self.platform in ["k8s", "kubernetes"]:
            return self._k8s_update(data)
    
    def _k8s_update(self, data: Any) -> Dict:
        """Update Kubernetes deployment image"""
        if not self.name or not self.image:
            raise ComponentError("Name and image required for update")
        
        cmd = [
            "kubectl", "set", "image",
            f"deployment/{self.name}",
            f"{self.name}={self.image}:{self.tag}",
            "-n", self.namespace
        ]
        
        if self.context:
            cmd.extend(["--context", self.context])
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "kubernetes",
            "operation": "update",
            "deployment": self.name,
            "image": f"{self.image}:{self.tag}",
            "output": result["stdout"]
        }
    
    def _scale(self, data: Any) -> Dict:
        """Scale deployment"""
        if self.platform in ["k8s", "kubernetes"]:
            return self._k8s_scale(data)
        elif self.platform == "compose":
            return self._compose_scale(data)
    
    def _k8s_scale(self, data: Any) -> Dict:
        """Scale Kubernetes deployment"""
        if not self.name or not self.replicas:
            raise ComponentError("Name and replicas required for scaling")
        
        cmd = [
            "kubectl", "scale",
            f"deployment/{self.name}",
            f"--replicas={self.replicas}",
            "-n", self.namespace
        ]
        
        if self.context:
            cmd.extend(["--context", self.context])
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "kubernetes",
            "operation": "scale",
            "deployment": self.name,
            "replicas": self.replicas,
            "output": result["stdout"]
        }
    
    def _status(self, data: Any) -> Dict:
        """Get deployment status"""
        if self.platform in ["k8s", "kubernetes"]:
            return self._k8s_status(data)
        elif self.platform == "compose":
            return self._compose_status(data)
    
    def _k8s_status(self, data: Any) -> Dict:
        """Get Kubernetes deployment status"""
        cmd = ["kubectl", "get", "deployments", "-n", self.namespace, "-o", "json"]
        
        if self.name:
            cmd.insert(3, self.name)
        
        if self.context:
            cmd.extend(["--context", self.context])
        
        result = self._run_command(cmd)
        
        if result["returncode"] == 0:
            status_data = json.loads(result["stdout"])
        else:
            status_data = {}
        
        return {
            "success": result["returncode"] == 0,
            "platform": "kubernetes",
            "operation": "status",
            "data": status_data
        }
    
    def _logs(self, data: Any) -> str:
        """Get deployment logs"""
        if self.platform in ["k8s", "kubernetes"]:
            return self._k8s_logs(data)
    
    def _k8s_logs(self, data: Any) -> str:
        """Get Kubernetes pod logs"""
        if not self.name:
            raise ComponentError("Deployment name required for logs")
        
        cmd = [
            "kubectl", "logs",
            f"deployment/{self.name}",
            "-n", self.namespace,
            "--tail=100"
        ]
        
        if self.context:
            cmd.extend(["--context", self.context])
        
        result = self._run_command(cmd)
        
        return result["stdout"]
    
    def _rollback(self, data: Any) -> Dict:
        """Rollback deployment"""
        if self.platform in ["k8s", "kubernetes"]:
            return self._k8s_rollback(data)
    
    def _k8s_rollback(self, data: Any) -> Dict:
        """Rollback Kubernetes deployment"""
        if not self.name:
            raise ComponentError("Deployment name required for rollback")
        
        cmd = [
            "kubectl", "rollout", "undo",
            f"deployment/{self.name}",
            "-n", self.namespace
        ]
        
        if self.context:
            cmd.extend(["--context", self.context])
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "kubernetes",
            "operation": "rollback",
            "deployment": self.name,
            "output": result["stdout"]
        }
    
    # Docker Compose Operations
    def _execute_compose(self, operation_func, data):
        """Execute Docker Compose operation"""
        return operation_func(data)
    
    def _compose_up(self, data: Any) -> Dict:
        """Docker Compose up"""
        cmd = ["docker-compose"]
        
        if self.compose_file:
            cmd.extend(["-f", self.compose_file])
        
        if self.project_name:
            cmd.extend(["-p", self.project_name])
        
        cmd.extend(["up", "-d"])
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "compose",
            "operation": "up",
            "project": self.project_name,
            "output": result["stdout"]
        }
    
    def _compose_down(self, data: Any) -> Dict:
        """Docker Compose down"""
        cmd = ["docker-compose"]
        
        if self.compose_file:
            cmd.extend(["-f", self.compose_file])
        
        if self.project_name:
            cmd.extend(["-p", self.project_name])
        
        cmd.append("down")
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "compose",
            "operation": "down",
            "output": result["stdout"]
        }
    
    def _compose_scale(self, data: Any) -> Dict:
        """Docker Compose scale"""
        if not self.name or not self.replicas:
            raise ComponentError("Service name and replicas required")
        
        cmd = ["docker-compose"]
        
        if self.compose_file:
            cmd.extend(["-f", self.compose_file])
        
        if self.project_name:
            cmd.extend(["-p", self.project_name])
        
        cmd.extend(["up", "-d", "--scale", f"{self.name}={self.replicas}"])
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "compose",
            "operation": "scale",
            "service": self.name,
            "replicas": self.replicas,
            "output": result["stdout"]
        }
    
    def _compose_status(self, data: Any) -> Dict:
        """Docker Compose status"""
        cmd = ["docker-compose"]
        
        if self.compose_file:
            cmd.extend(["-f", self.compose_file])
        
        if self.project_name:
            cmd.extend(["-p", self.project_name])
        
        cmd.append("ps")
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "compose",
            "operation": "status",
            "output": result["stdout"]
        }
    
    # Docker Swarm Operations
    def _execute_swarm(self, operation_func, data):
        """Execute Docker Swarm operation"""
        return operation_func(data)
    
    def _swarm_deploy(self, data: Any) -> Dict:
        """Deploy Docker Swarm stack"""
        if not self.stack_name:
            raise ComponentError("Stack name required")
        
        cmd = ["docker", "stack", "deploy"]
        
        if self.compose_file:
            cmd.extend(["-c", self.compose_file])
        
        cmd.append(self.stack_name)
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "swarm",
            "operation": "deploy",
            "stack": self.stack_name,
            "output": result["stdout"]
        }
    
    def _swarm_remove(self, data: Any) -> Dict:
        """Remove Docker Swarm stack"""
        if not self.stack_name:
            raise ComponentError("Stack name required")
        
        cmd = ["docker", "stack", "rm", self.stack_name]
        
        result = self._run_command(cmd)
        
        return {
            "success": result["returncode"] == 0,
            "platform": "swarm",
            "operation": "remove",
            "stack": self.stack_name,
            "output": result["stdout"]
        }
    
    # Docker Operations
    def _execute_docker(self, operation_func, data):
        """Execute Docker operation"""
        return operation_func(data)
    
    # Helper methods
    def _run_command(self, cmd: List[str]) -> Dict:
        """Run shell command"""
        try:
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
        except subprocess.TimeoutExpired:
            raise ComponentError("Command timed out")
        except FileNotFoundError:
            raise ComponentError(f"Command not found: {cmd[0]}")
        except Exception as e:
            raise ComponentError(f"Command execution failed: {e}")


# Quick helper functions
def deploy_k8s(manifest: str, namespace: str = "default", context: str = None) -> Dict:
    """Quick Kubernetes deployment"""
    from ..core import flow
    
    uri = f"k8s://apply?manifest={manifest}&namespace={namespace}"
    if context:
        uri += f"&context={context}"
    
    return flow(uri).run()


def deploy_compose(compose_file: str, project: str = None) -> Dict:
    """Quick Docker Compose deployment"""
    from ..core import flow
    
    uri = f"deploy://compose?file={compose_file}"
    if project:
        uri += f"&project={project}"
    
    return flow(uri).run()


def scale_k8s(name: str, replicas: int, namespace: str = "default") -> Dict:
    """Quick Kubernetes scaling"""
    from ..core import flow
    
    uri = f"k8s://scale?name={name}&replicas={replicas}&namespace={namespace}"
    return flow(uri).run()
