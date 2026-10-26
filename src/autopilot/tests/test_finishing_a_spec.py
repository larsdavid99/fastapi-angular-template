"""Seam 1: the merged PRs listed on a Spec once its last Ticket merged."""

import pytest

SPEC = 66


@pytest.fixture(autouse=True)
def spec(github):
    github.issue(SPEC, title="Autopilot", labels=("ready-for-agent", "autopilot"))


def test_each_ticket_is_listed_with_the_pr_that_merged_it(github, autopilot):
    github.issue(78, title="Labelling a Spec builds a Ticket", state="closed")
    github.issue(79, title="A PR gets gated", state="closed")
    github.closed_by(78, 99)
    github.closed_by(79, 103)
    github.sub_issues(SPEC, 78, 79)

    assert autopilot("summary", "66") == (
        "- #78 Labelling a Spec builds a Ticket: merged in #99\n"
        "- #79 A PR gets gated: merged in #103"
    )


def test_a_ticket_closed_without_a_merged_pr_says_so(github, autopilot):
    """Such as a ready-for-human setup Ticket the Driver closed by hand."""
    github.issue(81, title="Rulesets and labels", state="closed")
    github.sub_issues(SPEC, 81)

    summary = autopilot("summary", "66")

    assert summary == "- #81 Rulesets and labels: closed without a merged PR"


def test_a_pr_closed_without_merging_isnt_listed(github, autopilot):
    github.issue(79, title="A PR gets gated", state="closed")
    github.closed_by(79, 100, merged=False)
    github.closed_by(79, 103)
    github.closed_by(79, 104)
    github.sub_issues(SPEC, 79)

    summary = autopilot("summary", "66")

    assert summary == "- #79 A PR gets gated: merged in #103, #104"


def test_a_merged_pr_that_only_mentions_the_ticket_isnt_listed(github, autopilot):
    github.issue(72, title="Drink of the night", state="closed")
    github.mentioned_by(72, 91, closes=69)
    github.closed_by(72, 106)
    github.sub_issues(SPEC, 72)

    summary = autopilot("summary", "66")

    assert summary == "- #72 Drink of the night: merged in #106"


def test_a_ticket_still_open_says_so(github, autopilot):
    github.issue(84, title="Canary Spec")
    github.sub_issues(SPEC, 84)

    assert autopilot("summary", "66") == "- #84 Canary Spec: still open"
