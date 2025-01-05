from abc import ABC, abstractmethod
from typing import Dict, Callable, Type
from pydantic import BaseModel

from app.database import DuckDBManager


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
    def __init__(self, db_manager: DuckDBManager, table_name: str):
        self.db_manager = db_manager
        self.table_name = table_name
        self.ensure_table()

    @property
    @abstractmethod
    def schema(self) -> str:
        """DuckDB table schema definition."""
        pass

    def ensure_table(self):
        """Ensure the table exists in the database."""
        self.db_manager.create_table(self.schema)

    @abstractmethod
    def process(self, data: dict):
        """Application-specific logic for processing data."""
        pass
