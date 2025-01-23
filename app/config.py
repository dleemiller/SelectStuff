from typing import Callable, Optional, Type

import yaml
from pydantic import BaseModel, field_validator
from fastapi import APIRouter

from .applications import get_stuff
from .models import get_request_model
from .database import SQLiteManager


# models.py

from typing import Callable, Optional, Type

import yaml
from pydantic import BaseModel, field_validator
from fastapi import APIRouter

from .applications import get_stuff
from .models import get_request_model
from .database import SQLiteManager


class RouteConfig(BaseModel):
    name: str
    path: str
    application: str
    table: str
    request_model: Type[BaseModel]
    tags: list[str] = ["Default"]

    @field_validator("application")
    def validate_application(cls, application):
        registered_apps = get_stuff()
        if application not in registered_apps:
            raise ValueError(
                f"Application '{application}' is not registered. "
                f"Available applications: {list(registered_apps.keys())}"
            )
        return application

    @field_validator("request_model", mode="before")
    def resolve_request_model(cls, request_model):
        """Resolve the request model name into a registered model."""
        return get_request_model(request_model)

    def create_route(self, db_manager: SQLiteManager) -> Callable:
        registered_apps = get_stuff()
        app_class = registered_apps[self.application]

        # Initialize the application with the specified table
        application = app_class(db_manager, self.table)

        async def route_handler(data: self.request_model):  # Use the request model
            return application.process(data.dict())

        return self.path, route_handler



class ModelConfig(BaseModel):
    name: str
    ipaddr: Optional[str] = None
    apikey: Optional[str] = None


class AppConfig(BaseModel):
    routes: list[RouteConfig]
    database: str
    model: ModelConfig

    def register_routes(self, router: APIRouter):
        """Register all routes to the provided router."""
        for route in self.routes:
            path, handler = route.create_route()
            router.post(path, tags=route.tags)(handler)


def load_config(yaml_file: str) -> AppConfig:
    with open(yaml_file, "r") as file:
        data = yaml.safe_load(file)
    return AppConfig(**data)
