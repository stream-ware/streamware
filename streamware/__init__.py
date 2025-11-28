"""
Streamware - Modern Python stream processing framework inspired by Apache Camel
"""

__version__ = "0.1.0"
__author__ = "Softreck"
__license__ = "Apache-2.0"

from .core import (
    flow,
    Flow,
    Component,
    StreamComponent,
    register,
    Registry,
)

from .patterns import (
    split,
    join,
    multicast,
    choose,
    aggregate,
    filter_stream,
)

from .diagnostics import (
    enable_diagnostics,
    get_logger,
    metrics,
    DiagnosticsContext,
)

from .uri import StreamwareURI
from .mime import MimeValidator
from .exceptions import (
    StreamwareError,
    ComponentError,
    MimeTypeError,
    RoutingError,
)

# Simplified DSL imports
from .dsl import (
    Pipeline,
    pipeline,
    PipelineBuilder,
    quick,
    compose,
    as_component,
    pipeline_step,
)

# Convenience imports
from .components import *

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
