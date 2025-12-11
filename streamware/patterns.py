"""
Advanced workflow patterns for Streamware (split, join, multicast, choose, etc.)
"""

import asyncio
from typing import Any, List, Callable, Optional, Iterator, Union, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import re
from .core import Flow, Component, StreamComponent, registry, register
from .uri import StreamwareURI
from .diagnostics import get_logger

logger = get_logger(__name__)


class SplitPattern:
    """Split data into multiple parts for parallel processing"""
    
    def __init__(self, pattern: Optional[str] = None):
        """
        Initialize split pattern
        
        Args:
            pattern: Split pattern (e.g., "$.items[*]" for JSONPath, None for auto-detect)
        """
        self.pattern = pattern
        
    def split(self, data: Any) -> List[Any]:
        """Split data according to pattern"""
        if self.pattern is None:
            # Auto-detect: split lists/arrays
            if isinstance(data, (list, tuple)):
                return list(data)
            elif isinstance(data, dict):
                return list(data.values())
            elif isinstance(data, str):
                # Split by newlines for strings
                return data.strip().split('\n')
            else:
                return [data]
                
        elif self.pattern.startswith('$'):
            # JSONPath pattern
            from jsonpath_ng import parse
            expr = parse(self.pattern)
            matches = expr.find(data)
            return [match.value for match in matches]
            
        elif self.pattern.startswith('xpath:'):
            # XPath pattern (for XML)
            raise NotImplementedError("XPath splitting not yet implemented")
            
        elif self.pattern == 'lines':
            # Split text by lines
            if isinstance(data, str):
                return data.strip().split('\n')
            return [data]
            
        elif self.pattern == 'csv':
            # Split CSV rows
            import csv
            import io
            if isinstance(data, str):
                reader = csv.reader(io.StringIO(data))
                return list(reader)
            return [data]
            
        else:
            # Regex pattern
            if isinstance(data, str):
                return re.split(self.pattern, data)
            return [data]
            
    def __call__(self, flow: Flow) -> 'SplitFlow':
        """Apply split to a flow"""
        return SplitFlow(flow, self)


class JoinPattern:
    """Join split data back together"""
    
    def __init__(self, strategy: str = "list"):
        """
        Initialize join pattern
        
        Args:
            strategy: Join strategy ("list", "merge", "concat", "sum", "first", "last")
        """
        self.strategy = strategy
        
    def join(self, parts: List[Any]) -> Any:
        """Join parts according to strategy"""
        if not parts:
            return None
            
        if self.strategy == "list":
            # Return as list
            return parts
            
        elif self.strategy == "merge":
            # Merge dictionaries
            if all(isinstance(p, dict) for p in parts):
                result = {}
                for part in parts:
                    result.update(part)
                return result
            return parts
            
        elif self.strategy == "concat":
            # Concatenate strings or lists
            if all(isinstance(p, str) for p in parts):
                return ''.join(parts)
            elif all(isinstance(p, list) for p in parts):
                result = []
                for part in parts:
                    result.extend(part)
                return result
            return parts
            
        elif self.strategy == "sum":
            # Sum numeric values
            if all(isinstance(p, (int, float)) for p in parts):
                return sum(parts)
            return parts
            
        elif self.strategy == "first":
            # Return first non-null result
            for part in parts:
                if part is not None:
                    return part
            return None
            
        elif self.strategy == "last":
            # Return last non-null result
            for part in reversed(parts):
                if part is not None:
                    return part
            return None
            
        else:
            return parts


class MulticastPattern:
    """Send data to multiple destinations"""
    
    def __init__(self, destinations: List[Union[str, Flow]], parallel: bool = True):
        """
        Initialize multicast pattern
        
        Args:
            destinations: List of destination URIs or flows
            parallel: Process destinations in parallel (True) or sequential (False)
        """
        self.destinations = destinations
        self.parallel = parallel
        
    def multicast(self, data: Any) -> List[Any]:
        """Send data to all destinations"""
        results = []
        
        if self.parallel:
            # Parallel processing
            with ThreadPoolExecutor() as executor:
                futures = []
                for dest in self.destinations:
                    if isinstance(dest, str):
                        flow = Flow(dest)
                    else:
                        flow = dest
                    futures.append(executor.submit(flow.run, data))
                    
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Multicast destination failed: {e}")
                        results.append(None)
        else:
            # Sequential processing
            for dest in self.destinations:
                try:
                    if isinstance(dest, str):
                        flow = Flow(dest)
                    else:
                        flow = dest
                    result = flow.run(data)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Multicast destination failed: {e}")
                    results.append(None)
                    
        return results


