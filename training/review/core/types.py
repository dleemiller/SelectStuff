from enum import Enum, auto
from dataclasses import dataclass
from typing import Dict, Any


class FileAction(Enum):
    ACCEPT = auto()
    REJECT = auto()


@dataclass
class FieldConfig:
    """Configuration for how a field should be displayed and edited"""

    height: int
    widget_type: str = "text_area"
