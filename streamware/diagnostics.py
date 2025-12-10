"""
Diagnostics and monitoring for Streamware with Camel-style logging
"""

import logging
import time
import json
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from datetime import datetime
from collections import defaultdict
import threading
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table


# Rich console for pretty output
console = Console()


class CamelFormatter(logging.Formatter):
    """Camel-style log formatter"""
    
    def format(self, record):
        # Add Camel-style prefixes
        if hasattr(record, 'component'):
            record.msg = f"[{record.component}] {record.msg}"
        if hasattr(record, 'exchange_id'):
            record.msg = f"Exchange[{record.exchange_id}] {record.msg}"
        if hasattr(record, 'route'):
            record.msg = f"Route[{record.route}] {record.msg}"
        return super().format(record)


class StreamwareLogger:
    """Enhanced logger with Camel-style features"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.exchange_id = None
        self.route_name = None
        self.component_name = None
        
    def _add_context(self, record):
        """Add Camel context to log record"""
        if self.exchange_id:
            record.exchange_id = self.exchange_id
        if self.route_name:
            record.route = self.route_name
        if self.component_name:
            record.component = self.component_name
            
    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
        
    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
        
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
        
    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
        
    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)
        
    def exchange_start(self, exchange_id: str):
        """Log exchange start (Camel-style)"""
        self.exchange_id = exchange_id
        self.info(f">>> Exchange Started: {exchange_id}")
        
    def exchange_end(self, exchange_id: str):
        """Log exchange end (Camel-style)"""
        self.info(f"<<< Exchange Completed: {exchange_id}")
        self.exchange_id = None
        
    def route_start(self, route_name: str):
        """Log route start"""
        self.route_name = route_name
        self.info(f"→ Route Started: {route_name}")
        
    def route_end(self, route_name: str):
        """Log route end"""
        self.info(f"← Route Completed: {route_name}")
        self.route_name = None
        
    def component_process(self, component_name: str, data: Any = None):
        """Log component processing"""
        self.component_name = component_name
        self.debug(f"⚙ Processing in {component_name}")
        if data is not None:
            self.debug(f"  Data: {str(data)[:200]}")


# Logger cache
_loggers: Dict[str, StreamwareLogger] = {}


def get_logger(name: str) -> StreamwareLogger:
    """Get or create a logger instance"""
    if name not in _loggers:
        _loggers[name] = StreamwareLogger(name)
    return _loggers[name]


def enable_diagnostics(
    level: str = "INFO",
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    use_rich: bool = True,
    camel_style: bool = True
):
    """Enable diagnostics with specified configuration"""
    
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if use_rich:
        # Use Rich for pretty console output
        handler = RichHandler(
            console=console,
            show_time=True,
            show_path=False
        )
    else:
        handler = logging.StreamHandler()
        
    if camel_style:
        formatter = CamelFormatter(format)
    else:
        formatter = logging.Formatter(format)
        
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)
    
    # Configure Streamware logger
    streamware_logger = logging.getLogger('streamware')
    streamware_logger.setLevel(log_level)
    
    console.print(f"[green]✓ Diagnostics enabled (level: {level})[/green]")


class Metrics:
    """Metrics collection for pipeline monitoring"""
    
    def __init__(self):
        self._metrics = defaultdict(lambda: {
            'processed': 0,
            'errors': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'last_update': None
        })
        self._lock = threading.Lock()
        
    @contextmanager
    def track(self, name: str):
        """Context manager to track metrics for a named operation"""
        start_time = time.time()
        error = False
        
        try:
            yield
        except Exception as e:
            error = True
            raise e
        finally:
            elapsed = time.time() - start_time
            
            with self._lock:
                metric = self._metrics[name]
                metric['processed'] += 1
                if error:
                    metric['errors'] += 1
                metric['total_time'] += elapsed
                metric['min_time'] = min(metric['min_time'], elapsed)
                metric['max_time'] = max(metric['max_time'], elapsed)
                metric['last_update'] = datetime.now()
                
    def record(self, name: str, value: float):
        """Record a custom metric value"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []
            self._metrics[name].append(value)
            
    def get_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for a named metric"""
        with self._lock:
            if name not in self._metrics:
                return {}
                
            metric = self._metrics[name]
            if isinstance(metric, dict):
                stats = metric.copy()
                if stats['processed'] > 0:
                    stats['avg_time'] = stats['total_time'] / stats['processed']
                return stats
            else:
                # For custom metrics (list of values)
                values = metric
                if not values:
                    return {}
                return {
                    'count': len(values),
                    'mean': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'sum': sum(values)
                }
                
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all collected statistics"""
        with self._lock:
            all_stats = {}
            for name in self._metrics:
                all_stats[name] = self.get_stats(name)
            return all_stats
            
    def print_summary(self):
        """Print a summary table of all metrics"""
        table = Table(title="Pipeline Metrics Summary")
        table.add_column("Pipeline", style="cyan")
        table.add_column("Processed", style="green")
        table.add_column("Errors", style="red")
        table.add_column("Avg Time (s)", style="yellow")
        table.add_column("Min/Max (s)", style="blue")
        
        stats = self.get_all_stats()
        for name, metric in stats.items():
            if 'processed' in metric:
                table.add_row(
                    name,
                    str(metric.get('processed', 0)),
                    str(metric.get('errors', 0)),
                    f"{metric.get('avg_time', 0):.3f}",
                    f"{metric.get('min_time', 0):.3f}/{metric.get('max_time', 0):.3f}"
                )
                
        console.print(table)
        
    def reset(self, name: Optional[str] = None):
        """Reset metrics for a specific name or all metrics"""
        with self._lock:
            if name:
                if name in self._metrics:
                    del self._metrics[name]
            else:
                self._metrics.clear()
                
    def export_json(self) -> str:
        """Export metrics as JSON"""
        stats = self.get_all_stats()
        # Convert datetime objects to strings
        for name, metric in stats.items():
            if 'last_update' in metric and metric['last_update']:
                metric['last_update'] = metric['last_update'].isoformat()
        return json.dumps(stats, indent=2)


