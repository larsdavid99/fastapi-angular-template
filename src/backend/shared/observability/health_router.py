"""Health Router — reports the app and each dependency it needs."""

from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Depends, Response

from shared.observability.health_dependencies import HealthCheck, get_health_checks
from shared.observability.health_report import HealthReport

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthReport)
async def health(
    response: Response,
    checks: Annotated[dict[str, HealthCheck], Depends(get_health_checks)],
) -> HealthReport:
    """200 while every dependency is up, 503 (degraded) otherwise."""
    results = {name: await _run(name, check) for name, check in checks.items()}
    healthy = all(result == "ok" for result in results.values())
    response.status_code = 200 if healthy else 503
    return HealthReport(status="ok" if healthy else "degraded", checks=results)


async def _run(name: str, check: HealthCheck) -> Literal["ok", "down"]:
    """A check that raises counts as down, so one broken check can't 500 /health."""
    try:
        up = await check()
    except Exception:
        logger.warning("health.check_failed", check=name, exc_info=True)
        return "down"
    if not up:
        logger.warning("health.check_failed", check=name)
    return "ok" if up else "down"
