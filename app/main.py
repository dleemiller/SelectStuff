from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .config import AppConfig, load_config
from .database import DuckDBManager

# Import applications to ensure they are registered
import app.applications.news
from app.models.inputs import TextInputRequest

# Load configuration
app_config = load_config("config.yml")

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
