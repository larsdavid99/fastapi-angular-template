"""Tests for HelloLogic."""

import pytest

from modules.hello.exceptions.uuid_source_unavailable_error import (
    UuidSourceUnavailableError,
)
from modules.hello.logic.hello_logic import HelloLogic
from modules.hello.models.dtos.hello_request import HelloRequest
from modules.hello.tests.fake_uuid_source import FakeUuidSource


async def test_greets_by_name_with_a_fresh_uuid():
    source = FakeUuidSource(uuid="uuid-1")
    logic = HelloLogic(uuid_source=source)

    result = await logic.greet(HelloRequest(name="World"))

    assert result.message == "Hello World"
    assert result.uuid == "uuid-1"
    assert source.calls == 1


async def test_an_unavailable_source_propagates():
    logic = HelloLogic(uuid_source=FakeUuidSource(available=False))

    with pytest.raises(UuidSourceUnavailableError):
        await logic.greet(HelloRequest(name="World"))
