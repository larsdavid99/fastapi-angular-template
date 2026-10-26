"""`start <spec>`: whether a Spec labelled `autopilot` may start."""

from __future__ import annotations

from github import GitHub
from issue import Issue
from labels import AUTOPILOT, NEEDS_REVIEW, READY_FOR_AGENT, WORKING
from waiting import still_being_built


def decide_start(github: GitHub, spec_number: int) -> str:
    spec = github.issue(spec_number)
    tickets = github.sub_issues(spec_number)
    refusal = _refusal(github, spec, tickets)
    if refusal:
        return f"refuse: {refusal}"
    waiting_for = still_being_built(tickets)
    if waiting_for:
        return f"wait: {waiting_for}"
    if _built_a_ticket_before(github, tickets):
        return "resume"
    return "start"


def _refusal(github: GitHub, spec: Issue, tickets: list[Issue]) -> str | None:
    # The label can be gone by the time the run starts: the Driver stopped it.
    if AUTOPILOT not in spec.labels:
        return f"#{spec.number} isn't labelled autopilot"
    if NEEDS_REVIEW in spec.labels:
        return f"#{spec.number} still needs review"
    if READY_FOR_AGENT not in spec.labels:
        return f"#{spec.number} isn't ready-for-agent"
    running = _other_specs_on_autopilot(github, spec.number)
    if running:
        return f"#{running[0]} is already on autopilot"
    if not tickets:
        return f"#{spec.number} has no Tickets"
    return None


def _other_specs_on_autopilot(github: GitHub, spec_number: int) -> list[int]:
    """Sorted, so the refusal names the same Spec on every run."""
    return sorted(
        issue.number
        for issue in github.open_issues_labelled(AUTOPILOT)
        if issue.number != spec_number
    )


def _built_a_ticket_before(github: GitHub, tickets: list[Issue]) -> bool:
    """A refused Spec never claimed a Ticket, so it starts rather than resumes."""
    return any(github.was_ever_labelled(t.number, WORKING) for t in tickets)
