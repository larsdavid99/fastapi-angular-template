"""Fake UuidSource for tests: hands out fixed UUIDs, or fails on request."""

from modules.hello.exceptions.uuid_source_unavailable_error import (
    UuidSourceUnavailableError,
)


class FakeUuidSource:
    def __init__(self, uuid: str = "fake-uuid-0000", available: bool = True):
        self.uuid = uuid
        self.available = available
        self.calls = 0

    async def next_uuid(self) -> str:
        self.calls += 1
        if not self.available:
            raise UuidSourceUnavailableError()
        return self.uuid
