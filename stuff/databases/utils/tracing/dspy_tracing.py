import logging
from typing import Any, Dict, Optional

from dspy.utils.callback import BaseCallback  # Adjust the import path as necessary
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

logger = logging.getLogger(__name__)


class OpenTelemetryCallback(BaseCallback):
    """A custom callback handler that integrates DSPy with OpenTelemetry."""

    def __init__(self):
        self.tracer = trace.get_tracer(__name__)

    # Module Callbacks
    def on_module_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """Callback for when a module starts."""
        with self.tracer.start_as_current_span(
            f"module_start:{instance.__class__.__name__}", kind=trace.SpanKind.INTERNAL
        ) as span:
            span.set_attribute("call_id", call_id)
            span.set_attribute("module_name", instance.__class__.__name__)
            for key, value in inputs.items():
                span.set_attribute(f"input.{key}", str(value))

    def on_module_end(
        self,
        call_id: str,
        outputs: Optional[Any],
        exception: Optional[Exception] = None,
    ):
        """Callback for when a module ends."""
        current_span = trace.get_current_span()
        current_span.set_attribute("call_id", call_id)
        if exception:
            current_span.record_exception(exception)
            current_span.set_status(Status(StatusCode.ERROR, str(exception)))
        else:
            current_span.set_attribute("output", str(outputs))
            current_span.set_status(Status(StatusCode.OK))
        # Span will automatically end when exiting the context

    # LM Callbacks
    def on_lm_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """Callback for when a language model starts."""
        with self.tracer.start_as_current_span(
            f"lm_start:{instance.model_name}", kind=trace.SpanKind.INTERNAL
        ) as span:
            span.set_attribute("call_id", call_id)
            span.set_attribute("lm_name", instance.model_name)
            for key, value in inputs.items():
                span.set_attribute(f"input.{key}", str(value))

    def on_lm_end(
        self,
        call_id: str,
        outputs: Optional[Dict[str, Any]],
        exception: Optional[Exception] = None,
    ):
        """Callback for when a language model ends."""
        current_span = trace.get_current_span()
        current_span.set_attribute("call_id", call_id)
        if exception:
            current_span.record_exception(exception)
            current_span.set_status(Status(StatusCode.ERROR, str(exception)))
        else:
            current_span.set_attribute("output", str(outputs))
            current_span.set_status(Status(StatusCode.OK))
        # Span will automatically end when exiting the context

    # Adapter Callbacks
    def on_adapter_format_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """Callback for when an adapter format starts."""
        with self.tracer.start_as_current_span(
            f"adapter_format_start:{instance.__class__.__name__}",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("call_id", call_id)
            span.set_attribute("adapter_name", instance.__class__.__name__)
            for key, value in inputs.items():
                span.set_attribute(f"input.{key}", str(value))

    def on_adapter_format_end(
        self,
        call_id: str,
        outputs: Optional[Dict[str, Any]],
        exception: Optional[Exception] = None,
    ):
        """Callback for when an adapter format ends."""
        current_span = trace.get_current_span()
        current_span.set_attribute("call_id", call_id)
        if exception:
            current_span.record_exception(exception)
            current_span.set_status(Status(StatusCode.ERROR, str(exception)))
        else:
            current_span.set_attribute("output", str(outputs))
            current_span.set_status(Status(StatusCode.OK))
        # Span will automatically end when exiting the context

    def on_adapter_parse_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        """Callback for when an adapter parse starts."""
        with self.tracer.start_as_current_span(
            f"adapter_parse_start:{instance.__class__.__name__}",
            kind=trace.SpanKind.INTERNAL,
        ) as span:
            span.set_attribute("call_id", call_id)
            span.set_attribute("adapter_name", instance.__class__.__name__)
            for key, value in inputs.items():
                span.set_attribute(f"input.{key}", str(value))

    def on_adapter_parse_end(
        self,
        call_id: str,
        outputs: Optional[Dict[str, Any]],
        exception: Optional[Exception] = None,
    ):
        """Callback for when an adapter parse ends."""
        current_span = trace.get_current_span()
        current_span.set_attribute("call_id", call_id)
        if exception:
            current_span.record_exception(exception)
            current_span.set_status(Status(StatusCode.ERROR, str(exception)))
        else:
            current_span.set_attribute("output", str(outputs))
            current_span.set_status(Status(StatusCode.OK))
        # Span will automatically end when exiting the context

    # Tool Callbacks
    def on_tool_start(
        self,
        call_id: str,
        instance: Any,
        inputs: Dict[str, Any],
    ):
        with self.tracer.start_as_current_span(
            f"tool_start:{instance.__class__.__name__}", kind=trace.SpanKind.INTERNAL
        ) as span:
            span.set_attribute("call_id", call_id)
            span.set_attribute("tool_name", instance.__class__.__name__)
            for key, value in inputs.items():
                span.set_attribute(f"input.{key}", str(value))

    def on_tool_end(
        self,
        call_id: str,
        outputs: Optional[Dict[str, Any]],
        exception: Optional[Exception] = None,
    ):
        current_span = trace.get_current_span()
        current_span.set_attribute("call_id", call_id)
        if exception:
            current_span.record_exception(exception)
            current_span.set_status(Status(StatusCode.ERROR, str(exception)))
        else:
            current_span.set_attribute("output", str(outputs))
            current_span.set_status(Status(StatusCode.OK))
