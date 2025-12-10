"""
Streamware - Modern Python stream processing framework inspired by Apache Camel

OPTIMIZED: Uses lazy imports for fast CLI startup (~0.1s instead of ~3s)
Import heavy modules only when accessed.
"""

__version__ = "0.2.1"
__author__ = "Softreck"
__license__ = "Apache-2.0"

# Lazy import system - modules loaded only when accessed
def __getattr__(name):
    """Lazy import handler - imports modules only when accessed."""
    
    # Core
    if name in ("flow", "Flow", "Component", "StreamComponent", "register", "Registry"):
        from . import core
        return getattr(core, name)
    
    # Patterns
    if name in ("split", "join", "multicast", "choose", "aggregate", "filter_stream"):
        from . import patterns
        return getattr(patterns, name)
    
    # Diagnostics
    if name in ("enable_diagnostics", "get_logger", "metrics", "DiagnosticsContext"):
        from . import diagnostics
        return getattr(diagnostics, name)
    
    # URI/MIME
    if name == "StreamwareURI":
        from .uri import StreamwareURI
        return StreamwareURI
    if name == "MimeValidator":
        from .mime import MimeValidator
        return MimeValidator
    
    # Exceptions
    if name in ("StreamwareError", "ComponentError", "MimeTypeError", "RoutingError"):
        from . import exceptions
        return getattr(exceptions, name)
    
    # DSL
    if name in ("Pipeline", "pipeline", "PipelineBuilder", "quick", "compose", "as_component", "pipeline_step"):
        from . import dsl
        return getattr(dsl, name)
    
    # Components - loaded on demand
    if name == "components":
        from . import components
        return components
    
    raise AttributeError(f"module 'streamware' has no attribute '{name}'")

__all__ = [
    # Core
    "flow",
    "Flow",
    "Component",
    "StreamComponent",
    "register",
    "Registry",
    
    # Patterns
    "split",
    "join",
    "multicast",
    "choose",
    "aggregate",
    "filter_stream",
    
    # Simplified DSL
    "Pipeline",
    "pipeline",
    "PipelineBuilder",
    "quick",
    "compose",
    "as_component",
    "pipeline_step",
    
    # Diagnostics
    "enable_diagnostics",
    "get_logger",
    "metrics",
    
    # Types
    "StreamwareURI",
    "MimeValidator",
    
    # Exceptions
    "StreamwareError",
    "ComponentError",
    "MimeTypeError",
    "RoutingError",
]
