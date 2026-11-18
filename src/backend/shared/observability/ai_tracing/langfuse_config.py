"""Langfuse Config DTO."""

from pydantic import BaseModel, Field


class LangfuseConfig(BaseModel):
    """Where AI traces go (ADR-0002)."""

    public_key: str
    secret_key: str
    base_url: str = Field(..., description="e.g. https://cloud.langfuse.com")
    environment: str = Field(..., description="Langfuse's environment filter")