# Global metrics instance
metrics = Metrics()


class DiagnosticsContext:
    """Context manager for diagnostic tracing"""
    
    def __init__(self, name: str, logger: Optional[StreamwareLogger] = None):
        self.name = name
        self.logger = logger or get_logger('streamware')
        self.start_time = None
        self.exchange_id = f"EX-{int(time.time() * 1000)}"
        
    def __enter__(self):
        self.start_time = time.time()
        self.logger.exchange_start(self.exchange_id)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = time.time() - self.start_time
        if exc_type:
            self.logger.error(f"Exchange failed: {exc_val}")
        self.logger.exchange_end(self.exchange_id)
        self.logger.info(f"Exchange duration: {elapsed:.3f}s")
        
        # Record metrics
        with metrics.track(self.name):
            pass


class MessageTrace:
    """Camel-style message tracing"""
    
    def __init__(self):
        self.traces = []
        
    def add_trace(
        self,
        exchange_id: str,
        component: str,
        message: Any,
        headers: Optional[Dict] = None
    ):
        """Add a trace entry"""
        trace = {
            'timestamp': datetime.now().isoformat(),
            'exchange_id': exchange_id,
            'component': component,
            'message': str(message)[:1000],  # Limit message size
            'headers': headers or {}
        }
        self.traces.append(trace)
        
    def get_traces(self, exchange_id: Optional[str] = None) -> List[Dict]:
        """Get traces, optionally filtered by exchange ID"""
        if exchange_id:
            return [t for t in self.traces if t['exchange_id'] == exchange_id]
        return self.traces
        
    def clear(self):
        """Clear all traces"""
        self.traces.clear()
        
    def export_json(self) -> str:
        """Export traces as JSON"""
        return json.dumps(self.traces, indent=2)


# Global message tracer
message_trace = MessageTrace()


def trace_message(
    exchange_id: str,
    component: str,
    message: Any,
    headers: Optional[Dict] = None
):
    """Convenience function to trace a message"""
    message_trace.add_trace(exchange_id, component, message, headers)


def print_active_configuration():
    """Print the currently active Streamware configuration"""
    from .config import config
    
    # Reload to ensure we have latest from env
    config.reload()
    
    provider = config.get("SQ_LLM_PROVIDER", "Not set (defaults to openai)")
    model = config.get("SQ_MODEL", "Not set")
    ollama_url = config.get("SQ_OLLAMA_URL", "http://localhost:11434")
    
    console.print("\n[bold cyan]🔧 Streamware Active Configuration[/bold cyan]")
    console.print("=" * 40)
    
    table = Table(show_header=False, box=None)
    table.add_column("Key", style="yellow")
    table.add_column("Value", style="green")
    
    table.add_row("LLM Provider", provider)
    table.add_row("Model", model)
    
    if provider == "ollama":
        table.add_row("Ollama URL", ollama_url)
        
    # Check keys presence (without showing them)
    import os
    keys = {
        "OPENAI_API_KEY": "OpenAI",
        "ANTHROPIC_API_KEY": "Anthropic",
        "GROQ_API_KEY": "Groq",
        "GEMINI_API_KEY": "Gemini"
    }
    
    found_keys = []
    for env_var, name in keys.items():
        if os.environ.get(env_var) or config.get(f"SQ_{env_var}"):
            found_keys.append(name)
            
    if found_keys:
        table.add_row("Detected Keys", ", ".join(found_keys))
    else:
        table.add_row("Detected Keys", "[red]None[/red]")
        
    console.print(table)
    console.print("\nTo change settings run: [bold]streamware setup[/bold]")
    console.print("=" * 40)

