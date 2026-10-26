"""Seam 1: which Ticket of a Spec on autopilot gets built next."""

import pytest

SPEC = 66


@pytest.fixture(autouse=True)
def spec(github):
    github.issue(SPEC, title="Autopilot", labels=("ready-for-agent", "autopilot"))


def test_the_first_open_ticket_in_sub_issue_order_is_next(github, autopilot):
    github.issue(76, state="closed")
    github.issue(80)
    github.issue(78)
    github.sub_issues(SPEC, 76, 78, 80)

    assert autopilot("next", "66") == "ticket #78"


def test_a_ticket_with_an_open_blocker_is_skipped(github, autopilot):
    github.issue(79, open_blockers=1)
    github.issue(80)
    github.sub_issues(SPEC, 79, 80)

    assert autopilot("next", "66") == "ticket #80"


def test_a_ticket_for_a_human_is_skipped(github, autopilot):
    github.issue(81, labels=("ready-for-human",))
    github.issue(82, labels=("ready-for-agent",))
    github.sub_issues(SPEC, 81, 82)

    assert autopilot("next", "66") == "ticket #82"


def test_a_ticket_already_being_worked_on_is_skipped(github, autopilot):
    github.issue(78, labels=("ready-for-agent", "autopilot:working"))
    github.issue(79, labels=("ready-for-agent",))
    github.sub_issues(SPEC, 78, 79)

    assert autopilot("next", "66") == "ticket #79"


def test_it_pauses_when_only_blocked_or_human_tickets_are_left(github, autopilot):
    github.issue(78, state="closed")
    github.issue(81, labels=("ready-for-human",))
    github.issue(83, open_blockers=1)
    github.sub_issues(SPEC, 78, 81, 83)

    assert autopilot("next", "66") == "pause: waiting on #81, #83"


def test_it_is_done_when_every_ticket_is_closed(github, autopilot):
    github.issue(78, state="closed")
    github.issue(79, state="closed")
    github.sub_issues(SPEC, 78, 79)

    assert autopilot("next", "66") == "done"
