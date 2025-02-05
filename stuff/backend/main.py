# backend/main.py

import time
import uuid
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from stuff.applications import router as apps_router
from stuff.shared.logging_config import configure_logging, get_logger, request_id

# ------------------------------
# Load Environment Variables
# ------------------------------
load_dotenv()
APIKEY = os.getenv("APIKEY")

# ------------------------------
# Configure Logging
# ------------------------------
configure_logging("fastapi")
logger = get_logger("fastapi")

# ------------------------------
# OpenTelemetry Configuration
# ------------------------------
if os.getenv("ENABLE_TRACING", "false").lower() == "true":
    resource = Resource.create({"service.name": "fastapi"})
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()
    otlp_exporter = OTLPSpanExporter()
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
else:
    trace.set_tracer_provider(TracerProvider())  # No-op tracer for local dev

tracer = trace.get_tracer(__name__)


# ------------------------------
# Application Setup
# ------------------------------
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title="Database Interaction API",
        description="API for interacting with databases and running queries.",
        version="1.0.0",
    )

    # Middleware to log all requests
    @app.middleware("http")
    async def logging_middleware(request: Request, call_next):
        req_id = str(uuid.uuid4())  # Generate a request ID
        request_id.set(req_id)  # Store it in context variable

        start_time = time.time()
        logger.info(
            "request.start",
            path=request.url.path,
            method=request.method,
            query_params=str(request.query_params),
            client_host=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                "request.complete",
                path=request.url.path,
                method=request.method,
                status_code=response.status_code,
                duration=duration,
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.exception(
                "request.error",
                path=request.url.path,
                method=request.method,
                error=str(e),
                duration=duration,
            )
            raise

    # CORS settings
    origins = [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "chrome-extension://*",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include application routers
    app.include_router(apps_router)

    return app


# ------------------------------
# Entry Point
# ------------------------------
application = create_app()


@application.get("/health", include_in_schema=False)
def health_check():
    """Health check endpoint."""
    logger.info("health_check called")
    return {"status": "healthy"}
