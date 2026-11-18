"""AI Trace DTO."""

from datetime import datetime

from pydantic import BaseModel, Field


class AiTrace(BaseModel):
    """
    One AI call as sent to AI tracing (ADR-0002). input and output already have
    names and phone numbers replaced by placeholders.
    """

    name: str = Field(..., description="What the call was for, e.g. 'summarise'")
    correlation_id: str = Field(..., description="ID of the request or job's work")
    model: str
    prompt_version: str
    input: str
    output: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = Field(None, description="None when no tokens were used")
    started_at: datetime
    latency_ms: int
    error: str | None = Field(None, description="Why the call gave no answer")
