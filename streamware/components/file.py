"""
File Component for Streamware - file system operations
"""

import os
import json
import csv
import time
from pathlib import Path
from typing import Any, Optional, Iterator, Dict, List
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError

logger = get_logger(__name__)


@register("file")
class FileComponent(Component):
    """
    File component for file system operations
    
    URI formats:
        file://read?path=/tmp/data.json
        file://write?path=/tmp/output.csv&mode=append
        file://watch?path=/tmp/uploads&pattern=*.json
        file://list?path=/tmp&recursive=true
    """
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "read"
        
    def process(self, data: Any) -> Any:
        """Process data based on file operation"""
        if self.operation == "read":
            return self._read()
        elif self.operation == "write":
            return self._write(data)
        elif self.operation == "append":
            return self._append(data)
        elif self.operation == "delete":
            return self._delete()
        elif self.operation == "list":
            return self._list()
        elif self.operation == "exists":
            return self._exists()
        elif self.operation == "watch":
            return self._watch()
        else:
            raise ComponentError(f"Unknown file operation: {self.operation}")
            
    def _read(self) -> Any:
        """Read file contents"""
        path = self.uri.get_param('path')
        if not path:
            raise ComponentError("File path not specified")
            
        path = Path(path).expanduser()
        if not path.exists():
            raise ComponentError(f"File not found: {path}")
            
        encoding = self.uri.get_param('encoding', 'utf-8')
        as_binary = self.uri.get_param('binary', False)
        
        try:
            if as_binary:
                with open(path, 'rb') as f:
                    return f.read()
            else:
                with open(path, 'r', encoding=encoding) as f:
                    content = f.read()
                    
                # Auto-detect format
                if path.suffix == '.json':
                    return json.loads(content)
                elif path.suffix == '.csv':
                    reader = csv.DictReader(content.splitlines())
                    return list(reader)
                else:
                    return content
                    
        except Exception as e:
            raise ComponentError(f"Error reading file {path}: {e}")
            
    def _write(self, data: Any) -> Dict[str, Any]:
        """Write data to file"""
        path = self.uri.get_param('path')
        if not path:
            raise ComponentError("File path not specified")
            
        path = Path(path).expanduser()
        
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)
        
        encoding = self.uri.get_param('encoding', 'utf-8')
        mode = self.uri.get_param('mode', 'w')
        
        try:
            # Auto-detect format from extension
            if path.suffix == '.json':
                content = json.dumps(data, indent=2)
            elif path.suffix == '.csv':
                if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                    import io
                    output = io.StringIO()
                    if data:
                        writer = csv.DictWriter(output, fieldnames=data[0].keys())
                        writer.writeheader()
                        writer.writerows(data)
                    content = output.getvalue()
                else:
                    content = str(data)
            else:
                content = str(data)
                
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
                
            return {
                "success": True,
                "path": str(path),
                "size": len(content),
                "mode": mode
            }
            
        except Exception as e:
            raise ComponentError(f"Error writing file {path}: {e}")
            
    def _append(self, data: Any) -> Dict[str, Any]:
        """Append data to file"""
        self.uri.update_param('mode', 'a')
        return self._write(data)
        
    def _delete(self) -> Dict[str, Any]:
        """Delete file"""
        path = self.uri.get_param('path')
        if not path:
            raise ComponentError("File path not specified")
            
        path = Path(path).expanduser()
        
        try:
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                return {"success": False, "error": "Path does not exist"}
                
            return {"success": True, "path": str(path)}
            
        except Exception as e:
            raise ComponentError(f"Error deleting {path}: {e}")
            
    def _list(self) -> List[Dict[str, Any]]:
        """List files in directory"""
        path = self.uri.get_param('path', '.')
        path = Path(path).expanduser()
        
        if not path.exists():
            raise ComponentError(f"Path not found: {path}")
            
        pattern = self.uri.get_param('pattern', '*')
        recursive = self.uri.get_param('recursive', False)
        
        files = []
        
        try:
            if recursive:
                for file_path in path.rglob(pattern):
                    files.append(self._file_info(file_path))
            else:
                for file_path in path.glob(pattern):
                    files.append(self._file_info(file_path))
                    
            return files
            
        except Exception as e:
            raise ComponentError(f"Error listing files in {path}: {e}")
            
    def _exists(self) -> bool:
        """Check if file exists"""
        path = self.uri.get_param('path')
        if not path:
            raise ComponentError("File path not specified")
            
        return Path(path).expanduser().exists()
        
    def _watch(self) -> List[str]:
        """Watch directory for changes (simple implementation)"""
        path = self.uri.get_param('path', '.')
        path = Path(path).expanduser()
        
        if not path.exists():
            raise ComponentError(f"Path not found: {path}")
            
        pattern = self.uri.get_param('pattern', '*')
        
        # This is a simple snapshot comparison
        # For production, use watchdog or inotify
        
        initial_files = set(path.glob(pattern))
        time.sleep(1)  # Wait a bit
        current_files = set(path.glob(pattern))
        
        new_files = current_files - initial_files
        
        return [str(f) for f in new_files]
        
    def _file_info(self, path: Path) -> Dict[str, Any]:
        """Get file information"""
        stat = path.stat()
        return {
            "path": str(path),
            "name": path.name,
            "type": "file" if path.is_file() else "directory",
            "size": stat.st_size,
            "modified": stat.st_mtime,
            "created": stat.st_ctime
        }


