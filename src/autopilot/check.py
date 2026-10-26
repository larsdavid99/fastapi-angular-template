"""A CI check on a PR's head commit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Conclusions that don't hold a PR back. Anything else that finished is red.
_PASSING = {"success", "neutral", "skipped"}


@dataclass(frozen=True)
class Check:
    name: str
    finished: bool
    passed: bool

    @classmethod
    def from_json(cls, run: dict[str, Any]) -> Check:
        return cls(
            name=run["name"],
            finished=run["status"] == "completed",
            passed=run["conclusion"] in _PASSING,
        )
