"""A pull request as the gate and the after-merge decision need it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PullRequest:
    number: int
    branch: str
    head_sha: str
    base: str
    merged: bool
    mergeable: bool | None  # None until GitHub has worked it out

    @classmethod
    def from_json(cls, pull: dict[str, Any]) -> PullRequest:
        return cls(
            number=pull["number"],
            branch=pull["head"]["ref"],
            head_sha=pull["head"]["sha"],
            base=pull["base"]["ref"],
            merged=pull["merged"],
            mergeable=pull["mergeable"],
        )
