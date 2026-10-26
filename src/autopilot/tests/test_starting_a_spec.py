"""Seam 1: whether a Spec labelled `autopilot` may start, resume or is refused."""

import pytest

SPEC = 66


@pytest.fixture
def approved_spec(github):
    """A Spec the Reviewer approved, cut into Tickets, just labelled `autopilot`."""
    github.issue(SPEC, title="Autopilot", labels=("ready-for-agent", "autopilot"))
    github.issue(78, labels=("ready-for-agent",))
    github.sub_issues(SPEC, 78)


def test_an_approved_spec_starts(approved_spec, autopilot):
    assert autopilot("start", "66") == "start"


def test_a_spec_that_built_a_ticket_before_resumes(approved_spec, github, autopilot):
    github.label(78, "autopilot:working")
    github.unlabel(78, "autopilot:working")  # handed back, or its PR merged
    github.unlabel(SPEC, "autopilot")
    github.label(SPEC, "autopilot")

    assert autopilot("start", "66") == "resume"


def test_a_spec_refused_before_starts_once_approved(github, autopilot):
    github.issue(SPEC, labels=("needs-review", "autopilot"))
    github.issue(78, labels=("ready-for-agent",))
    github.sub_issues(SPEC, 78)
    github.unlabel(SPEC, "autopilot")  # refused
    github.unlabel(SPEC, "needs-review")
    github.label(SPEC, "ready-for-agent")
    github.label(SPEC, "autopilot")

    assert autopilot("start", "66") == "start"


def test_a_spec_still_in_review_is_refused(github, autopilot):
    github.issue(SPEC, labels=("needs-review", "ready-for-agent", "autopilot"))
    github.issue(78)
    github.sub_issues(SPEC, 78)

    assert autopilot("start", "66") == "refuse: #66 still needs review"


def test_a_spec_that_isnt_ready_for_agent_is_refused(github, autopilot):
    github.issue(SPEC, labels=("idea", "autopilot"))
    github.issue(78)
    github.sub_issues(SPEC, 78)

    assert autopilot("start", "66") == "refuse: #66 isn't ready-for-agent"


def test_a_second_spec_is_refused_while_another_runs(approved_spec, github, autopilot):
    github.issue(12, title="Leaderboards", labels=("ready-for-agent", "autopilot"))

    assert autopilot("start", "66") == "refuse: #12 is already on autopilot"


def test_a_pull_request_labelled_autopilot_isnt_a_running_spec(
    approved_spec, github, autopilot
):
    github.pull_request(97, labels=("autopilot",))

    assert autopilot("start", "66") == "start"


def test_a_spec_whose_label_was_removed_before_the_run_is_refused(
    approved_spec, github, autopilot
):
    github.unlabel(SPEC, "autopilot")

    assert autopilot("start", "66") == "refuse: #66 isn't labelled autopilot"


def test_a_spec_without_tickets_is_refused(github, autopilot):
    github.issue(SPEC, labels=("ready-for-agent", "autopilot"))

    assert autopilot("start", "66") == "refuse: #66 has no Tickets"


def test_a_spec_re_labelled_while_a_ticket_is_built_waits_for_it(
    approved_spec, github, autopilot
):
    """Removed and re-added mid-Ticket: that Ticket's merge carries the loop on."""
    github.label(78, "autopilot:working")
    github.unlabel(SPEC, "autopilot")
    github.label(SPEC, "autopilot")

    assert autopilot("start", "66") == "wait: #78 is still being built"


def test_a_closed_ticket_still_marked_working_doesnt_hold_a_spec_up(
    approved_spec, github, autopilot
):
    github.issue(77, labels=("autopilot:working",), state="closed")
    github.sub_issues(SPEC, 77, 78)

    assert autopilot("start", "66") == "resume"
