# shared/logging_config.py
import logging
import uuid
from contextvars import ContextVar
from typing import Optional
from opentelemetry import trace
import structlog

# Context variables for request tracking
request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id: ContextVar[Optional[str]] = ContextVar("user_id", default=None)

def get_trace_context() -> dict:
    """Get current trace context if available"""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        return {
            "trace_id": format(span_context.trace_id, "032x"),
            "span_id": format(span_context.span_id, "016x"),
        }
    return {}
  
def configure_logging(service_name: str):
    """
    Configure structured logging for the application
    """
    def add_trace_context(logger, method_name, event_dict):
        """Add trace context to log events if available"""
        trace_context = get_trace_context()
        if trace_context:
            event_dict.update(trace_context)
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_trace_context,  # Add trace context
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a logger instance with the given name"""
    return structlog.get_logger(name).bind(service=name)
