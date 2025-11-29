"""
CurLLM Component - Web automation with LLM integration for Streamware
"""

import json
import requests
from typing import Any, Optional, Dict, List, Iterator
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError, ConnectionError

logger = get_logger(__name__)

# Try to import curllm dependencies
try:
    from playwright.sync_api import sync_playwright
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.debug("Playwright not installed. Some CurLLM features will be limited.")

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.debug("Ollama not installed. CurLLM will use HTTP API.")


@register("curllm")
class CurLLMComponent(Component):
    """
    CurLLM component for web automation with LLM
    
    URI format:
        curllm://action?url=https://example.com&param=value
        
    Actions:
        - browse: Navigate to URL and interact with page
        - extract: Extract data using LLM instructions
        - fill_form: Fill forms using provided data
        - screenshot: Take screenshot
        - bql: Execute BQL (Browser Query Language)
        - api: Direct API call to CurLLM server
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.action = uri.path or uri.operation or "browse"
        self.api_host = uri.get_param('api_host', 'http://localhost:8000')
        self.ollama_host = uri.get_param('ollama_host', 'http://localhost:11434')
        self.model = uri.get_param('model', 'qwen2.5:7b')
        
    def process(self, data: Any) -> Any:
        """Process data based on CurLLM action"""
        
        if self.action == "browse":
            return self._browse(data)
        elif self.action == "extract":
            return self._extract(data)
        elif self.action == "fill_form":
            return self._fill_form(data)
        elif self.action == "screenshot":
            return self._screenshot(data)
        elif self.action == "bql":
            return self._execute_bql(data)
        elif self.action == "api":
            return self._api_call(data)
        else:
            raise ComponentError(f"Unknown CurLLM action: {self.action}")
            
    def _browse(self, data: Any) -> Dict[str, Any]:
        """Browse to URL and interact with page"""
        url = self.uri.get_param('url')
        if not url and isinstance(data, dict):
            url = data.get('url')
        if not url:
            raise ComponentError("No URL specified for browsing")
            
        # Build request payload
        payload = {
            "url": url,
            "visual_mode": self.uri.get_param('visual', False),
            "stealth_mode": self.uri.get_param('stealth', False),
            "captcha_solver": self.uri.get_param('captcha', False),
        }
        
        # Add instruction if provided
        instruction = self.uri.get_param('instruction')
        if instruction:
            payload["data"] = instruction
        elif isinstance(data, dict) and 'instruction' in data:
            payload["data"] = data['instruction']
            
        # Add additional params
        if self.uri.get_param('session'):
            payload["session_id"] = self.uri.get_param('session')
            
        return self._make_request(payload)
        
    def _extract(self, data: Any) -> Dict[str, Any]:
        """Extract data from page using LLM"""
        url = self.uri.get_param('url')
        instruction = self.uri.get_param('instruction')
        
        # Get from input data if not in URI
        if isinstance(data, dict):
            url = url or data.get('url')
            instruction = instruction or data.get('instruction')
            
        if not url:
            raise ComponentError("No URL specified for extraction")
        if not instruction:
            raise ComponentError("No extraction instruction provided")
            
        payload = {
            "url": url,
            "data": {
                "instruction": instruction,
                "params": {
                    "hierarchical_planner": self.uri.get_param('planner', True),
                    "visual_mode": self.uri.get_param('visual', False),
                    "stealth_mode": self.uri.get_param('stealth', True),
                }
            }
        }
        
        return self._make_request(payload)
        
    def _fill_form(self, data: Any) -> Dict[str, Any]:
        """Fill forms on a webpage"""
        url = self.uri.get_param('url')
        form_data = self.uri.get_param('data')
        
        # Get from input data if not in URI
        if isinstance(data, dict):
            url = url or data.get('url')
            form_data = form_data or data.get('form_data', data)
            
        if not url:
            raise ComponentError("No URL specified for form filling")
        if not form_data:
            raise ComponentError("No form data provided")
            
        # Build instruction for form filling
        instruction = self._build_form_instruction(form_data)
        
        payload = {
            "url": url,
            "data": {
                "instruction": instruction,
                "params": {
                    "hierarchical_planner": True,
                    "visual_mode": self.uri.get_param('visual', True),
                    "stealth_mode": self.uri.get_param('stealth', True),
                    "llm_orchestrator": True,
                }
            }
        }
        
        return self._make_request(payload)
        
    def _screenshot(self, data: Any) -> Dict[str, Any]:
        """Take screenshot of webpage"""
        url = self.uri.get_param('url')
        
        if not url and isinstance(data, dict):
            url = data.get('url')
        if not url:
            raise ComponentError("No URL specified for screenshot")
            
        payload = {
            "url": url,
            "data": "Take a screenshot",
            "visual_mode": True,
        }
        
        return self._make_request(payload)
        
    def _execute_bql(self, data: Any) -> Dict[str, Any]:
        """Execute BQL (Browser Query Language) query"""
        query = self.uri.get_param('query')
        
        if not query and isinstance(data, dict):
            query = data.get('query')
        elif not query and isinstance(data, str):
            query = data
            
        if not query:
            raise ComponentError("No BQL query provided")
            
        payload = {
            "use_bql": True,
            "data": query
        }
        
        # Extract URL from BQL query if present
        if 'url:' in query:
            import re
            url_match = re.search(r'url:\s*["\']([^"\']+)["\']', query)
            if url_match:
                payload["url"] = url_match.group(1)
                
        return self._make_request(payload)
        
    def _api_call(self, data: Any) -> Dict[str, Any]:
        """Direct API call to CurLLM server"""
        if isinstance(data, dict):
            payload = data
        else:
            payload = {"data": data}
            
        # Add URI params to payload
        for key, value in self.uri.params.items():
            if key not in ['api_host', 'ollama_host', 'model']:
                payload[key] = value
                
        return self._make_request(payload)
        
    def _make_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP request to CurLLM API"""
        try:
            url = f"{self.api_host}/api/execute"
            
            logger.debug(f"CurLLM request to {url}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)[:500]}")
            
            response = requests.post(
                url,
                json=payload,
                timeout=120  # 2 minute timeout for complex operations
            )
            
            response.raise_for_status()
            result = response.json()
            
            logger.debug(f"CurLLM response: {json.dumps(result, indent=2)[:500]}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"CurLLM API error: {e}")
        except json.JSONDecodeError as e:
            raise ComponentError(f"Invalid response from CurLLM API: {e}")
            
    def _build_form_instruction(self, form_data: Dict[str, Any]) -> str:
        """Build form filling instruction from data"""
        parts = ["Fill the form with the following data:"]
        
        for field, value in form_data.items():
            # Convert field names to readable format
            readable_field = field.replace('_', ' ').title()
            parts.append(f"{readable_field}: {value}")
            
        return " ".join(parts)


@register("curllm-stream")
class CurLLMStreamComponent(StreamComponent):
    """
    Streaming version of CurLLM component for processing multiple pages/tasks
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.base_component = CurLLMComponent(uri)
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Process stream of URLs or tasks"""
        if input_stream:
            for item in input_stream:
                try:
                    result = self.base_component.process(item)
                    yield result
                except Exception as e:
                    logger.error(f"Error processing item in stream: {e}")
                    yield {"error": str(e), "input": item}


@register("web")
class WebComponent(Component):
    """
    Simple web component for basic HTTP requests (complementary to CurLLM)
    """
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Make simple HTTP request"""
        url = self.uri.get_param('url')
        method = self.uri.get_param('method', 'get').lower()
        headers = self.uri.get_param('headers', {})
        
        # Get from input data if not in URI
        if isinstance(data, dict):
            url = url or data.get('url')
            method = data.get('method', method)
            headers.update(data.get('headers', {}))
            
        if not url:
            raise ComponentError("No URL specified for web request")
            
        try:
            if method == 'get':
                response = requests.get(url, headers=headers)
            elif method == 'post':
                json_data = data if isinstance(data, dict) else None
                response = requests.post(url, json=json_data, headers=headers)
            elif method == 'put':
                json_data = data if isinstance(data, dict) else None
                response = requests.put(url, json=json_data, headers=headers)
            elif method == 'delete':
                response = requests.delete(url, headers=headers)
            else:
                raise ComponentError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            
            # Try to return JSON if possible
            try:
                return response.json()
            except json.JSONDecodeError:
                return response.text
                
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Web request failed: {e}")


# Helper functions for common CurLLM operations

def browse(url: str, instruction: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Browse to URL and optionally interact with page
    
    Args:
        url: URL to browse
        instruction: Optional instruction for interaction
        **kwargs: Additional parameters (visual, stealth, captcha, etc.)
        
    Returns:
        Result from CurLLM
    """
    uri = f"curllm://browse?url={url}"
    if instruction:
        uri += f"&instruction={instruction}"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = CurLLMComponent(StreamwareURI(uri))
    return component.process(None)


def extract_data(url: str, instruction: str, **kwargs) -> Dict[str, Any]:
    """
    Extract data from webpage using LLM
    
    Args:
        url: URL to extract from
        instruction: Extraction instruction
        **kwargs: Additional parameters
        
    Returns:
        Extracted data
    """
    uri = f"curllm://extract?url={url}&instruction={instruction}"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = CurLLMComponent(StreamwareURI(uri))
    return component.process(None)


def fill_form(url: str, form_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """
    Fill form on webpage
    
    Args:
        url: URL with form
        form_data: Data to fill
        **kwargs: Additional parameters
        
    Returns:
        Result of form submission
    """
    uri = f"curllm://fill_form?url={url}"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = CurLLMComponent(StreamwareURI(uri))
    return component.process({"form_data": form_data})


def execute_bql(query: str, **kwargs) -> Dict[str, Any]:
    """
    Execute BQL query
    
    Args:
        query: BQL query string
        **kwargs: Additional parameters
        
    Returns:
        Query results
    """
    uri = "curllm://bql"
    for key, value in kwargs.items():
        uri += f"&{key}={value}"
        
    component = CurLLMComponent(StreamwareURI(uri))
    return component.process({"query": query})
