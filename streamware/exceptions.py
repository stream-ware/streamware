"""
Custom exceptions for Streamware
"""


class StreamwareError(Exception):
    """Base exception for all Streamware errors"""
    pass


class ComponentError(StreamwareError):
    """Error in component processing"""
    pass


class MimeTypeError(StreamwareError):
    """MIME type validation error"""
    pass


class RoutingError(StreamwareError):
    """Error in routing/flow execution"""
    pass


class ConfigurationError(StreamwareError):
    """Configuration error"""
    pass


class ConnectionError(StreamwareError):
    """Connection error for external services"""
    pass


class TimeoutError(StreamwareError):
    """Operation timeout"""
    pass


class AuthenticationError(StreamwareError):
    """Authentication/authorization error"""
    pass


class ValidationError(StreamwareError):
    """Data validation error"""
    pass


class ParseError(StreamwareError):
    """Parsing error"""
    pass
