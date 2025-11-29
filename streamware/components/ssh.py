"""
SSH/SFTP Component for Streamware

Provides secure file transfer and command execution via SSH.
"""

from __future__ import annotations
import os
import json
import subprocess
from pathlib import Path
from typing import Any, Optional, Dict, List
from ..core import Component, register
from ..uri import StreamwareURI
from ..exceptions import ComponentError
from ..diagnostics import get_logger

logger = get_logger(__name__)

# Check for optional dependencies
try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False
    logger.debug("paramiko not installed. SSH features will use system SSH")


@register("ssh")
class SSHComponent(Component):
    """
    SSH/SFTP operations component
    
    Operations:
    - upload: Upload file via SFTP
    - download: Download file via SFTP
    - exec: Execute remote command
    - deploy: Deploy files to remote server
    
    URI Examples:
        ssh://upload?host=server.com&user=deploy&key=/path/to/key&remote=/data/file.txt
        ssh://download?host=server.com&user=deploy&remote=/data/file.txt&local=/tmp/file.txt
        ssh://exec?host=server.com&user=deploy&command=systemctl restart app
        ssh://deploy?host=server.com&user=deploy&path=/app/&restart=true
    """
    
    input_mime = "*/*"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.operation or "upload"
        
        # SSH connection parameters
        self.host = uri.get_param("host", uri.host)
        self.port = uri.get_param("port", 22)
        self.user = uri.get_param("user", os.environ.get("SSH_USER", "root"))
        self.password = uri.get_param("password", os.environ.get("SSH_PASSWORD"))
        self.key_file = uri.get_param("key", os.environ.get("SSH_KEY", "~/.ssh/id_rsa"))
        
        # Paths
        self.remote_path = uri.get_param("remote", uri.path or "/tmp")
        self.local_path = uri.get_param("local", "/tmp")
        
        # Command execution
        self.command = uri.get_param("command")
        
        # Deployment options
        self.restart_service = uri.get_param("restart", False)
        self.backup = uri.get_param("backup", True)
        self.permissions = uri.get_param("permissions", "644")
        
        # Options
        self.strict_host_key = uri.get_param("strict", False)
        self.timeout = uri.get_param("timeout", 30)
        
        if not self.host:
            raise ComponentError("SSH host is required")
    
    def process(self, data: Any) -> Any:
        """Process SSH operation"""
        logger.info(f"SSH operation: {self.operation} on {self.host}")
        
        operations = {
            "upload": self._upload,
            "download": self._download,
            "exec": self._execute_command,
            "deploy": self._deploy,
            "copy": self._upload,  # Alias
            "get": self._download,  # Alias
            "put": self._upload,    # Alias
            "run": self._execute_command,  # Alias
        }
        
        operation_func = operations.get(self.operation)
        if not operation_func:
            raise ComponentError(f"Unknown SSH operation: {self.operation}")
        
        return operation_func(data)
    
    def _upload(self, data: Any) -> Dict:
        """Upload file via SFTP"""
        # Determine local file path
        if isinstance(data, (str, Path)):
            local_file = str(data)
        elif isinstance(data, bytes):
            # Save bytes to temp file
            local_file = f"/tmp/ssh_upload_{os.getpid()}.tmp"
            with open(local_file, "wb") as f:
                f.write(data)
        else:
            raise ComponentError("Data must be file path or bytes")
        
        if not os.path.exists(local_file):
            raise ComponentError(f"Local file not found: {local_file}")
        
        # Determine remote path
        remote = self.remote_path
        if os.path.isfile(local_file):
            filename = os.path.basename(local_file)
            if remote.endswith('/'):
                remote = os.path.join(remote, filename)
        
        logger.info(f"Uploading {local_file} to {self.user}@{self.host}:{remote}")
        
        if PARAMIKO_AVAILABLE:
            return self._upload_paramiko(local_file, remote)
        else:
            return self._upload_scp(local_file, remote)
    
    def _upload_scp(self, local_file: str, remote_path: str) -> Dict:
        """Upload using system SCP"""
        cmd = ["scp"]
        
        # Options
        if not self.strict_host_key:
            cmd.extend(["-o", "StrictHostKeyChecking=no"])
        
        if self.key_file:
            key_file = os.path.expanduser(self.key_file)
            if os.path.exists(key_file):
                cmd.extend(["-i", key_file])
        
        cmd.extend(["-P", str(self.port)])
        
        # Source and destination
        cmd.append(local_file)
        cmd.append(f"{self.user}@{self.host}:{remote_path}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Upload successful: {remote_path}")
                return {
                    "success": True,
                    "operation": "upload",
                    "local": local_file,
                    "remote": remote_path,
                    "host": self.host,
                    "method": "scp"
                }
            else:
                error = result.stderr or "Upload failed"
                logger.error(f"Upload failed: {error}")
                raise ComponentError(f"SCP upload failed: {error}")
                
        except subprocess.TimeoutExpired:
            raise ComponentError(f"SCP upload timed out after {self.timeout}s")
        except Exception as e:
            raise ComponentError(f"SCP upload error: {e}")
    
    def _upload_paramiko(self, local_file: str, remote_path: str) -> Dict:
        """Upload using Paramiko SFTP"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Connect
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.user,
                "timeout": self.timeout,
            }
            
            if self.key_file:
                key_file = os.path.expanduser(self.key_file)
                if os.path.exists(key_file):
                    connect_kwargs["key_filename"] = key_file
            elif self.password:
                connect_kwargs["password"] = self.password
            
            ssh.connect(**connect_kwargs)
            
            # Upload via SFTP
            sftp = ssh.open_sftp()
            sftp.put(local_file, remote_path)
            sftp.close()
            
            ssh.close()
            
            logger.info(f"✓ Upload successful: {remote_path}")
            return {
                "success": True,
                "operation": "upload",
                "local": local_file,
                "remote": remote_path,
                "host": self.host,
                "method": "sftp"
            }
            
        except Exception as e:
            raise ComponentError(f"SFTP upload error: {e}")
    
    def _download(self, data: Any) -> bytes:
        """Download file via SFTP"""
        remote = self.remote_path
        local = self.local_path
        
        if isinstance(data, str):
            local = data
        
        logger.info(f"Downloading {self.user}@{self.host}:{remote} to {local}")
        
        if PARAMIKO_AVAILABLE:
            return self._download_paramiko(remote, local)
        else:
            return self._download_scp(remote, local)
    
    def _download_scp(self, remote_path: str, local_path: str) -> bytes:
        """Download using system SCP"""
        cmd = ["scp"]
        
        if not self.strict_host_key:
            cmd.extend(["-o", "StrictHostKeyChecking=no"])
        
        if self.key_file:
            key_file = os.path.expanduser(self.key_file)
            if os.path.exists(key_file):
                cmd.extend(["-i", key_file])
        
        cmd.extend(["-P", str(self.port)])
        cmd.append(f"{self.user}@{self.host}:{remote_path}")
        cmd.append(local_path)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                with open(local_path, "rb") as f:
                    return f.read()
            else:
                raise ComponentError(f"SCP download failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise ComponentError(f"SCP download timed out")
        except Exception as e:
            raise ComponentError(f"SCP download error: {e}")
    
    def _download_paramiko(self, remote_path: str, local_path: str) -> bytes:
        """Download using Paramiko SFTP"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.user,
                "timeout": self.timeout,
            }
            
            if self.key_file:
                key_file = os.path.expanduser(self.key_file)
                if os.path.exists(key_file):
                    connect_kwargs["key_filename"] = key_file
            elif self.password:
                connect_kwargs["password"] = self.password
            
            ssh.connect(**connect_kwargs)
            
            sftp = ssh.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            
            ssh.close()
            
            with open(local_path, "rb") as f:
                return f.read()
                
        except Exception as e:
            raise ComponentError(f"SFTP download error: {e}")
    
    def _execute_command(self, data: Any) -> Dict:
        """Execute remote command"""
        command = self.command or data
        
        if not command:
            raise ComponentError("No command specified")
        
        logger.info(f"Executing on {self.host}: {command}")
        
        if PARAMIKO_AVAILABLE:
            return self._execute_paramiko(command)
        else:
            return self._execute_ssh(command)
    
    def _execute_ssh(self, command: str) -> Dict:
        """Execute using system SSH"""
        cmd = ["ssh"]
        
        if not self.strict_host_key:
            cmd.extend(["-o", "StrictHostKeyChecking=no"])
        
        if self.key_file:
            key_file = os.path.expanduser(self.key_file)
            if os.path.exists(key_file):
                cmd.extend(["-i", key_file])
        
        cmd.extend(["-p", str(self.port)])
        cmd.append(f"{self.user}@{self.host}")
        cmd.append(command)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            return {
                "success": result.returncode == 0,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": command,
                "host": self.host
            }
            
        except subprocess.TimeoutExpired:
            raise ComponentError(f"Command timed out after {self.timeout}s")
        except Exception as e:
            raise ComponentError(f"SSH command error: {e}")
    
    def _execute_paramiko(self, command: str) -> Dict:
        """Execute using Paramiko"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                "hostname": self.host,
                "port": self.port,
                "username": self.user,
                "timeout": self.timeout,
            }
            
            if self.key_file:
                key_file = os.path.expanduser(self.key_file)
                if os.path.exists(key_file):
                    connect_kwargs["key_filename"] = key_file
            elif self.password:
                connect_kwargs["password"] = self.password
            
            ssh.connect(**connect_kwargs)
            
            stdin, stdout, stderr = ssh.exec_command(command, timeout=self.timeout)
            exit_code = stdout.channel.recv_exit_status()
            
            result = {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout.read().decode('utf-8'),
                "stderr": stderr.read().decode('utf-8'),
                "command": command,
                "host": self.host
            }
            
            ssh.close()
            return result
            
        except Exception as e:
            raise ComponentError(f"SSH command error: {e}")
    
    def _deploy(self, data: Any) -> Dict:
        """Deploy files to remote server"""
        # Upload file(s)
        upload_result = self._upload(data)
        
        results = {
            "upload": upload_result,
            "commands": []
        }
        
        # Set permissions
        if self.permissions:
            perm_result = self._execute_command(
                f"chmod {self.permissions} {self.remote_path}"
            )
            results["commands"].append(perm_result)
        
        # Restart service if requested
        if self.restart_service:
            service_name = self.restart_service if isinstance(self.restart_service, str) else "app"
            restart_result = self._execute_command(
                f"systemctl restart {service_name}"
            )
            results["commands"].append(restart_result)
        
        results["success"] = upload_result["success"] and all(
            cmd.get("success", True) for cmd in results["commands"]
        )
        
        return results


# Quick helpers for common SSH operations
def ssh_upload(host: str, local_file: str, remote_path: str, 
               user: str = "root", key: str = None) -> Dict:
    """Quick SSH upload helper"""
    from ..core import flow
    
    uri = f"ssh://upload?host={host}&user={user}&remote={remote_path}"
    if key:
        uri += f"&key={key}"
    
    return flow(uri).run(local_file)


def ssh_download(host: str, remote_path: str, local_path: str,
                 user: str = "root", key: str = None) -> bytes:
    """Quick SSH download helper"""
    from ..core import flow
    
    uri = f"ssh://download?host={host}&user={user}&remote={remote_path}&local={local_path}"
    if key:
        uri += f"&key={key}"
    
    return flow(uri).run()


def ssh_exec(host: str, command: str, user: str = "root", key: str = None) -> Dict:
    """Quick SSH command execution helper"""
    from ..core import flow
    
    uri = f"ssh://exec?host={host}&user={user}&command={command}"
    if key:
        uri += f"&key={key}"
    
    return flow(uri).run()


def ssh_deploy(host: str, local_file: str, remote_path: str,
               user: str = "deploy", restart: str = None, key: str = None) -> Dict:
    """Quick deployment helper"""
    from ..core import flow
    
    uri = f"ssh://deploy?host={host}&user={user}&path={remote_path}"
    if key:
        uri += f"&key={key}"
    if restart:
        uri += f"&restart={restart}"
    
    return flow(uri).run(local_file)
