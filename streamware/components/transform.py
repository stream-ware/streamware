"""
Transform Component for Streamware - data transformation operations
"""

import json
import csv
import io
import re
from typing import Any, Optional, Iterator, Dict, List
from ..core import Component, StreamComponent, register
from ..uri import StreamwareURI
from ..diagnostics import get_logger
from ..exceptions import ComponentError

logger = get_logger(__name__)

try:
    from jsonpath_ng import parse as jsonpath_parse
    JSONPATH_AVAILABLE = True
except ImportError:
    JSONPATH_AVAILABLE = False
    logger.debug("jsonpath-ng not installed. JSONPath transformations will be limited.")

try:
    from jinja2 import Template, Environment, FileSystemLoader
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logger.debug("Jinja2 not installed. Template transformations will not be available.")


@register("transform")
class TransformComponent(Component):
    """
    Transform component for data transformations
    
    URI formats:
        transform://json?pretty=true
        transform://csv?delimiter=;
        transform://jsonpath?query=$.items[*].name
        transform://template?file=template.j2
        transform://base64?decode=true
        transform://regex?pattern=\\d+&replace=X
    """
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.operation = uri.path or uri.operation or "json"
        
    def process(self, data: Any) -> Any:
        """Process data based on transformation type"""
        if self.operation == "json":
            return self._transform_json(data)
        elif self.operation == "csv":
            return self._transform_csv(data)
        elif self.operation == "jsonpath":
            return self._transform_jsonpath(data)
        elif self.operation == "template":
            return self._transform_template(data)
        elif self.operation == "base64":
            return self._transform_base64(data)
        elif self.operation == "regex":
            return self._transform_regex(data)
        elif self.operation == "normalize":
            return self._normalize(data)
        elif self.operation == "flatten":
            return self._flatten(data)
        elif self.operation == "merge":
            return self._merge(data)
        else:
            raise ComponentError(f"Unknown transform operation: {self.operation}")
            
    def _transform_json(self, data: Any) -> Any:
        """Transform to/from JSON"""
        if isinstance(data, str):
            # Parse JSON string
            try:
                return json.loads(data)
            except json.JSONDecodeError as e:
                raise ComponentError(f"Invalid JSON: {e}")
        else:
            # Convert to JSON string
            pretty = self.uri.get_param('pretty', False)
            if pretty:
                return json.dumps(data, indent=2, ensure_ascii=False)
            else:
                return json.dumps(data, ensure_ascii=False)
                
    def _transform_csv(self, data: Any) -> Any:
        """Transform to/from CSV"""
        delimiter = self.uri.get_param('delimiter', ',')
        
        if isinstance(data, str):
            # Parse CSV string
            reader = csv.DictReader(io.StringIO(data), delimiter=delimiter)
            return list(reader)
        elif isinstance(data, list):
            # Convert to CSV string
            if not data:
                return ""
                
            output = io.StringIO()
            
            if all(isinstance(item, dict) for item in data):
                # List of dicts -> CSV
                fieldnames = data[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=delimiter)
                writer.writeheader()
                writer.writerows(data)
            elif all(isinstance(item, (list, tuple)) for item in data):
                # List of lists -> CSV
                writer = csv.writer(output, delimiter=delimiter)
                writer.writerows(data)
            else:
                # Simple list -> single column CSV
                writer = csv.writer(output, delimiter=delimiter)
                for item in data:
                    writer.writerow([item])
                    
            return output.getvalue()
        else:
            raise ComponentError("CSV transformation requires string or list input")
            
    def _transform_jsonpath(self, data: Any) -> Any:
        """Apply JSONPath query to data"""
        if not JSONPATH_AVAILABLE:
            raise ComponentError("JSONPath support not available. Install with: pip install jsonpath-ng")
            
        query = self.uri.get_param('query') or self.uri.get_param('path')
        if not query:
            raise ComponentError("JSONPath query not specified")
            
        try:
            expr = jsonpath_parse(query)
            matches = expr.find(data)
            
            # Extract values from matches
            results = [match.value for match in matches]
            
            # Return single value if only one match
            if len(results) == 1:
                return results[0]
            return results
            
        except Exception as e:
            raise ComponentError(f"JSONPath error: {e}")
            
    def _transform_template(self, data: Any) -> str:
        """Apply Jinja2 template transformation"""
        if not JINJA2_AVAILABLE:
            raise ComponentError("Template support not available. Install with: pip install Jinja2")
            
        template_file = self.uri.get_param('file')
        template_str = self.uri.get_param('template')
        
        if not template_file and not template_str:
            raise ComponentError("Template file or template string not specified")
            
        try:
            if template_file:
                # Load template from file
                from pathlib import Path
                template_path = Path(template_file)
                
                if template_path.exists():
                    env = Environment(loader=FileSystemLoader(template_path.parent))
                    template = env.get_template(template_path.name)
                else:
                    raise ComponentError(f"Template file not found: {template_file}")
            else:
                # Use template string
                template = Template(template_str)
                
            # Render template with data
            if isinstance(data, dict):
                return template.render(**data)
            else:
                return template.render(data=data)
                
        except Exception as e:
            raise ComponentError(f"Template error: {e}")
            
    def _transform_base64(self, data: Any) -> Any:
        """Encode/decode base64"""
        import base64
        
        decode = self.uri.get_param('decode', False)
        
        if decode:
            # Decode base64
            if isinstance(data, str):
                try:
                    return base64.b64decode(data).decode('utf-8')
                except Exception:
                    return base64.b64decode(data)
            elif isinstance(data, bytes):
                return base64.b64decode(data)
            else:
                raise ComponentError("Base64 decode requires string or bytes input")
        else:
            # Encode to base64
            if isinstance(data, str):
                return base64.b64encode(data.encode()).decode('ascii')
            elif isinstance(data, bytes):
                return base64.b64encode(data).decode('ascii')
            else:
                # Convert to JSON first, then encode
                json_str = json.dumps(data)
                return base64.b64encode(json_str.encode()).decode('ascii')
                
    def _transform_regex(self, data: Any) -> Any:
        """Apply regex transformation"""
        pattern = self.uri.get_param('pattern')
        if not pattern:
            raise ComponentError("Regex pattern not specified")
            
        replace = self.uri.get_param('replace')
        extract = self.uri.get_param('extract', False)
        
        if not isinstance(data, str):
            data = str(data)
            
        try:
            if extract:
                # Extract matches
                matches = re.findall(pattern, data)
                return matches if matches else None
            elif replace is not None:
                # Replace matches
                return re.sub(pattern, replace, data)
            else:
                # Test if pattern matches
                return bool(re.search(pattern, data))
                
        except re.error as e:
            raise ComponentError(f"Regex error: {e}")
            
    def _normalize(self, data: Any) -> Any:
        """Normalize data structure"""
        # Convert various formats to consistent structure
        if isinstance(data, str):
            # Try to parse as JSON
            try:
                return json.loads(data)
            except Exception:
                return {"value": data}
        elif isinstance(data, (list, tuple)):
            return list(data)
        elif isinstance(data, dict):
            return data
        else:
            return {"value": data}
            
    def _flatten(self, data: Any) -> Any:
        """Flatten nested data structure"""
        if not isinstance(data, dict):
            return data
            
        def flatten_dict(d, parent_key='', sep='_'):
            items = []
            for k, v in d.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                if isinstance(v, dict):
                    items.extend(flatten_dict(v, new_key, sep=sep).items())
                else:
                    items.append((new_key, v))
            return dict(items)
            
        return flatten_dict(data)
        
    def _merge(self, data: Any) -> Any:
        """Merge multiple data items"""
        if not isinstance(data, list):
            return data
            
        if all(isinstance(item, dict) for item in data):
            # Merge dictionaries
            result = {}
            for item in data:
                result.update(item)
            return result
        elif all(isinstance(item, list) for item in data):
            # Concatenate lists
            result = []
            for item in data:
                result.extend(item)
            return result
        else:
            # Return as-is
            return data


