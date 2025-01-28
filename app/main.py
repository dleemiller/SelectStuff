# app/main.py

import logging
import os

import dspy
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator

# Import applications to ensure they are registered
import app.applications.news
from app.models.inputs import TextInputRequest

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
def setup_tracer(application: FastAPI):
    # Set up the tracer provider
    trace.set_tracer_provider(
        TracerProvider(resource=Resource.create({SERVICE_NAME: "fastapi-app"}))
    )
    tracer = trace.get_tracer(__name__)

    # Configure the Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=os.getenv("JAEGER_AGENT_HOST", "jaeger"),
        agent_port=int(os.getenv("JAEGER_AGENT_PORT", 6831))
        # collector_endpoint="http://jaeger:14250/api/traces"
    )

    # Add the exporter to the tracer provider
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(jaeger_exporter))

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(
        application, tracer_provider=trace.get_tracer_provider()
    )
    RequestsInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    # Instrument logging
    LoggingInstrumentor().instrument(set_logging_format=True)

    return tracer


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

    # Middleware for CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load application configuration
    app_config = load_config("config.yml")

    # Configure LLM
    configure_llm(app_config, APIKEY)

    # Store global objects in application state
    app.state.db_manager = initialize_database(app_config)

    # Register routes
    register_routes(app, app_config)
    setup_tracer(app)
    Instrumentator().instrument(app).expose(app)

    return app


# ------------------------------
# Helper Functions
# ------------------------------
def configure_llm(config: AppConfig, api_key: str):
    """
    Configure the LLM for use across the application.
    """
    lm = dspy.LM(config.model.name, api_key=api_key, cache=True)
    dspy.configure(lm=lm)


def initialize_database(config) -> SQLiteManager:
    """
    Initialize and return the SQLiteManager instance.
    """
    return SQLiteManager(db_path=config.database)


def register_routes(app: FastAPI, config: AppConfig):
    """
    Register all application routes.
    """
    # Include the database-related routes
    app.include_router(db_router)

    # Dynamically register additional routes defined in config. Pass Tags.
    for route in config.routes:
        path, handler = route.create_route(app.state.db_manager)
        app.post(path, tags=route.tags)(handler)


# ------------------------------
# Entry Point
# ------------------------------
application = create_app()


# Health Check
@application.get("/health")
def health_check():
    return {"status": "healthy"}
