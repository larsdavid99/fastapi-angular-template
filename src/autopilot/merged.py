"""`merged <pr>`: what the loop does once an Autopilot PR has merged."""

from __future__ import annotations

from typing import Callable

from branch import ticket_of
from github import GitHub
from issue import Issue
from labels import AUTOPILOT, READY_FOR_HUMAN
from waiting import still_being_built

# The merge workflow closes the Ticket a step after it merges the PR, and this run
# starts on the merge, so it may read the Ticket in between.
_READS = 4
_SECONDS_BETWEEN_READS = 10

Sleep = Callable[[float], None]
"""Waits this many seconds."""


def decide_merged(github: GitHub, pr_number: int, sleep: Sleep) -> str:
    pr = github.pull_request(pr_number)
    ticket_number = ticket_of(pr.branch)
    # Hand-written PRs are the Driver's own, so the loop never acts on them.
    if ticket_number is None:
        return f"ignore: #{pr_number} isn't an Autopilot PR: {pr.branch}"
    if not pr.merged:
        return f"ignore: #{pr_number} wasn't merged"
    ticket = _read_until_closed(github, ticket_number, sleep)
    # Without `Closes #<n>`, `next` would pick the same Ticket and build it again.
    if ticket.is_open:
        return f"hand-back: #{ticket_number} is still open after #{pr_number} merged"
    return _after_closing(github, ticket, pr_number)


def _read_until_closed(github: GitHub, ticket_number: int, sleep: Sleep) -> Issue:
    """The Ticket, read again while it's open, up to a few times."""
    ticket = github.issue(ticket_number)
    for _ in range(_READS - 1):
        if not ticket.is_open:
            break
        sleep(_SECONDS_BETWEEN_READS)
        ticket = github.issue(ticket_number)
    return ticket


def _after_closing(github: GitHub, ticket: Issue, pr_number: int) -> str:
    spec = github.parent(ticket.number)
    # Removing the label stops the loop after the current Ticket, not during it.
    if AUTOPILOT not in spec.labels:
        return _stopped(spec, ticket, pr_number)
    # A PR the Driver took over and merged, while the loop runs on without it.
    waiting_for = still_being_built(github.sub_issues(spec.number))
    if waiting_for:
        return f"wait: {waiting_for}"
    return f"move-on #{spec.number}"


def _stopped(spec: Issue, ticket: Issue, pr_number: int) -> str:
    """A hand-back took `autopilot` off and said so on the Spec already."""
    if READY_FOR_HUMAN in ticket.labels:
        return f"already-stopped: #{ticket.number} was handed back before #{pr_number} merged"
    return f"stop: #{spec.number} isn't labelled {AUTOPILOT}"
