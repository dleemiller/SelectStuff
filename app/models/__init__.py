from typing import Dict, Type
from pydantic import BaseModel


_request_model: Dict[str, Type[BaseModel]] = {}


def request_model(name: str):
    """Decorator to register a request model by name."""

    def decorator(model_class: Type[BaseModel]):
        if name in _request_model:
            raise ValueError(f"Request model '{name}' is already registered.")
        _request_model[name] = model_class
        return model_class

    return decorator


def get_request_model(name: str) -> Type[BaseModel]:
    """Retrieve a registered request model by name."""
    if name not in _request_model:
        raise ValueError(f"Request model '{name}' is not registered.")
    return _request_model[name]


def list_request_models() -> Dict[str, Type[BaseModel]]:
    """List all registered request models."""
    return _request_model
