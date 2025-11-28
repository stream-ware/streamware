"""
URI parser for Streamware - handles Camel-style URIs
"""

from urllib.parse import urlparse, parse_qs, unquote
from typing import Dict, Optional, Any
import json


class StreamwareURI:
    """Parser for Streamware URIs in Camel style"""
    
    def __init__(self, uri: str):
        """
        Parse URI in format: scheme://path?param1=value1&param2=value2
        
        Examples:
            http://api.example.com/users
            file://read?path=/tmp/data.json
            transform://jsonpath?query=$.items[*]
            kafka://consume?topic=events&group=processor
        """
        self.raw = uri
        
        # Handle special case for HTTP/HTTPS URLs
        if uri.startswith(('http://', 'https://')):
            self._parse_http_uri(uri)
        else:
            self._parse_standard_uri(uri)
            
    def _parse_http_uri(self, uri: str):
        """Parse HTTP/HTTPS URIs specially"""
        parsed = urlparse(uri)
        self.scheme = parsed.scheme
        self.host = parsed.netloc
        self.path = parsed.path
        self.params = self._parse_params(parsed.query)
        
        # Store full URL for HTTP requests
        if '?' in uri:
            self.url = uri[:uri.index('?')]
        else:
            self.url = uri
            
    def _parse_standard_uri(self, uri: str):
        """Parse standard Streamware URIs"""
        parsed = urlparse(uri)
        self.scheme = parsed.scheme
        
        # For Streamware URIs, netloc is usually the operation (e.g., file://read)
        # unless there's an actual path (e.g., file:///path/to/file)
        if parsed.netloc and not parsed.path.strip('/'):
            # netloc is the operation
            self.operation = parsed.netloc
            self.host = None
            self.path = parsed.netloc
        else:
            # path contains the operation
            self.host = parsed.netloc if parsed.netloc else None
            self.path = parsed.path.lstrip('/')
            self.operation = self.path if self.path else None
        
        self.params = self._parse_params(parsed.query)
        
    def _parse_params(self, query_string: str) -> Dict[str, Any]:
        """Parse query parameters and convert types"""
        if not query_string:
            return {}
            
        params = {}
        for key, values in parse_qs(query_string).items():
            value = values[0]  # Take first value for duplicates
            
            # Unescape value
            value = unquote(value)
            
            # Try to parse as JSON for complex types
            if value.startswith(('{', '[')):
                try:
                    params[key] = json.loads(value)
                except json.JSONDecodeError:
                    params[key] = value
            # Parse booleans
            elif value.lower() in ('true', 'false'):
                params[key] = value.lower() == 'true'
            # Parse numbers
            elif value.replace('.', '', 1).replace('-', '', 1).isdigit():
                try:
                    params[key] = int(value) if '.' not in value else float(value)
                except ValueError:
                    params[key] = value
            else:
                params[key] = value
                
        return params
        
    def get_param(self, key: str, default: Any = None) -> Any:
        """Get parameter with default value"""
        return self.params.get(key, default)
        
    def has_param(self, key: str) -> bool:
        """Check if parameter exists"""
        return key in self.params
        
    def update_param(self, key: str, value: Any) -> None:
        """Update a parameter value"""
        self.params[key] = value
        
    def to_string(self) -> str:
        """Reconstruct URI string from components"""
        if self.scheme in ('http', 'https'):
            base = self.url
        else:
            base = f"{self.scheme}://"
            if self.host:
                base += self.host
            if self.path:
                base += f"/{self.path}"
                
        if self.params:
            query_parts = []
            for key, value in self.params.items():
                if isinstance(value, (dict, list)):
                    value = json.dumps(value)
                elif isinstance(value, bool):
                    value = str(value).lower()
                else:
                    value = str(value)
                query_parts.append(f"{key}={value}")
            base += '?' + '&'.join(query_parts)
            
        return base
        
    def __str__(self) -> str:
        return self.to_string()
        
    def __repr__(self) -> str:
        return f"StreamwareURI('{self.raw}')"
        
    def copy(self) -> 'StreamwareURI':
        """Create a copy of this URI"""
        return StreamwareURI(self.to_string())
