"""Seam 1: what happens to an Autopilot PR once it's reviewed, fixed and CI is done."""

from __future__ import annotations

import pytest

from tests.fake_github import FakeGitHub

SPEC = 66
TICKET = 79
PR = 102
APP_CODE = "src/backend/logic/tally_logic.py"
REQUIRED = ("pytest", "black", "flake8", "mypy")


@pytest.fixture(autouse=True)
def ticket(github):
    """A Ticket of a Spec on autopilot, being built."""
    github.issue(SPEC, title="Autopilot", labels=("ready-for-agent", "autopilot"))
    github.issue(TICKET, labels=("ready-for-agent", "autopilot:working"))
    github.sub_issues(SPEC, TICKET)
    github.required_checks("main", *REQUIRED)


def autopilot_pr(
    github: FakeGitHub, *paths: str, mergeable: bool | None = True
) -> None:
    github.pull_request(
        PR,
        branch=f"claude/feature/{TICKET}-pr-gets-gated",
        paths=paths,
        mergeable=mergeable,
    )


def ci_passes(github: FakeGitHub) -> None:
    for check in REQUIRED:
        github.check_run(PR, check)


def test_a_green_pr_of_an_auto_merge_spec_merges_itself(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    ci_passes(github)

    assert autopilot("gate", str(PR)) == "auto-merge"


def test_a_green_pr_waits_for_the_driver_without_auto_merge(github, autopilot):
    autopilot_pr(github, APP_CODE)
    ci_passes(github)

    gate = autopilot("gate", str(PR))

    assert gate == "request-driver: #66 isn't labelled autopilot:auto-merge"


def test_a_pr_with_a_failing_check_is_handed_back(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    github.check_run(PR, "pytest")
    github.check_run(PR, "mypy", conclusion="failure")
    github.check_run(PR, "black", conclusion="timed_out")

    assert autopilot("gate", str(PR)) == "hand-back: CI is red: black, mypy"


def test_a_pr_whose_checks_are_still_running_is_handed_back(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    github.check_run(PR, "mypy")
    github.check_run(PR, "pytest", conclusion=None, status="in_progress")

    assert autopilot("gate", str(PR)) == "hand-back: CI hasn't finished: pytest"


def test_a_pr_a_required_check_never_ran_on_is_handed_back(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    github.check_run(PR, "pytest")
    github.check_run(PR, "black")

    assert autopilot("gate", str(PR)) == "hand-back: CI didn't run: flake8, mypy"


def test_a_failing_check_main_doesnt_require_doesnt_hold_a_pr_back(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    ci_passes(github)
    github.check_run(PR, "some app's scan", conclusion="failure")

    assert autopilot("gate", str(PR)) == "auto-merge"


def test_a_pr_that_conflicts_with_main_is_handed_back(github, autopilot):
    """GitHub runs no CI on a conflicting PR, so the conflict is the reason."""
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE, mergeable=False)

    assert autopilot("gate", str(PR)) == "hand-back: conflicts with main"


def test_a_pr_github_hasnt_checked_for_conflicts_is_handed_back(github, autopilot):
    """Green checks can predate a conflict, so they don't prove there's none."""
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE, mergeable=None)
    ci_passes(github)

    gate = autopilot("gate", str(PR))

    assert gate == "hand-back: GitHub hasn't said whether it conflicts with main"


def test_without_required_checks_on_main_nothing_counts_as_green(github, autopilot):
    github.required_checks("main")
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    ci_passes(github)

    assert autopilot("gate", str(PR)) == "hand-back: main requires no CI checks"


def test_an_adr_change_waits_for_the_reviewer_even_with_auto_merge(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE, "docs/adr/0012-tallies-expire.md")
    ci_passes(github)

    gate = autopilot("gate", str(PR))

    assert gate == "request-reviewer: changes docs/adr/0012-tallies-expire.md"


def test_a_glossary_change_waits_for_the_reviewer(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, "GLOSSARY.md")
    ci_passes(github)

    assert autopilot("gate", str(PR)) == "request-reviewer: changes GLOSSARY.md"


def test_moving_an_adr_out_of_the_adr_folder_waits_for_the_reviewer(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github)
    github.renamed_file(PR, "docs/adr/0008-opt-out-as-keywords.md", "docs/opt-out.md")
    ci_passes(github)

    gate = autopilot("gate", str(PR))

    assert gate == "request-reviewer: changes docs/adr/0008-opt-out-as-keywords.md"


def test_a_spec_finding_the_fixer_couldnt_resolve_waits_for_the_reviewer(
    github, autopilot
):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    ci_passes(github)

    gate = autopilot("gate", str(PR), "--unresolved-spec-finding")

    assert gate == "request-reviewer: the fixer couldn't resolve a Spec finding"


@pytest.mark.parametrize(
    "machinery",
    [
        ".github/workflows/ci.yml",
        ".claude/settings.json",
        "docs/agents/autopilot-review.md",
        "src/autopilot/gate.py",
    ],
)
def test_a_change_to_the_loops_machinery_waits_for_the_driver_even_with_auto_merge(
    machinery, github, autopilot
):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE, machinery)
    ci_passes(github)

    assert autopilot("gate", str(PR)) == f"request-driver: changes {machinery}"


def test_red_ci_beats_every_other_gate(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, "docs/adr/0012-tallies-expire.md", ".github/workflows/ci.yml")
    github.check_run(PR, "pytest", conclusion="failure")

    gate = autopilot("gate", str(PR), "--unresolved-spec-finding")

    assert gate == "hand-back: CI is red: pytest"


def test_the_reviewer_beats_the_driver(github, autopilot):
    autopilot_pr(github, "docs/adr/0012-tallies-expire.md", ".github/workflows/ci.yml")
    ci_passes(github)

    gate = autopilot("gate", str(PR), "--unresolved-spec-finding")

    assert gate == (
        "request-reviewer: changes docs/adr/0012-tallies-expire.md;"
        " the fixer couldn't resolve a Spec finding"
    )


def test_skipped_and_neutral_checks_dont_hold_a_pr_back(github, autopilot):
    github.label(SPEC, "autopilot:auto-merge")
    autopilot_pr(github, APP_CODE)
    github.check_run(PR, "pytest")
    github.check_run(PR, "black")
    github.check_run(PR, "flake8", conclusion="skipped")
    github.check_run(PR, "mypy", conclusion="neutral")

    assert autopilot("gate", str(PR)) == "auto-merge"


def test_a_hand_written_pr_has_no_gate(github, autopilot):
    github.pull_request(PR, branch=f"feature/{TICKET}-pr-gets-gated")

    with pytest.raises(SystemExit, match="#102 isn't an Autopilot PR"):
        autopilot("gate", str(PR))