class ChoicePattern:
    """Conditional routing based on predicates"""
    
    def __init__(self):
        """Initialize choice pattern"""
        self.conditions = []
        self.otherwise_flow = None
        
    def when(self, predicate: Union[str, Callable], destination: Union[str, Flow]) -> 'ChoicePattern':
        """Add a conditional route"""
        self.conditions.append((predicate, destination))
        return self
        
    def otherwise(self, destination: Union[str, Flow]) -> 'ChoicePattern':
        """Set default route when no conditions match"""
        self.otherwise_flow = destination
        return self
        
    def route(self, data: Any) -> Any:
        """Route data based on conditions"""
        for predicate, destination in self.conditions:
            if self._evaluate_predicate(predicate, data):
                if isinstance(destination, str):
                    flow = Flow(destination)
                else:
                    flow = destination
                return flow.run(data)
                
        # No conditions matched, use otherwise
        if self.otherwise_flow:
            if isinstance(self.otherwise_flow, str):
                flow = Flow(self.otherwise_flow)
            else:
                flow = self.otherwise_flow
            return flow.run(data)
            
        # No otherwise specified, return data unchanged
        return data
        
    def _evaluate_predicate(self, predicate: Union[str, Callable], data: Any) -> bool:
        """Evaluate a predicate against data"""
        if callable(predicate):
            # Function predicate
            return predicate(data)
            
        elif isinstance(predicate, str):
            if predicate.startswith('$'):
                # JSONPath expression
                from jsonpath_ng import parse
                expr = parse(predicate)
                matches = expr.find(data)
                return bool(matches)
                
            elif '==' in predicate or '!=' in predicate or '>' in predicate or '<' in predicate:
                # Simple expression (e.g., "$.status == 'active'")
                # This is a simplified implementation
                try:
                    # Extract the JSONPath and value
                    parts = re.split(r'(==|!=|>|<|>=|<=)', predicate)
                    if len(parts) == 3:
                        path, operator, value = parts
                        path = path.strip()
                        value = value.strip().strip('"\'')
                        
                        # Get the actual value from data
                        if path.startswith('$'):
                            from jsonpath_ng import parse
                            expr = parse(path)
                            matches = expr.find(data)
                            if matches:
                                actual_value = matches[0].value
                                
                                # Compare
                                if operator == '==':
                                    return str(actual_value) == value
                                elif operator == '!=':
                                    return str(actual_value) != value
                                elif operator == '>':
                                    return float(actual_value) > float(value)
                                elif operator == '<':
                                    return float(actual_value) < float(value)
                                elif operator == '>=':
                                    return float(actual_value) >= float(value)
                                elif operator == '<=':
                                    return float(actual_value) <= float(value)
                except (ValueError, TypeError, KeyError):
                    pass
                    
            # Treat as boolean
            return bool(predicate)
            
        return False


class AggregatePattern:
    """Aggregate data over a window"""
    
    def __init__(self, function: str = "list", window: Optional[int] = None):
        """
        Initialize aggregate pattern
        
        Args:
            function: Aggregation function ("list", "sum", "avg", "min", "max", "count")
            window: Window size (number of items to aggregate)
        """
        self.function = function
        self.window = window
        self.buffer = []
        
    def aggregate(self, item: Any) -> Optional[Any]:
        """Add item to aggregation and return result if window is complete"""
        self.buffer.append(item)
        
        if self.window and len(self.buffer) >= self.window:
            result = self._compute_aggregate()
            self.buffer.clear()
            return result
        elif not self.window:
            # No window, aggregate everything
            return self._compute_aggregate()
            
        return None
        
    def _compute_aggregate(self) -> Any:
        """Compute aggregate from buffer"""
        if not self.buffer:
            return None
            
        if self.function == "list":
            return self.buffer.copy()
            
        elif self.function == "sum":
            if all(isinstance(x, (int, float)) for x in self.buffer):
                return sum(self.buffer)
            return self.buffer
            
        elif self.function == "avg":
            if all(isinstance(x, (int, float)) for x in self.buffer):
                return sum(self.buffer) / len(self.buffer)
            return self.buffer
            
        elif self.function == "min":
            return min(self.buffer)
            
        elif self.function == "max":
            return max(self.buffer)
            
        elif self.function == "count":
            return len(self.buffer)
            
        else:
            return self.buffer
            
    def flush(self) -> Optional[Any]:
        """Flush remaining buffer"""
        if self.buffer:
            result = self._compute_aggregate()
            self.buffer.clear()
            return result
        return None


class FilterPattern:
    """Filter data based on conditions"""
    
    def __init__(self, predicate: Union[str, Callable]):
        """
        Initialize filter pattern
        
        Args:
            predicate: Filter condition (string expression or callable)
        """
        self.predicate = predicate
        
    def filter(self, data: Any) -> Optional[Any]:
        """Filter data based on predicate"""
        # Use same predicate evaluation as ChoicePattern
        choice = ChoicePattern()
        if choice._evaluate_predicate(self.predicate, data):
            return data
        return None
        
    def filter_stream(self, stream: Iterator) -> Iterator:
        """Filter a stream of data"""
        for item in stream:
            filtered = self.filter(item)
            if filtered is not None:
                yield filtered


# Component implementations for patterns

