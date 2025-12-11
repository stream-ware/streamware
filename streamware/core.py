"""
Core flow and component system for Streamware
"""

__all__ = [
    "Component",
    "Flow", 
    "StreamwareURI",
    "flow",
    "register",
]

import asyncio
from typing import Any, Iterator, Optional, Union, List, Dict, Type
from abc import ABC, abstractmethod
import inspect
from .uri import StreamwareURI
from .mime import MimeValidator
from .diagnostics import get_logger
from .exceptions import ComponentError, MimeTypeError

logger = get_logger(__name__)


class Component(ABC):
    """Base component class for all Streamware components"""
    
    input_mime: Optional[str] = None
    output_mime: Optional[str] = None
    
    def __init__(self, uri: StreamwareURI):
        self.uri = uri
        self.params = uri.params
        
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data synchronously"""
        raise NotImplementedError
        
    async def process_async(self, data: Any) -> Any:
        """Process data asynchronously (default delegates to sync)"""
        return self.process(data)
        
    def validate_mime(self, input_data: Any) -> None:
        """Validate input MIME type"""
        if self.input_mime:
            MimeValidator.validate(input_data, self.input_mime)


class StreamComponent(Component):
    """Streaming component that processes data as a stream"""
    
    def process(self, data: Any) -> Any:
        """Process entire data (collects stream)"""
        result = []
        for item in self.stream(data):
            result.append(item)
        return result
        
    @abstractmethod
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        """Process data as a stream"""
        raise NotImplementedError
        
    async def stream_async(self, input_stream: Optional[Iterator]) -> Iterator:
        """Process data as an async stream"""
        async for item in input_stream:
            yield await self.process_async(item)


class Registry:
    """Component registry for managing all components"""
    
    _instance = None
    _components: Dict[str, Type[Component]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    @classmethod
    def register(cls, scheme: str, component_class: Type[Component]) -> None:
        """Register a component with a scheme"""
        cls._components[scheme] = component_class
        logger.debug(f"Registered component: {scheme} -> {component_class.__name__}")
        
    @classmethod
    def resolve(cls, uri: Union[str, StreamwareURI]) -> Component:
        """Resolve URI to component instance"""
        if isinstance(uri, str):
            uri = StreamwareURI(uri)
            
        component_class = cls._components.get(uri.scheme)
        if not component_class:
            raise ComponentError(f"No component registered for scheme: {uri.scheme}")
            
        return component_class(uri)
        
    @classmethod
    def list_components(cls) -> List[str]:
        """List all registered component schemes"""
        return list(cls._components.keys())


# Global registry instance
registry = Registry()


def register(scheme: str):
    """Decorator to register a component"""
    def decorator(cls):
        registry.register(scheme, cls)
        return cls
    return decorator


class Flow:
    """Flow builder for creating pipelines"""
    
    def __init__(self, uri: Union[str, StreamwareURI]):
        """Initialize flow with starting URI"""
        self.steps = [uri]
        self._data = None
        self._diagnostics = False
        self._trace = False
        
    def __or__(self, other: Union[str, StreamwareURI]) -> 'Flow':
        """Pipe operator for chaining components"""
        self.steps.append(other)
        return self
        
    def pipe(self, uri: Union[str, StreamwareURI]) -> 'Flow':
        """Alternative to | operator"""
        return self | uri
        
    def with_data(self, data: Any) -> 'Flow':
        """Set initial data for the flow"""
        self._data = data
        return self
        
    def with_diagnostics(self, trace: bool = False) -> 'Flow':
        """Enable diagnostics for this flow"""
        self._diagnostics = True
        self._trace = trace
        return self
        
    def _validate_pipeline(self) -> None:
        """Validate MIME types through the pipeline"""
        components = [registry.resolve(uri) for uri in self.steps]
        
        for i in range(len(components) - 1):
            current = components[i]
            next_comp = components[i + 1]
            
            if current.output_mime and next_comp.input_mime:
                if not MimeValidator.is_compatible(current.output_mime, next_comp.input_mime):
                    raise MimeTypeError(
                        f"Incompatible MIME types in pipeline: "
                        f"{current.__class__.__name__} outputs {current.output_mime}, "
                        f"but {next_comp.__class__.__name__} expects {next_comp.input_mime}"
                    )
                    
    def run(self, data: Any = None) -> Any:
        """Execute the flow synchronously"""
        if data is None:
            data = self._data
            
        self._validate_pipeline()
        
        for i, uri in enumerate(self.steps):
            component = registry.resolve(uri)
            
            if self._diagnostics:
                logger.info(f"Step {i+1}/{len(self.steps)}: {component.__class__.__name__}")
                if self._trace:
                    logger.debug(f"Input: {data}")
                    
            try:
                data = component.process(data)
                
                if self._trace:
                    logger.debug(f"Output: {data}")
                    
            except Exception as e:
                logger.error(f"Error in component {component.__class__.__name__}: {e}")
                # Chain error message to preserve original error info
                error_msg = f"Pipeline failed at step {i+1}: {str(e)}"
                raise ComponentError(error_msg) from e
                
        return data
        
    async def run_async(self, data: Any = None) -> Any:
        """Execute the flow asynchronously"""
        if data is None:
            data = self._data
            
        self._validate_pipeline()
        
        for i, uri in enumerate(self.steps):
            component = registry.resolve(uri)
            
            if self._diagnostics:
                logger.info(f"Step {i+1}/{len(self.steps)}: {component.__class__.__name__}")
                if self._trace:
                    logger.debug(f"Input: {data}")
                    
            try:
                if asyncio.iscoroutinefunction(component.process_async):
                    data = await component.process_async(data)
                else:
                    data = component.process(data)
                    
                if self._trace:
                    logger.debug(f"Output: {data}")
                    
            except Exception as e:
                logger.error(f"Error in component {component.__class__.__name__}: {e}")
                raise ComponentError(f"Pipeline failed at step {i+1}") from e
                
        return data
        
    def stream(self, data: Any = None) -> Iterator:
        """Execute the flow as a stream"""
        if data is None:
            data = self._data
            
        self._validate_pipeline()
        
        stream = data
        
        for i, uri in enumerate(self.steps):
            component = registry.resolve(uri)
            
            if self._diagnostics:
                logger.info(f"Stream step {i+1}/{len(self.steps)}: {component.__class__.__name__}")
                
            try:
                if isinstance(component, StreamComponent):
                    stream = component.stream(stream)
                else:
                    # Non-streaming component - process and yield
                    result = component.process(stream) if stream is not None else component.process(None)
                    stream = iter([result]) if not isinstance(result, Iterator) else result
                    
            except Exception as e:
                logger.error(f"Error in stream component {component.__class__.__name__}: {e}")
                raise ComponentError(f"Stream pipeline failed at step {i+1}") from e
                
        # Yield from final stream
        for item in stream:
            yield item
            
    async def stream_async(self, data: Any = None) -> Iterator:
        """Execute the flow as an async stream"""
        if data is None:
            data = self._data
            
        self._validate_pipeline()
        
        stream = data
        
        for i, uri in enumerate(self.steps):
            component = registry.resolve(uri)
            
            if self._diagnostics:
                logger.info(f"Async stream step {i+1}/{len(self.steps)}: {component.__class__.__name__}")
                
            try:
                if isinstance(component, StreamComponent):
                    if asyncio.iscoroutinefunction(component.stream_async):
                        stream = component.stream_async(stream)
                    else:
                        stream = component.stream(stream)
                else:
                    # Non-streaming component
                    if asyncio.iscoroutinefunction(component.process_async):
                        result = await component.process_async(stream) if stream is not None else await component.process_async(None)
                    else:
                        result = component.process(stream) if stream is not None else component.process(None)
                    stream = iter([result]) if not isinstance(result, Iterator) else result
                    
            except Exception as e:
                logger.error(f"Error in async stream component {component.__class__.__name__}: {e}")
                raise ComponentError(f"Async stream pipeline failed at step {i+1}") from e
                
        # Yield from final stream
        if hasattr(stream, '__aiter__'):
            async for item in stream:
                yield item
        else:
            for item in stream:
                yield item
                
    def run_forever(self) -> None:
        """Run the flow continuously (for consumers)"""
        logger.info("Starting continuous flow execution")
        
        try:
            while True:
                try:
                    self.run()
                except Exception as e:
                    logger.error(f"Error in continuous flow: {e}")
                    # Continue running despite errors
                    
        except KeyboardInterrupt:
            logger.info("Flow execution stopped by user")
            
    def schedule(self, cron: str) -> None:
        """Schedule the flow with cron expression"""
        # This would integrate with a scheduler like APScheduler
        raise NotImplementedError("Scheduling support coming soon")


def flow(uri: Union[str, StreamwareURI]) -> Flow:
    """Create a new flow starting with the given URI"""
    return Flow(uri)
