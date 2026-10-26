"""Seam 1: what the loop does once an Autopilot PR merges."""

import pytest

from tests.fake_github import FakeGitHub

SPEC = 66
TICKET = 79
PR = 105
BRANCH = f"claude/feature/{TICKET}-pr-gets-gated"


@pytest.fixture(autouse=True)
def spec(github):
    """A Spec on autopilot whose Ticket's PR just merged, closing it."""
    github.issue(SPEC, title="Autopilot", labels=("ready-for-agent", "autopilot"))
    github.issue(TICKET, labels=("ready-for-agent",), state="closed")
    github.issue(80, labels=("ready-for-agent",))
    github.sub_issues(SPEC, TICKET, 80)


def merged_pr(github: FakeGitHub, branch: str = BRANCH, merged: bool = True) -> None:
    github.pull_request(PR, branch=branch, merged=merged)


def test_a_merged_pr_moves_the_spec_on(github, autopilot, slept):
    merged_pr(github)

    assert autopilot("merged", str(PR)) == "move-on #66"
    assert slept == []  # closed already: nothing to wait for


def test_the_loop_stops_once_the_driver_removed_autopilot(github, autopilot):
    github.unlabel(SPEC, "autopilot")  # mid-Ticket: the Ticket finished its PR
    merged_pr(github)

    assert autopilot("merged", str(PR)) == "stop: #66 isn't labelled autopilot"


def test_a_ticket_the_merge_workflow_closes_a_moment_later_moves_on(
    github, autopilot, slept
):
    """The run starts on the merge, before the workflow's next step closes it."""
    github.issue(TICKET, labels=("ready-for-agent", "autopilot:working"))
    github.closes_on_read(TICKET, 3)
    merged_pr(github)

    assert autopilot("merged", str(PR)) == "move-on #66"
    assert slept == [10, 10]


def test_a_merge_that_left_its_ticket_open_is_handed_back(github, autopilot, slept):
    """Otherwise `next` would pick the same Ticket and build it again."""
    github.issue(TICKET, labels=("ready-for-agent", "autopilot:working"))
    merged_pr(github)

    merged = autopilot("merged", str(PR))

    assert merged == "hand-back: #79 is still open after #105 merged"
    assert slept == [10, 10, 10]  # read four times, half a minute in all


def test_an_open_ticket_is_handed_back_even_once_autopilot_is_removed(
    github, autopilot
):
    github.issue(TICKET, labels=("ready-for-agent",))
    github.unlabel(SPEC, "autopilot")
    merged_pr(github)

    merged = autopilot("merged", str(PR))

    assert merged == "hand-back: #79 is still open after #105 merged"


def test_a_handed_back_pr_merged_while_another_ticket_is_built_waits(github, autopilot):
    """The Driver re-added autopilot, then merged the PR they took over."""
    github.label(TICKET, "ready-for-human")
    github.label(80, "autopilot:working")
    merged_pr(github)

    assert autopilot("merged", str(PR)) == "wait: #80 is still being built"


def test_a_handed_back_pr_merged_once_the_loop_stopped_stays_quiet(github, autopilot):
    """The hand-back already took autopilot off and said so on the Spec."""
    github.label(TICKET, "ready-for-human")
    github.unlabel(SPEC, "autopilot")
    merged_pr(github)

    merged = autopilot("merged", str(PR))

    assert merged == "already-stopped: #79 was handed back before #105 merged"


@pytest.mark.parametrize("branch", [f"feature/{TICKET}-pr-gets-gated", "claude/foo"])
def test_a_hand_written_pr_is_ignored(branch, github, autopilot):
    merged_pr(github, branch=branch)

    assert (
        autopilot("merged", str(PR)) == f"ignore: #105 isn't an Autopilot PR: {branch}"
    )


def test_a_pr_closed_without_merging_is_ignored(github, autopilot):
    merged_pr(github, merged=False)

    assert autopilot("merged", str(PR)) == "ignore: #105 wasn't merged"
