"""
Simplified DSL (Domain-Specific Language) for Streamware

This module provides alternative, more Pythonic APIs for creating pipelines.
"""

from typing import Any, Callable, Dict, List, Optional, Union
from .core import flow, Flow, Component, register
from .uri import StreamwareURI


# ============================================================================
# 1. FLUENT API - Method Chaining Style
# ============================================================================

class Pipeline:
    """
    Fluent API for building pipelines with method chaining
    
    Example:
        result = (
            Pipeline()
            .http_get("https://api.example.com/data")
            .to_json()
            .filter(lambda x: x['age'] > 18)
            .to_csv()
            .save("output.csv")
            .run()
        )
    """
    
    def __init__(self):
        self._flow = None
        self._data = None
        
    def configure(self, key: str, value: str) -> 'Pipeline':
        """Set configuration value"""
        from .config import config
        config.set(key, value)
        return self
        
    # HTTP Methods
    def http_get(self, url: str, **params) -> 'Pipeline':
        """HTTP GET request"""
        query = "&".join(f"{k}={v}" for k, v in params.items())
        uri = f"{url}?{query}" if query else url
        self._flow = flow(uri)
        return self
        
    def http_post(self, url: str, data: Any = None) -> 'Pipeline':
        """HTTP POST request"""
        self._flow = flow(f"{url}?method=post")
        if data:
            self._data = data
        return self
        
    # File Operations
    def read_file(self, path: str) -> 'Pipeline':
        """Read file"""
        self._flow = flow(f"file://read?path={path}")
        return self
        
    def save(self, path: str, mode: str = "write") -> 'Pipeline':
        """Save to file"""
        if self._flow is None:
            raise ValueError("Pipeline must have a source")
        self._flow = self._flow | f"file://{mode}?path={path}"
        return self
        
    # Transformations
    def to_json(self, pretty: bool = False) -> 'Pipeline':
        """Convert to/from JSON"""
        uri = "transform://json"
        if pretty:
            uri += "?pretty=true"
        self._flow = self._flow | uri
        return self
        
    def to_csv(self, delimiter: str = ",") -> 'Pipeline':
        """Convert to CSV"""
        self._flow = self._flow | f"transform://csv?delimiter={delimiter}"
        return self
        
    def to_base64(self, decode: bool = False) -> 'Pipeline':
        """Base64 encode/decode"""
        uri = "transform://base64"
        if decode:
            uri += "?decode=true"
        self._flow = self._flow | uri
        return self
        
    def jsonpath(self, query: str) -> 'Pipeline':
        """Extract data using JSONPath"""
        self._flow = self._flow | f"transform://jsonpath?query={query}"
        return self
        
    # Filtering and Processing
    def filter(self, predicate: Callable) -> 'Pipeline':
        """Filter data with custom predicate"""
        # Create temporary filter component
        @register("_temp_filter")
        class TempFilter(Component):
            def process(self, data):
                if isinstance(data, list):
                    return [item for item in data if predicate(item)]
                return data if predicate(data) else None
                
        self._flow = self._flow | "_temp_filter://"
        return self
        
    def map(self, func: Callable) -> 'Pipeline':
        """Map function over data"""
        @register("_temp_map")
        class TempMap(Component):
            def process(self, data):
                if isinstance(data, list):
                    return [func(item) for item in data]
                return func(data)
                
        self._flow = self._flow | "_temp_map://"
        return self
        
    # Messaging
    def to_kafka(self, topic: str, **kwargs) -> 'Pipeline':
        """Send to Kafka"""
        params = f"topic={topic}" + "".join(f"&{k}={v}" for k, v in kwargs.items())
        self._flow = self._flow | f"kafka://produce?{params}"
        return self
        
    def from_kafka(self, topic: str, group: str = "default") -> 'Pipeline':
        """Consume from Kafka"""
        self._flow = flow(f"kafka://consume?topic={topic}&group={group}")
        return self
        
    # Database
    def to_postgres(self, table: str, **kwargs) -> 'Pipeline':
        """Insert to PostgreSQL"""
        params = f"table={table}" + "".join(f"&{k}={v}" for k, v in kwargs.items())
        self._flow = self._flow | f"postgres://insert?{params}"
        return self
        
    def from_postgres(self, sql: str) -> 'Pipeline':
        """Query PostgreSQL"""
        self._flow = flow(f"postgres://query?sql={sql}")
        return self
        
    # Communication
    def send_email(self, to: str, subject: str, **kwargs) -> 'Pipeline':
        """Send email"""
        params = f"to={to}&subject={subject}" + "".join(f"&{k}={v}" for k, v in kwargs.items())
        self._flow = self._flow | f"email://send?{params}"
        return self
        
    def send_slack(self, channel: str, token: str) -> 'Pipeline':
        """Send to Slack"""
        self._flow = self._flow | f"slack://send?channel={channel}&token={token}"
        return self
        
    # Execution
    def run(self, data: Any = None) -> Any:
        """Execute the pipeline"""
        if self._flow is None:
            raise ValueError("Pipeline is empty")
        if data is None and self._data is not None:
            data = self._data
        return self._flow.run(data)
        
    def stream(self):
        """Execute as stream"""
        if self._flow is None:
            raise ValueError("Pipeline is empty")
        return self._flow.stream()


# ============================================================================
# 2. CONTEXT MANAGER - With Statement Style
# ============================================================================

