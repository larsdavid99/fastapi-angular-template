"""A Ticket of a Spec: open, or closed with the PRs that merged for it."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# GitHub's closing keywords, as in a PR body's `Closes #<ticket>`
_CLOSES = r"\b(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?):?\s+#{}\b"


@dataclass(frozen=True)
class TicketOutcome:
    number: int
    title: str
    is_open: bool
    merged_prs: tuple[int, ...]

    @classmethod
    def from_json(
        cls, issue: dict[str, Any], timeline: list[dict[str, Any]]
    ) -> TicketOutcome:
        """A merged PR counts when its body closes the Ticket as `#<n>`.

        REST has no field for the PRs that closed an issue, so this reads the
        timeline, which lists every PR that names the Ticket. Unlike GraphQL's
        closing references, it misses a PR linked by hand, or one that closes it
        as `owner/repo#<n>` or by URL: Autopilot PRs start `Closes #<n>`.
        """
        closes = re.compile(_CLOSES.format(issue["number"]), re.IGNORECASE)
        merged = [
            pr["number"]
            for pr in _referencing_prs(timeline)
            if pr["pull_request"]["merged_at"] and closes.search(pr["body"] or "")
        ]
        return cls(
            number=issue["number"],
            title=issue["title"],
            is_open=issue["state"] == "open",
            merged_prs=tuple(dict.fromkeys(merged)),  # once each, in timeline order
        )


def _referencing_prs(timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sources = [
        event["source"]["issue"]
        for event in timeline
        if event["event"] == "cross-referenced"
    ]
    return [source for source in sources if "pull_request" in source]
