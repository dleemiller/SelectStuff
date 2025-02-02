from pydantic import BaseModel, Field
from ..helpers.models import request_model


@request_model("TextInput")
class TextInputRequest(BaseModel):
    text: str = Field(
        ...,
        description="The main text content to process",
        example="Example text content",
    )
    url: str = Field(
        ...,
        description="The URL associated with the text content",
        example="https://example.com",
    )
