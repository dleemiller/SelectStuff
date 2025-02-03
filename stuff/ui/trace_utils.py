from shared.logging_config import get_logger
import requests
import os

logger = get_logger("tracing_session")

class TracingSession(requests.Session):
    def __init__(self):
        super().__init__()
        self.trace_id = os.urandom(16).hex()
        logger.info(
            "tracing_session.initialized",
            trace_id=self.trace_id
        )
    
    def request(self, method, url, *args, **kwargs):
        # Generate new span ID for this request
        span_id = os.urandom(8).hex()
        traceparent = f"00-{self.trace_id}-{span_id}-01"
        
        # Add headers if they don't exist
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
            
        kwargs['headers']['traceparent'] = traceparent

        # Log the outgoing request with trace context
        logger.info(
            "http.request.started",
            method=method,
            url=url,
            trace_id=self.trace_id,
            span_id=span_id,
        )
        
        try:
            response = super().request(method, url, *args, **kwargs)
            
            # Log successful response
            logger.info(
                "http.request.completed",
                method=method,
                url=url,
                status_code=response.status_code,
                trace_id=self.trace_id,
                span_id=span_id,
            )
            return response
            
        except requests.RequestException as e:
            # Log failed request
            logger.error(
                "http.request.failed",
                method=method,
                url=url,
                error=str(e),
                trace_id=self.trace_id,
                span_id=span_id,
                exc_info=True
            )
            raise

tracing_session = TracingSession()