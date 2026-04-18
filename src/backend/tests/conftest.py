"""Shared test fixtures."""

from unittest.mock import AsyncMock

import pytest

from clients.example_http_client import ExampleHttpClient


@pytest.fixture
def mock_example_http_client():
    """ExampleHttpClient mock with a happy-path return value."""
    client = AsyncMock(spec=ExampleHttpClient)
    client.fetch_uuid.return_value = "fake-uuid-0000"
    return client
