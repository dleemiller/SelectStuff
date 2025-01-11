import os

import dspy
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .config import AppConfig, load_config
from .database import DuckDBManager

import logging

logging.getLogger().setLevel(logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)


# set your api key (if needed)
load_dotenv()
APIKEY = os.getenv("APIKEY")

# Import applications to ensure they are registered
import app.applications.news
from app.models.inputs import TextInputRequest

# Load configuration
app_config = load_config("config.yml")

# set your model (litellm model strings)
lm = dspy.LM(app_config.model.name, api_key=APIKEY, cache=True)
dspy.configure(lm=lm)

# Create FastAPI instance and router
app = FastAPI()
router = APIRouter()
db_manager = DuckDBManager(app_config.database)

# Register routes dynamically
for route in app_config.routes:
    path, handler = route.create_route(db_manager)
    router.post(path)(handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include the router in the FastAPI app
app.include_router(router)
