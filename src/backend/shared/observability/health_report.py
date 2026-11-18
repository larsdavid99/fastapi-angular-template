"""Health Report DTO."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthReport(BaseModel):
    """What GET /health answers: the app's status and each dependency's."""

    status: Literal["ok", "degraded"]
    checks: dict[str, Literal["ok", "down"]] = Field(
        ..., description="One entry per dependency, e.g. 'database'"
    )