@register("transform-jsonpath")
@register("jsonpath")
class JSONPathComponent(Component):
    """Dedicated JSONPath component"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "jsonpath"
        self.transform = TransformComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.transform._transform_jsonpath(data)


@register("transform-template")
@register("template")
class TemplateComponent(Component):
    """Dedicated template component"""
    
    input_mime = "application/json"
    output_mime = "text/plain"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "template"
        self.transform = TransformComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.transform._transform_template(data)


@register("transform-csv")
@register("csv")
class CSVComponent(Component):
    """Dedicated CSV component"""
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        uri.operation = "csv"
        self.transform = TransformComponent(uri)
        
    def process(self, data: Any) -> Any:
        return self.transform._transform_csv(data)


@register("transform-stream")
class TransformStreamComponent(StreamComponent):
    """Streaming transform component"""
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        self.transform = TransformComponent(uri)
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Transform each item in stream"""
        if input_stream:
            for item in input_stream:
                try:
                    yield self.transform.process(item)
                except Exception as e:
                    logger.error(f"Error transforming item: {e}")
                    yield {"error": str(e), "input": item}


@register("enrich")
class EnrichComponent(Component):
    """Enrich data with additional information"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Enrich data with metadata"""
        import time
        from datetime import datetime
        
        if not isinstance(data, dict):
            data = {"value": data}
            
        # Add enrichment metadata
        enrichment = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "processing_node": "streamware",
        }
        
        # Add custom fields from URI params
        for key, value in self.uri.params.items():
            if key not in ['path', 'operation']:
                enrichment[key] = value
                
        data["_metadata"] = enrichment
        return data


@register("validate")
class ValidateComponent(Component):
    """Validate data against schema or rules"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        """Validate data"""
        # Simple validation based on URI params
        required_fields = self.uri.get_param('required', '').split(',')
        min_length = self.uri.get_param('min_length')
        max_length = self.uri.get_param('max_length')
        pattern = self.uri.get_param('pattern')
        
        errors = []
        
        if isinstance(data, dict):
            # Check required fields
            for field in required_fields:
                if field and field not in data:
                    errors.append(f"Missing required field: {field}")
                    
        if isinstance(data, (str, list, dict)):
            # Check length
            length = len(data)
            if min_length and length < int(min_length):
                errors.append(f"Length {length} is less than minimum {min_length}")
            if max_length and length > int(max_length):
                errors.append(f"Length {length} exceeds maximum {max_length}")
                
        if pattern and isinstance(data, str):
            # Check pattern match
            if not re.match(pattern, data):
                errors.append(f"Data does not match pattern: {pattern}")
                
        if errors:
            raise ComponentError(f"Validation failed: {', '.join(errors)}")
            
        return data
