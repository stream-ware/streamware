"""
MIME type validation and mapping for Streamware
"""

from typing import Any, Optional, Dict
import json
import mimetypes


class MimeValidator:
    """MIME type validation and compatibility checking"""
    
    # Standard MIME type mappings for schemes
    SCHEME_MIME_MAP = {
        # Data formats
        "json": "application/json",
        "xml": "application/xml",
        "csv": "text/csv",
        "txt": "text/plain",
        "html": "text/html",
        
        # Media types
        "mp4": "video/mp4",
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "pcm": "audio/pcm",
        "rtsp": "application/x-rtsp",
        "hls": "application/vnd.apple.mpegurl",
        
        # Stream types
        "stream": "application/octet-stream",
        "file": "application/octet-stream",
        
        # Structured data
        "sql": "application/sql",
        "bql": "application/x-bql",
        
        # Message formats
        "kafka": "application/x-kafka",
        "rabbitmq": "application/x-amqp",
        "mqtt": "application/x-mqtt",
    }
    
    # MIME type compatibility matrix
    COMPATIBLE_TYPES = {
        "application/json": ["text/plain", "application/octet-stream"],
        "text/plain": ["application/octet-stream"],
        "text/csv": ["text/plain", "application/octet-stream"],
        "application/xml": ["text/plain", "application/octet-stream"],
        "video/mp4": ["application/octet-stream", "video/*"],
        "audio/wav": ["audio/pcm", "application/octet-stream", "audio/*"],
        "audio/mpeg": ["application/octet-stream", "audio/*"],
    }
    
    @classmethod
    def get_mime_for_scheme(cls, scheme: str) -> Optional[str]:
        """Get MIME type for a URI scheme"""
        return cls.SCHEME_MIME_MAP.get(scheme)
        
    @classmethod
    def detect_mime(cls, data: Any) -> str:
        """Detect MIME type from data"""
        if data is None:
            return "application/octet-stream"
            
        if isinstance(data, dict):
            return "application/json"
        elif isinstance(data, (list, tuple)):
            return "application/json"
        elif isinstance(data, str):
            # Try to detect if it's JSON
            if data.strip().startswith(('{', '[')):
                try:
                    json.loads(data)
                    return "application/json"
                except json.JSONDecodeError:
                    pass
            # Check if it's XML
            if data.strip().startswith('<'):
                return "application/xml"
            # Check if it's CSV
            if '\n' in data and ',' in data.split('\n')[0]:
                return "text/csv"
            return "text/plain"
        elif isinstance(data, bytes):
            # Try to detect from bytes
            if data.startswith(b'\x89PNG'):
                return "image/png"
            elif data.startswith(b'\xff\xd8\xff'):
                return "image/jpeg"
            elif data.startswith(b'GIF89'):
                return "image/gif"
            elif data.startswith(b'%PDF'):
                return "application/pdf"
            else:
                return "application/octet-stream"
        else:
            return "application/octet-stream"
            
    @classmethod
    def is_compatible(cls, output_mime: str, input_mime: str) -> bool:
        """Check if two MIME types are compatible"""
        # Exact match
        if output_mime == input_mime:
            return True
            
        # Check wildcard matches
        if '*' in input_mime:
            base_type = input_mime.split('/')[0]
            if output_mime.startswith(base_type):
                return True
                
        if '*' in output_mime:
            base_type = output_mime.split('/')[0]
            if input_mime.startswith(base_type):
                return True
                
        # Check compatibility matrix
        if output_mime in cls.COMPATIBLE_TYPES:
            if input_mime in cls.COMPATIBLE_TYPES[output_mime]:
                return True
                
        # application/octet-stream is compatible with everything
        if input_mime == "application/octet-stream" or output_mime == "application/octet-stream":
            return True
            
        return False
        
    @classmethod
    def validate(cls, data: Any, expected_mime: str) -> bool:
        """Validate that data matches expected MIME type"""
        detected = cls.detect_mime(data)
        if not cls.is_compatible(detected, expected_mime):
            from .exceptions import MimeTypeError
            raise MimeTypeError(
                f"Data MIME type {detected} is not compatible with expected {expected_mime}"
            )
        return True
        
    @classmethod
    def convert(cls, data: Any, from_mime: str, to_mime: str) -> Any:
        """Convert data between MIME types if possible"""
        # JSON to text
        if from_mime == "application/json" and to_mime == "text/plain":
            if isinstance(data, (dict, list)):
                return json.dumps(data, indent=2)
            return str(data)
            
        # Text to JSON
        if from_mime == "text/plain" and to_mime == "application/json":
            if isinstance(data, str):
                try:
                    return json.loads(data)
                except json.JSONDecodeError:
                    return {"text": data}
                    
        # CSV to JSON
        if from_mime == "text/csv" and to_mime == "application/json":
            import csv
            import io
            
            if isinstance(data, str):
                reader = csv.DictReader(io.StringIO(data))
                return list(reader)
                
        # JSON to CSV
        if from_mime == "application/json" and to_mime == "text/csv":
            import csv
            import io
            
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                output = io.StringIO()
                if data:
                    writer = csv.DictWriter(output, fieldnames=data[0].keys())
                    writer.writeheader()
                    writer.writerows(data)
                return output.getvalue()
                
        # Default: return as-is
        return data
        
    @classmethod
    def get_file_extension(cls, mime_type: str) -> str:
        """Get file extension for MIME type"""
        extensions = {
            "application/json": ".json",
            "application/xml": ".xml",
            "text/csv": ".csv",
            "text/plain": ".txt",
            "text/html": ".html",
            "video/mp4": ".mp4",
            "audio/mpeg": ".mp3",
            "audio/wav": ".wav",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "application/pdf": ".pdf",
        }
        return extensions.get(mime_type, "")
