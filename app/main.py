# app/main.py

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

import dspy

from .config import load_config, AppConfig
from .database import SQLiteManager

# Import applications to ensure they are registered
import app.applications.news
from app.models.inputs import TextInputRequest
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

    # Fix: Pass the tags when registering routes
    for route in config.routes:
        path, handler = route.create_route(app.state.db_manager)
        app.post(path, tags=route.tags)(handler)


# ------------------------------
# Entry Point
# ------------------------------
app = create_app()
