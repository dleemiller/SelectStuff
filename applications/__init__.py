# applications/__init__.py

import importlib
from .helpers.appconfig import AppConfig, load_config
from .helpers.database import initialize_database
from .helpers.llm import configure_llm
import pkgutil
import os
from fastapi import APIRouter
import logging
from opentelemetry import trace
from .models import inputs

tracer = trace.get_tracer(__name__)
router = APIRouter(prefix="/v1")
APIKEY = os.getenv("APIKEY")

def path_to_tags(path: str) -> list[str]:
    """
    Convert a path like '/news/politics' into hierarchical tags ['Select/News']
    The last component is excluded since it's the endpoint name
    """
    # Remove leading slash and split
    parts = path.strip("/").split("/")
    # Only use parts up to the second-to-last one (if they exist)
    if len(parts) > 1:
        hierarchy_parts = parts[:-1]  # Exclude the last part
        return ["/".join(["Select"] + [part.capitalize() for part in hierarchy_parts])]
    return [parts[0].capitalize()]


def register_all_subrouters():
    """
    Find and import each submodule under 'applications/<module_name>/router.py'
    that defines 'router = APIRouter()', and include it in the single 'applications.router'.

    Optionally, we can filter which submodules are enabled based on config/ENV vars.
    """
    package_name = __name__  # "applications"

    # For illustration, maybe an ENV var like "ENABLED_APPS=news,search"
    enabled_apps = os.getenv("ENABLED_APPS")  # e.g. "news,search"

    if enabled_apps:
        enabled_apps = [app.strip() for app in enabled_apps.split(",")]
    print(f"Setting up enabled apps: {enabled_apps}")
    for app in enabled_apps:
        # for _, app, is_pkg in pkgutil.iter_modules(__path__):
        #     if is_pkg:
        # If you only want certain submodules, skip the disabled ones:
        if enabled_apps and (app not in enabled_apps):
            continue
        print(f"Importing module {app}")
        module = importlib.import_module(f"applications.{app}")
        print(f"Loading app config for {app}")
        config = load_config(f"applications/{app}/config.yml")
        configure_llm(config, APIKEY, callbacks=[])
        print(f"Initializing database for {app}")
        db_manager = initialize_database(config)
        print(f"Creating Routes for {app}")
        sub_router = APIRouter()
        for route in config.routes:
            path, base_handler = route.create_route(db_manager)
            hierarchical_tags = path_to_tags(path)
            handler_name = f"handle_{'_'.join(path.strip('/').split('/'))}"
            span_name = f"handle_{route.tags[0]}_{path.replace('/','_')}"

            # Use a factory function to create uniquely named handlers
            def create_handler(base_handler, handler_name):
                async def handler(data: route.request_model) -> dict:
                    with tracer.start_as_current_span(span_name):
                        return await base_handler(data)

                # Set the function name
                handler.__name__ = handler_name
                return handler

            # Create a unique handler for this route
            route_handler = create_handler(base_handler, handler_name)

            # Register with the unique handler
            sub_router.post(path, tags=hierarchical_tags)(route_handler)
            # Define the wrapped handler that maintains type hints and request model
            # @sub_router.post(path, tags=hierarchical_tags)
            # async def wrapped_handler(data: route.request_model) -> dict:
            #     with tracer.start_as_current_span(span_name):
            #         return await base_handler(data)
        router.include_router(sub_router)
        pass


# Run this at import time (or lazily call it the first time)
logging.debug("Attempting to register enaled routes on  parent router.")
register_all_subrouters()
