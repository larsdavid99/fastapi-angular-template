"""Tests for HelloLogic."""

import pytest

from exceptions.example_api_error import ExampleApiError
from logic.hello_logic import HelloLogic
from models.dtos.hello_request import HelloRequest


class TestBuildMessage:
    def setup_method(self):
        self.logic = HelloLogic(example_http_client=None)

    def test_formats_greeting(self):
        assert self.logic._build_message("World") == "Hello World"


class TestGreet:
    async def test_happy_path_returns_message_and_uuid(self, mock_example_http_client):
        logic = HelloLogic(example_http_client=mock_example_http_client)

        result = await logic.greet(HelloRequest(name="World"))

        assert result.message == "Hello World"
        assert result.uuid == "fake-uuid-0000"
        mock_example_http_client.fetch_uuid.assert_awaited_once()

    async def test_propagates_client_errors(self, mock_example_http_client):
        mock_example_http_client.fetch_uuid.side_effect = ExampleApiError(
            message="boom", source="httpbin"
        )
        logic = HelloLogic(example_http_client=mock_example_http_client)

        with pytest.raises(ExampleApiError, match="boom"):
            await logic.greet(HelloRequest(name="World"))
