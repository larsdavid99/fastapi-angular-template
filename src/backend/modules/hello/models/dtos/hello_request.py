"""Hello Request DTO."""

from pydantic import BaseModel, Field


class HelloRequest(BaseModel):
    """API request for the hello endpoint."""

    name: str = Field(..., min_length=1, description="Name to greet")
