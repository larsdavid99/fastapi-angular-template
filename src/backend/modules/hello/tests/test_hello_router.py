"""POST /api/hello end to end, with the UuidSource faked."""

import pytest

from main import app
from modules.hello.dependencies.hello_dependencies import get_uuid_source
from modules.hello.tests.fake_uuid_source import FakeUuidSource


@pytest.fixture
def uuid_source(client):
    source = FakeUuidSource(uuid="uuid-1")
    app.dependency_overrides[get_uuid_source] = lambda: source
    return source


def test_greets_with_a_uuid(client, uuid_source):
    response = client.post("/api/hello", json={"name": "World"})

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World", "uuid": "uuid-1"}


def test_an_unavailable_source_is_a_502(client, uuid_source):
    uuid_source.available = False

    response = client.post("/api/hello", json={"name": "World"})

    assert response.status_code == 502
    assert response.json() == {"detail": "UUID source unavailable"}


def test_an_empty_name_is_a_422(client, uuid_source):
    assert client.post("/api/hello", json={"name": ""}).status_code == 422