@register("file-read")
class FileReadComponent(Component):
    """Dedicated file read component"""
    
    output_mime = "application/octet-stream"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "read"
        self.file = FileComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.file._read()


@register("file-write")
class FileWriteComponent(Component):
    """Dedicated file write component"""
    
    input_mime = "application/octet-stream"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "write"
        self.file = FileComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.file._write(data)


@register("file-watch")
class FileWatchComponent(StreamComponent):
    """File watcher component for monitoring changes"""
    
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.path = Path(uri.get_param('path', '.')).expanduser()
        self.pattern = uri.get_param('pattern', '*')
        self.interval = uri.get_param('interval', 1)
        
        if not self.path.exists():
            raise ComponentError(f"Path not found: {self.path}")
            
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream file changes"""
        seen_files = set()
        
        # Initial scan
        for file_path in self.path.glob(self.pattern):
            seen_files.add(file_path)
            
        logger.info(f"Watching {self.path} for changes (pattern: {self.pattern})")
        
        while True:
            current_files = set(self.path.glob(self.pattern))
            new_files = current_files - seen_files
            deleted_files = seen_files - current_files
            
            for file_path in new_files:
                yield {
                    "event": "created",
                    "path": str(file_path),
                    "timestamp": time.time()
                }
                
            for file_path in deleted_files:
                yield {
                    "event": "deleted",
                    "path": str(file_path),
                    "timestamp": time.time()
                }
                
            # Check for modified files
            for file_path in current_files & seen_files:
                # Simple modification check based on mtime
                # For production, track and compare mtimes
                pass
                
            seen_files = current_files
            time.sleep(self.interval)
            
    def process(self, data: Any) -> Any:
        """Non-streaming watch (returns current snapshot)"""
        files = []
        for file_path in self.path.glob(self.pattern):
            stat = file_path.stat()
            files.append({
                "path": str(file_path),
                "size": stat.st_size,
                "modified": stat.st_mtime
            })
        return files


@register("file-lines")
class FileLinesComponent(StreamComponent):
    """Stream file line by line"""
    
    output_mime = "text/plain"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.path = uri.get_param('path')
        if not self.path:
            raise ComponentError("File path not specified")
            
        self.path = Path(self.path).expanduser()
        if not self.path.exists():
            raise ComponentError(f"File not found: {self.path}")
            
        self.encoding = uri.get_param('encoding', 'utf-8')
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Stream file lines"""
        with open(self.path, 'r', encoding=self.encoding) as f:
            for line in f:
                yield line.rstrip('\n')
                
    def process(self, data: Any) -> Any:
        """Read all lines"""
        with open(self.path, 'r', encoding=self.encoding) as f:
            return f.readlines()
