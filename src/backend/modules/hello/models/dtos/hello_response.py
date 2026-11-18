"""Hello Response DTO."""

from pydantic import BaseModel, Field


class HelloResponse(BaseModel):
    """API response for the hello endpoint."""

    message: str = Field(..., description="Greeting message")
    uuid: str = Field(..., description="A fresh UUID from the UUID source")
