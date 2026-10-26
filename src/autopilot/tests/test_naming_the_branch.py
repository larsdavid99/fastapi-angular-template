"""Seam 1: the `claude/<type>/<n>-<slug>` branch a Ticket is built on.

The agent names the paths it expects to touch; the command picks the type.
"""


def test_a_ticket_that_changes_the_app_is_a_feature(github, autopilot):
    github.issue(69, title="A Log records its Product")

    branch = autopilot("branch", "69", "src/backend/logic/log_logic.py")

    assert branch == "claude/feature/69-log-records-product"


def test_a_ticket_labelled_bug_is_a_fix(github, autopilot):
    github.issue(41, title="Undo drops the wrong Tally", labels=("bug",))

    branch = autopilot("branch", "41", "src/backend/logic/correction_logic.py")

    assert branch == "claude/fix/41-undo-drops-wrong-tally"


def test_a_ticket_labelled_documentation_is_docs(github, autopilot):
    github.issue(50, title="Explain the Pace nudge", labels=("documentation",))

    branch = autopilot("branch", "50", "src/backend/logic/pace_nudge_logic.py")

    assert branch == "claude/docs/50-explain-pace-nudge"


def test_a_ticket_that_touches_only_docs_is_docs(github, autopilot):
    github.issue(76, title="Record the spike's findings in ADR-0011")

    branch = autopilot(
        "branch", "76", "docs/adr/0011-autopilot-on-cloud-routines.md", "README.md"
    )

    assert branch == "claude/docs/76-record-spikes-findings-adr-0011"


def test_a_ticket_that_touches_only_github_config_is_ci(github, autopilot):
    github.issue(77, title="CI enforces black, flake8, mypy and a valid diagram")

    branch = autopilot("branch", "77", ".github/workflows/ci.yml")

    assert branch == "claude/ci/77-ci-enforces-black-flake8-mypy"


def test_a_ticket_that_touches_only_tooling_is_a_chore(github, autopilot):
    github.issue(92, title="Enable the mattpocock plugin through Claude settings")

    branch = autopilot("branch", "92", ".claude/settings.json", "README.md")

    assert branch == "claude/chore/92-enable-mattpocock-plugin-through-claude"
