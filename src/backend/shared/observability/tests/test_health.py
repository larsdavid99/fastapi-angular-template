"""GET /health reports each dependency."""

from main import app
from shared.observability.health_dependencies import get_health_checks


async def _up() -> bool:
    return True


async def _down() -> bool:
    return False


async def _broken() -> bool:
    raise ConnectionError("database unreachable")


def test_ok_with_no_dependencies(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {}}


def test_ok_while_every_dependency_is_up(client):
    app.dependency_overrides[get_health_checks] = lambda: {"database": _up}

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"database": "ok"}}


def test_degraded_when_a_dependency_is_down_or_broken(client):
    app.dependency_overrides[get_health_checks] = lambda: {
        "database": _up,
        "vendor": _down,
        "cache": _broken,
    }

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"database": "ok", "vendor": "down", "cache": "down"},
    }
