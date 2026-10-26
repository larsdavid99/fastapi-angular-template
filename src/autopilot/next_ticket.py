"""`next <spec>`: the Ticket to build next, or why there's none."""

from github import GitHub
from issue import Issue
from labels import READY_FOR_HUMAN, WORKING


def decide_next(github: GitHub, spec_number: int) -> str:
    open_tickets = [t for t in github.sub_issues(spec_number) if t.is_open]
    if not open_tickets:
        return "done"
    buildable = [t for t in open_tickets if _agent_can_build(t)]
    if not buildable:
        waiting_on = ", ".join(f"#{t.number}" for t in open_tickets)
        return f"pause: waiting on {waiting_on}"
    return f"ticket #{buildable[0].number}"


def _agent_can_build(ticket: Issue) -> bool:
    return (
        ticket.open_blockers == 0
        and READY_FOR_HUMAN not in ticket.labels
        and WORKING not in ticket.labels
    )
