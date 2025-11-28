"""
HTTP Component for Streamware - HTTP/REST operations
"""

import json
import requests
from typing import Any, Optional, Dict
from urllib.parse import urljoin
from ..core import Component, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)


@register("http")
@register("https")
class HTTPComponent(Component):
    """
    HTTP component for REST API calls
    
    URI formats:
        http://api.example.com/users
        https://api.example.com/users?method=post
        http://localhost:8080/api/data
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        
        # For HTTP URIs, the full URL is stored in uri.url
        if hasattr(uri, 'url'):
            self.url = uri.url
        else:
            # Reconstruct URL from components
            scheme = uri.scheme or 'http'
            host = uri.host or 'localhost'
            path = uri.path or '/'
            self.url = f"{scheme}://{host}{path}"
            
    def process(self, data: Any) -> Any:
        """Process HTTP request"""
        method = self.uri.get_param('method', 'get').lower()
        
        # Headers
        headers = self.uri.get_param('headers', {})
        content_type = self.uri.get_param('content_type', 'application/json')
        
        # Auth
        auth = None
        if self.uri.has_param('username') and self.uri.has_param('password'):
            auth = (self.uri.get_param('username'), self.uri.get_param('password'))
        elif self.uri.has_param('token'):
            headers['Authorization'] = f"Bearer {self.uri.get_param('token')}"
        elif self.uri.has_param('api_key'):
            api_key_header = self.uri.get_param('api_key_header', 'X-API-Key')
            headers[api_key_header] = self.uri.get_param('api_key')
            
        # Timeout
        timeout = self.uri.get_param('timeout', 30)
        
        # SSL verification
        verify_ssl = self.uri.get_param('verify_ssl', True)
        
        try:
            if method == 'get':
                response = self._get(headers, auth, timeout, verify_ssl)
            elif method == 'post':
                response = self._post(data, headers, content_type, auth, timeout, verify_ssl)
            elif method == 'put':
                response = self._put(data, headers, content_type, auth, timeout, verify_ssl)
            elif method == 'patch':
                response = self._patch(data, headers, content_type, auth, timeout, verify_ssl)
            elif method == 'delete':
                response = self._delete(headers, auth, timeout, verify_ssl)
            else:
                raise ComponentError(f"Unsupported HTTP method: {method}")
                
            # Check status code
            response.raise_for_status()
            
            # Parse response
            return self._parse_response(response)
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"HTTP request failed: {e}")
            
    def _get(self, headers: Dict, auth: Any, timeout: int, verify: bool) -> requests.Response:
        """Execute GET request"""
        params = {}
        
        # Add query parameters from URI params (exclude special ones)
        exclude_params = {'method', 'headers', 'content_type', 'username', 'password', 
                         'token', 'api_key', 'api_key_header', 'timeout', 'verify_ssl'}
        
        for key, value in self.uri.params.items():
            if key not in exclude_params:
                params[key] = value
                
        logger.debug(f"GET {self.url} with params: {params}")
        
        return requests.get(
            self.url,
            params=params if params else None,
            headers=headers,
            auth=auth,
            timeout=timeout,
            verify=verify
        )
        
    def _post(self, data: Any, headers: Dict, content_type: str, auth: Any, 
              timeout: int, verify: bool) -> requests.Response:
        """Execute POST request"""
        logger.debug(f"POST {self.url}")
        
        if content_type == 'application/json':
            headers['Content-Type'] = content_type
            return requests.post(
                self.url,
                json=data,
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify
            )
        elif content_type == 'application/x-www-form-urlencoded':
            headers['Content-Type'] = content_type
            return requests.post(
                self.url,
                data=data if isinstance(data, dict) else {'data': data},
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify
            )
        else:
            # Raw data
            headers['Content-Type'] = content_type
            return requests.post(
                self.url,
                data=data if isinstance(data, (str, bytes)) else json.dumps(data),
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify
            )
            
    def _put(self, data: Any, headers: Dict, content_type: str, auth: Any,
             timeout: int, verify: bool) -> requests.Response:
        """Execute PUT request"""
        logger.debug(f"PUT {self.url}")
        
        if content_type == 'application/json':
            headers['Content-Type'] = content_type
            return requests.put(
                self.url,
                json=data,
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify
            )
        else:
            headers['Content-Type'] = content_type
            return requests.put(
                self.url,
                data=data if isinstance(data, (str, bytes)) else json.dumps(data),
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify
            )
            
    def _patch(self, data: Any, headers: Dict, content_type: str, auth: Any,
               timeout: int, verify: bool) -> requests.Response:
        """Execute PATCH request"""
        logger.debug(f"PATCH {self.url}")
        
        if content_type == 'application/json':
            headers['Content-Type'] = content_type
            return requests.patch(
                self.url,
                json=data,
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify
            )
        else:
            headers['Content-Type'] = content_type
            return requests.patch(
                self.url,
                data=data if isinstance(data, (str, bytes)) else json.dumps(data),
                headers=headers,
                auth=auth,
                timeout=timeout,
                verify=verify
            )
            
    def _delete(self, headers: Dict, auth: Any, timeout: int, verify: bool) -> requests.Response:
        """Execute DELETE request"""
        logger.debug(f"DELETE {self.url}")
        
        return requests.delete(
            self.url,
            headers=headers,
            auth=auth,
            timeout=timeout,
            verify=verify
        )
        
    def _parse_response(self, response: requests.Response) -> Any:
        """Parse HTTP response"""
        content_type = response.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
        elif 'text/' in content_type:
            return response.text
        elif 'application/xml' in content_type:
            return response.text
        else:
            # Return raw bytes for binary content
            return response.content


@register("rest")
class RESTComponent(HTTPComponent):
    """REST API component with enhanced features"""
    
    def process(self, data: Any) -> Any:
        """Process REST API call with automatic path handling"""
        # Support RESTful path parameters
        # Example: rest://api.example.com/users/{id}?id=123
        
        # Replace path parameters
        for key, value in self.uri.params.items():
            placeholder = f"{{{key}}}"
            if placeholder in self.url:
                self.url = self.url.replace(placeholder, str(value))
                
        return super().process(data)


@register("webhook")
class WebhookComponent(HTTPComponent):
    """Webhook component for sending webhook notifications"""
    
    def process(self, data: Any) -> Any:
        """Send webhook notification"""
        # Webhooks are typically POST requests
        self.uri.update_param('method', 'post')
        
        # Add webhook-specific headers
        headers = self.uri.get_param('headers', {})
        headers['X-Webhook-Source'] = 'streamware'
        
        if self.uri.has_param('secret'):
            # Add webhook signature
            import hmac
            import hashlib
            
            secret = self.uri.get_param('secret')
            payload = json.dumps(data) if not isinstance(data, str) else data
            signature = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            headers['X-Webhook-Signature'] = signature
            
        self.uri.update_param('headers', headers)
        
        return super().process(data)


@register("graphql")
class GraphQLComponent(HTTPComponent):
    """GraphQL API component"""
    
    def process(self, data: Any) -> Any:
        """Execute GraphQL query"""
        query = self.uri.get_param('query')
        variables = self.uri.get_param('variables', {})
        operation_name = self.uri.get_param('operation_name')
        
        # Get query from data if not in URI
        if not query and isinstance(data, dict):
            query = data.get('query')
            variables = data.get('variables', variables)
            operation_name = data.get('operationName', operation_name)
        elif not query and isinstance(data, str):
            query = data
            
        if not query:
            raise ComponentError("GraphQL query not specified")
            
        # Build GraphQL request
        graphql_data = {
            "query": query,
            "variables": variables
        }
        
        if operation_name:
            graphql_data["operationName"] = operation_name
            
        # GraphQL is always POST with JSON
        self.uri.update_param('method', 'post')
        self.uri.update_param('content_type', 'application/json')
        
        return super().process(graphql_data)


@register("download")
class DownloadComponent(HTTPComponent):
    """Download files from URLs"""
    
    def process(self, data: Any) -> Any:
        """Download file from URL"""
        save_path = self.uri.get_param('path')
        chunk_size = self.uri.get_param('chunk_size', 8192)
        
        if not save_path:
            raise ComponentError("Save path not specified for download")
            
        try:
            response = requests.get(
                self.url,
                stream=True,
                timeout=self.uri.get_param('timeout', 60)
            )
            response.raise_for_status()
            
            # Save to file
            from pathlib import Path
            save_path = Path(save_path).expanduser()
            save_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        
            return {
                "success": True,
                "path": str(save_path),
                "size": save_path.stat().st_size,
                "url": self.url
            }
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Download failed: {e}")
