from abc import ABC, abstractmethod
from typing import Dict, Callable, Type
from pydantic import BaseModel

from app.database import SQLiteManager


_application_stuff: Dict[str, Callable] = {}


def stuff(name: str):
    """Decorator to register a valid application by name."""

    def decorator(func: Callable):
        _application_stuff[name] = func
        return func

    return decorator


def get_stuff() -> Dict[str, Callable]:
    """Retrieve the list of registered applications."""
    return _application_stuff


class ApplicationStuff(ABC):
    def __init__(self, db_manager: SQLiteManager, table_name: str):
        self.db_manager = db_manager
        self.table_name = table_name

    @abstractmethod
    def process(self, data: dict):
        """Application-specific logic for processing data."""
        pass
