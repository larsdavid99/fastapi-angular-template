"""UUID Source — the port HelloLogic gets its UUIDs through."""

from typing import Protocol


class UuidSource(Protocol):
    """Hands out a fresh UUID; raises UuidSourceUnavailableError when it can't."""

    async def next_uuid(self) -> str: ...
