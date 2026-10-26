"""One Ticket at a time: while one is being built, its merge moves the loop on."""

from __future__ import annotations

from issue import Issue


def still_being_built(tickets: list[Issue]) -> str | None:
    building = [t for t in tickets if t.being_built]
    return f"#{building[0].number} is still being built" if building else None
