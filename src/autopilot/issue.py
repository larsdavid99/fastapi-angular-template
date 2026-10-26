"""An issue (Spec or Ticket) as the decisions need it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from labels import WORKING


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    is_open: bool
    labels: frozenset[str]
    open_blockers: int

    @property
    def being_built(self) -> bool:
        """Claimed by the loop and not yet merged or handed back."""
        return self.is_open and WORKING in self.labels

    @classmethod
    def from_json(cls, issue: dict[str, Any]) -> Issue:
        return cls(
            number=issue["number"],
            title=issue["title"],
            is_open=issue["state"] == "open",
            labels=frozenset(label["name"] for label in issue["labels"]),
            open_blockers=issue["issue_dependencies_summary"]["blocked_by"],
        )
