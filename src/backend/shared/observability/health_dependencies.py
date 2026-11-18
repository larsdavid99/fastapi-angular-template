"""Health Dependencies — which dependencies GET /health checks."""

from collections.abc import Awaitable, Callable

HealthCheck = Callable[[], Awaitable[bool]]


def get_health_checks() -> dict[str, HealthCheck]:
    """Name → check; add one per dependency (e.g. "database") as the app gains it."""
    return {}
