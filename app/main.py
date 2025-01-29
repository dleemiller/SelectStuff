# app/main.py

import logging
import os

import dspy
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Import applications to ensure they are registered
import app.applications.news #noqa F401
from app.models.inputs import TextInputRequest #noqa F401
from .config import AppConfig, load_config
from .database import SQLiteManager
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


# 1. Create a Resource for your service
resource = Resource.create({"service.name": "fastapi"})

# 2. Create a TracerProvider and add the OTLP gRPC exporter
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()

# Configure OTLP via environment variables or explicitly:
#   endpoint="http://jaeger:4317", insecure=True
otlp_exporter = OTLPSpanExporter()

span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)
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
    app_config = load_config("config.yml")

    # Configure LLM
    configure_llm(app_config, APIKEY, callbacks=[])

    # Store global objects in application state
    app.state.db_manager = initialize_database(app_config)

    # 4. Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Register routes
    register_routes(app, app_config)

    return app


# ------------------------------
# Helper Functions
# ------------------------------
def configure_llm(config: AppConfig, api_key: str, callbacks: list):
    """
    Configure the LLM for use across the application.
    """
    lm = dspy.LM(config.model.name, api_key=api_key, cache=True, callbacks=[])
    dspy.configure(lm=lm)


def initialize_database(config) -> SQLiteManager:
    """
    Initialize and return the SQLiteManager instance.
    """
    return SQLiteManager(db_path=config.database)


def register_routes(app: FastAPI, config: AppConfig):
    """
    Register all application routes with proper decorator wrapping.
    """
    # Include the database-related routes
    app.include_router(db_router)

    # Dynamically register additional routes defined in config
    for route in config.routes:
        path, base_handler = route.create_route(app.state.db_manager)

        # Create the span name for tracing
        span_name = f"handle_{route.tags[0]}_{path.replace('/','_')}"

        # Define the wrapped handler that maintains type hints and request model
        @app.post(path, tags=route.tags)
        async def wrapped_handler(data: route.request_model) -> dict:
            with tracer.start_as_current_span(span_name):
                return await base_handler(data)


# ------------------------------
# Entry Point
# ------------------------------
application = create_app()


# Health Check
@application.get("/health")
def health_check():
    """Health check endpoint to verify the service is running."""
    return {"status": "healthy"}
