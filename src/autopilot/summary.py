"""`summary <spec>`: the merged PRs to list on a Spec that's done.

The Driver can also run it by hand on a Spec still in progress, so open Tickets
are listed too.
"""

from __future__ import annotations

from github import GitHub
from ticket_outcome import TicketOutcome


def decide_summary(github: GitHub, spec_number: int) -> str:
    return "\n".join(_line(t) for t in github.ticket_outcomes(spec_number))


def _line(ticket: TicketOutcome) -> str:
    if ticket.is_open:
        return f"- #{ticket.number} {ticket.title}: still open"
    if not ticket.merged_prs:
        return f"- #{ticket.number} {ticket.title}: closed without a merged PR"
    prs = ", ".join(f"#{pr}" for pr in ticket.merged_prs)
    return f"- #{ticket.number} {ticket.title}: merged in {prs}"