@register("split")
class SplitComponent(StreamComponent):
    """Component for splitting data"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        pattern = self.uri.get_param('pattern')
        splitter = SplitPattern(pattern)
        
        if input_stream:
            for data in input_stream:
                parts = splitter.split(data)
                for part in parts:
                    yield part
        else:
            # No input stream, process once
            parts = splitter.split(None)
            for part in parts:
                yield part


@register("join")
class JoinComponent(Component):
    """Component for joining split data"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def process(self, data: Any) -> Any:
        strategy = self.uri.get_param('strategy', 'list')
        joiner = JoinPattern(strategy)
        
        if isinstance(data, list):
            return joiner.join(data)
        return data


@register("multicast")
class MulticastComponent(Component):
    """Component for multicasting to multiple destinations"""
    
    def process(self, data: Any) -> Any:
        destinations = self.uri.get_param('destinations', [])
        parallel = self.uri.get_param('parallel', True)
        
        if not destinations:
            logger.warning("No multicast destinations specified")
            return data
            
        multicaster = MulticastPattern(destinations, parallel)
        return multicaster.multicast(data)


@register("choose")
class ChooseComponent(Component):
    """Component for conditional routing"""
    
    def process(self, data: Any) -> Any:
        # This component requires configuration through the URI params
        # Example: choose://route?when=$.status==active&then=kafka://active&otherwise=file://inactive
        
        choice = ChoicePattern()
        
        # Parse when conditions
        when_conditions = []
        for key, value in self.uri.params.items():
            if key.startswith('when'):
                # Extract condition number if present (when1, when2, etc.)
                condition = value
                then_key = key.replace('when', 'then')
                if then_key in self.uri.params:
                    destination = self.uri.params[then_key]
                    choice.when(condition, destination)
                    
        # Set otherwise
        if 'otherwise' in self.uri.params:
            choice.otherwise(self.uri.params['otherwise'])
            
        return choice.route(data)


@register("aggregate")
class AggregateComponent(StreamComponent):
    """Component for aggregating data"""
    
    input_mime = "application/json"
    output_mime = "application/json"
    
    def __init__(self, uri: StreamwareURI):
        super().__init__(uri)
        function = self.uri.get_param('function', 'list')
        window = self.uri.get_param('window')
        self.aggregator = AggregatePattern(function, window)
        
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        if input_stream:
            for item in input_stream:
                result = self.aggregator.aggregate(item)
                if result is not None:
                    yield result
                    
            # Flush remaining
            final = self.aggregator.flush()
            if final is not None:
                yield final


@register("filter")
class FilterComponent(StreamComponent):
    """Component for filtering data"""
    
    def stream(self, input_stream: Optional[Iterator]) -> Iterator:
        predicate = self.uri.get_param('predicate')
        if not predicate:
            # Try other common param names
            predicate = self.uri.get_param('condition') or self.uri.get_param('where')
            
        if not predicate:
            logger.warning("No filter predicate specified")
            if input_stream:
                yield from input_stream
            return
            
        filter_pattern = FilterPattern(predicate)
        
        if input_stream:
            yield from filter_pattern.filter_stream(input_stream)


# Convenience functions for patterns

def split(pattern: Optional[str] = None) -> SplitPattern:
    """Create a split pattern"""
    return SplitPattern(pattern)


def join(strategy: str = "list") -> JoinPattern:
    """Create a join pattern"""
    return JoinPattern(strategy)


def multicast(destinations: List[Union[str, Flow]], parallel: bool = True) -> MulticastPattern:
    """Create a multicast pattern"""
    return MulticastPattern(destinations, parallel)


def choose() -> ChoicePattern:
    """Create a choice pattern"""
    return ChoicePattern()


def aggregate(function: str = "list", window: Optional[int] = None) -> AggregatePattern:
    """Create an aggregate pattern"""
    return AggregatePattern(function, window)


def filter_stream(predicate: Union[str, Callable]) -> FilterPattern:
    """Create a filter pattern"""
    return FilterPattern(predicate)


class SplitFlow(Flow):
    """Special flow for split operations with automatic join"""
    
    def __init__(self, parent_flow: Flow, splitter: SplitPattern):
        super().__init__(parent_flow.steps[0])
        self.steps = parent_flow.steps
        self.splitter = splitter
        self.join_strategy = "list"
        
    def join_with(self, strategy: str = "list") -> 'SplitFlow':
        """Set join strategy for collecting results"""
        self.join_strategy = strategy
        return self
        
    def run(self, data: Any = None) -> Any:
        """Run split flow with automatic join"""
        # Run up to split point
        result = super().run(data)
        
        # Split data
        parts = self.splitter.split(result)
        
        # Process each part through remaining pipeline
        processed_parts = []
        for part in parts:
            # Create sub-flow for processing
            sub_flow = Flow(self.steps[0])
            sub_flow.steps = self.steps[1:] if len(self.steps) > 1 else []
            processed = sub_flow.run(part) if sub_flow.steps else part
            processed_parts.append(processed)
            
        # Join results
        joiner = JoinPattern(self.join_strategy)
        return joiner.join(processed_parts)