class pipeline:
    """
    Context manager for pipelines
    
    Example:
        with pipeline() as p:
            data = p.read("input.json")
            data = p.transform(data, "json")
            p.save(data, "output.json")
    """
    
    def __init__(self):
        self.data = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
        
    def read(self, path: str) -> Any:
        """Read file"""
        return flow(f"file://read?path={path}").run()
        
    def http_get(self, url: str) -> Any:
        """HTTP GET"""
        return flow(url).run()
        
    def transform(self, data: Any, transform_type: str, **kwargs) -> Any:
        """Transform data"""
        params = "&".join(f"{k}={v}" for k, v in kwargs.items())
        uri = f"transform://{transform_type}"
        if params:
            uri += f"?{params}"
        return flow(uri).run(data)
        
    def save(self, data: Any, path: str) -> Dict:
        """Save to file"""
        return flow(f"file://write?path={path}").run(data)


# ============================================================================
# 3. FUNCTION COMPOSITION - Functional Style
# ============================================================================

def compose(*functions):
    """
    Compose functions into a pipeline
    
    Example:
        process = compose(
            read_file("input.json"),
            to_json,
            filter_adults,
            to_csv,
            save_file("output.csv")
        )
        result = process()
    """
    def composed(*args, **kwargs):
        result = args[0] if args else None
        for func in functions:
            result = func(result) if result is not None else func()
        return result
    return composed


def read_file(path: str):
    """Function: Read file"""
    def _read(data=None):
        return flow(f"file://read?path={path}").run()
    return _read


def save_file(path: str):
    """Function: Save file"""
    def _save(data):
        return flow(f"file://write?path={path}").run(data)
    return _save


def to_json(data):
    """Function: Convert to JSON"""
    return flow("transform://json").run(data)


def to_csv(data):
    """Function: Convert to CSV"""
    return flow("transform://csv").run(data)


def http_get(url: str):
    """Function: HTTP GET"""
    def _get(data=None):
        return flow(url).run()
    return _get


# ============================================================================
# 4. SHORTCUTS - Quick Operations
# ============================================================================

def configure(**kwargs):
    """
    Set configuration values
    
    Example:
        configure(SQ_MODEL="llama3", SQ_DEBUG="true")
    """
    from .config import config
    for key, value in kwargs.items():
        config.set(key, str(value))


def quick(source: str) -> 'QuickPipeline':
    """
    Quick pipeline builder
    
    Example:
        quick("http://api.example.com/data").json().save("data.json")
    """
    return QuickPipeline(source)


class QuickPipeline:
    """Quick operations builder"""
    
    def __init__(self, source: str):
        self._flow = flow(source)
        
    def json(self):
        self._flow = self._flow | "transform://json"
        return self
        
    def csv(self):
        self._flow = self._flow | "transform://csv"
        return self
        
    def save(self, path: str):
        self._flow = self._flow | f"file://write?path={path}"
        return self._flow.run()


# ============================================================================
# 5. BUILDER PATTERN - Named Methods
# ============================================================================

class PipelineBuilder:
    """
    Builder pattern for complex pipelines
    
    Example:
        builder = PipelineBuilder()
        result = (
            builder
            .source_http("https://api.example.com/data")
            .transform_json()
            .filter_by(lambda x: x['active'])
            .transform_csv()
            .sink_file("output.csv")
            .execute()
        )
    """
    
    def __init__(self):
        self._steps = []
        self._data = None
        
    def source_http(self, url: str):
        """HTTP source"""
        self._steps.append(url)
        return self
        
    def source_file(self, path: str):
        """File source"""
        self._steps.append(f"file://read?path={path}")
        return self
        
    def source_kafka(self, topic: str, group: str = "default"):
        """Kafka source"""
        self._steps.append(f"kafka://consume?topic={topic}&group={group}")
        return self
        
    def transform_json(self):
        """JSON transformation"""
        self._steps.append("transform://json")
        return self
        
    def transform_csv(self):
        """CSV transformation"""
        self._steps.append("transform://csv")
        return self
        
    def transform_base64(self, decode: bool = False):
        """Base64 transformation"""
        uri = "transform://base64"
        if decode:
            uri += "?decode=true"
        self._steps.append(uri)
        return self
        
    def filter_by(self, predicate: Callable):
        """Filter data"""
        # Implementation similar to Pipeline.filter
        return self
        
    def sink_file(self, path: str):
        """File sink"""
        self._steps.append(f"file://write?path={path}")
        return self
        
    def sink_kafka(self, topic: str):
        """Kafka sink"""
        self._steps.append(f"kafka://produce?topic={topic}")
        return self
        
    def execute(self, data: Any = None):
        """Build and execute pipeline"""
        if not self._steps:
            raise ValueError("Pipeline has no steps")
            
        pipeline = flow(self._steps[0])
        for step in self._steps[1:]:
            pipeline = pipeline | step
            
        return pipeline.run(data or self._data)
        
    def with_data(self, data: Any):
        """Set initial data"""
        self._data = data
        return self


# ============================================================================
# 6. DECORATORS - Function Wrapping
# ============================================================================

def pipeline_step(uri: str):
    """
    Decorator to create pipeline steps from functions
    
    Example:
        @pipeline_step("transform://json")
        def process_json(data):
            # Custom processing
            return modified_data
    """
    def decorator(func):
        def wrapper(data):
            # Run through component first
            result = flow(uri).run(data)
            # Then apply function
            return func(result)
        return wrapper
    return decorator


def as_component(name: str):
    """
    Decorator to register function as component
    
    Example:
        @as_component("custom_transform")
        def my_transform(data):
            return data.upper()
            
        # Use: flow("custom_transform://")
    """
    def decorator(func):
        @register(name)
        class FunctionComponent(Component):
            def process(self, data):
                return func(data)
        return func
    return decorator


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Classes
    'Pipeline',
    'pipeline',
    'QuickPipeline',
    'PipelineBuilder',
    
    # Functions
    'configure',
    'compose',
    'quick',
    'read_file',
    'save_file',
    'to_json',
    'to_csv',
    'http_get',
    
    # Decorators
    'pipeline_step',
    'as_component',
]
