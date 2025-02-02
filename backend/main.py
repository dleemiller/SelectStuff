# app/main.py

import logging
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from applications import router as apps_router


# import applications.news #noqa F401 # Replacing this with importlib
from applications.models.inputs import TextInputRequest  # noqa F401


# from .config import AppConfig, load_config
from .routes.db_routes import router as db_router

# ------------------------------
# Configure Logging
# ------------------------------
logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

# ------------------------------
# Load Environment Variables
# ------------------------------
load_dotenv()
APIKEY = os.getenv("APIKEY")


# ------------------------------
# OpenTelemetry Configuration
# ------------------------------
# resource = Resource(
#     attributes={
#         "service.name": "SelectStuff",
#         "os-version": 1234.56,
#         "cluster": "Local",
#         "datacentre": "Local",
#     }
# )

if os.getenv("ENABLE_TRACING", "false").lower() == "true":
    # 1. Create a Resource for the service
    resource = Resource.create({"service.name": "fastapi"})

    # 2. Create a TracerProvider and add the OTLP gRPC exporter
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer_provider = trace.get_tracer_provider()

    # Configure OTLP via environment variables or explicitly:
    #   endpoint="http://jaeger:4317", insecure=True
    otlp_exporter = OTLPSpanExporter()

    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
else:
    # Set up a no-op tracer for local development
    trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)


# ------------------------------
# Application Setup
# ------------------------------
def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    # Initialize FastAPI instance
    app = FastAPI(
        title="Database Interaction API",
        description="An API for interacting with SQLite and running SQL queries.",
        version="1.0.0",
    )

    # Configure CORS middleware
    origins = [
        "chrome-extension://*",  # Allow Chrome extensions
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    # Middleware for CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load application configuration
    # app_config = load_config("config.yml")

    # Configure LLM
    # configure_llm(app_config, APIKEY, callbacks=[])

    # Store global objects in application state
    # app.state.db_manager = initialize_database(app_config)
    app.include_router(router=apps_router)
    app.include_router(router=db_router)
    # 4. Instrument FastAPI
    # FastAPIInstrumentor.instrument_app(app)

    # register_routes(app, app_config) #moved this to register them all on a router that we mount to the app above.

    return app


# ------------------------------
# Entry Point
# ------------------------------

application = create_app()


# Health Check
@application.get("/health", include_in_schema=False)
def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}
