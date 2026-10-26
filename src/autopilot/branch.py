"""`branch <ticket> [<path> ...]`: the branch a Ticket is built on."""

from __future__ import annotations

import re

from github import GitHub
from issue import Issue
from labels import BUG, DOCUMENTATION

# Dropped from the slug, which keeps the title's first few meaningful words.
_FILLER = {"a", "an", "and", "at", "by", "for", "in", "is", "its", "of", "on", "the"}
_SLUG_WORDS = 5

# What decide_branch names, read back.
_AUTOPILOT_BRANCH = re.compile(r"claude/[a-z]+/(\d+)-.+")


def decide_branch(github: GitHub, ticket_number: int, paths: list[str]) -> str:
    ticket = github.issue(ticket_number)
    branch_type = _branch_type(ticket, paths)
    return f"claude/{branch_type}/{ticket_number}-{_slug(ticket.title)}"


def ticket_of(branch: str) -> int | None:
    """The Ticket an Autopilot branch builds, or None for a hand-written branch."""
    match = _AUTOPILOT_BRANCH.fullmatch(branch)
    return int(match[1]) if match else None


def _branch_type(ticket: Issue, paths: list[str]) -> str:
    """A person's label wins over the paths the agent expects to touch."""
    if BUG in ticket.labels:
        return "fix"
    if DOCUMENTATION in ticket.labels:
        return "docs"
    if not paths or any(path.startswith("src/") for path in paths):
        return "feature"
    if all(path.startswith("docs/") or path.endswith(".md") for path in paths):
        return "docs"
    if all(path.startswith(".github/") for path in paths):
        return "ci"
    return "chore"


def _slug(title: str) -> str:
    words = re.findall(r"[a-z0-9]+", re.sub(r"['’]", "", title.lower()))
    return "-".join([w for w in words if w not in _FILLER][:_SLUG_WORDS])
