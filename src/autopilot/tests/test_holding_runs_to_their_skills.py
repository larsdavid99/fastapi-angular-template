"""The skills hook's seam: hook input and the session's transcript in, decision out.

Before a command runs, the hook refuses an Autopilot run's PR, or a Review
run's first comment, until the skills its instructions name have run. When the
run stops, it sends back one that got past that without them.
"""

from __future__ import annotations

from typing import Any

IMPLEMENT = (
    "Follow docs/agents/autopilot-implement.md. Your input is either the Spec"
    " number in the fire payload, or the pull request whose merge triggered this run."
)
REVIEW = (
    "Follow docs/agents/autopilot-review.md for the pull request that triggered"
    " this run."
)
OPEN_PR = (
    'gh api "repos/{owner}/{repo}/pulls" -f base=main'
    ' -f head=claude/docs/121-readme -f title="The README covers Autopilot"'
    " -F body=@/tmp/body.md -q .number"
)
POST_REPORT = (
    'gh api "repos/{owner}/{repo}/issues/122/comments" -F body=@/tmp/report.md'
)
CODE_REVIEW = "mattpocock-skills:code-review"
PR = "mattpocock-skills:pr"
TDD = "mattpocock-skills:tdd"
DOCS = ["README.md", "docs/agents/autopilot-review.md"]
SRC = ["README.md", "src/backend/logic/log_logic.py"]


def denied(decision: dict[str, Any] | None) -> str:
    """The reason a command was refused, failing the test if it wasn't."""
    assert decision is not None
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
    reason: str = decision["hookSpecificOutput"]["permissionDecisionReason"]
    return reason


def blocked(decision: dict[str, Any] | None) -> str:
    """The reason a stop was blocked, failing the test if it wasn't."""
    assert decision is not None
    assert decision["decision"] == "block"
    reason: str = decision["reason"]
    return reason


# Before the PR opens


def test_opening_a_pr_without_code_review_is_refused(transcript, before_command):
    transcript.prompt(IMPLEMENT).skill(PR)

    reason = denied(before_command(OPEN_PR, changed=DOCS))

    assert f"/{CODE_REVIEW} origin/main" in reason
    assert f"/{PR}" not in reason


def test_opening_a_pr_without_the_pr_skill_is_refused(transcript, before_command):
    transcript.prompt(IMPLEMENT).skill(CODE_REVIEW)

    reason = denied(before_command(OPEN_PR, changed=DOCS))

    assert f"/{PR}" in reason
    assert f"/{CODE_REVIEW}" not in reason


def test_opening_a_pr_that_changes_src_without_tdd_is_refused_to_hand_back(
    transcript, before_command
):
    transcript.prompt(IMPLEMENT).skill(CODE_REVIEW).skill(PR)

    reason = denied(before_command(OPEN_PR, changed=SRC))

    assert f"/{TDD}" in reason
    assert "hand the Ticket back" in reason


def test_opening_a_pr_after_every_skill_goes_ahead(transcript, before_command):
    transcript.prompt(IMPLEMENT).skill(TDD).skill(CODE_REVIEW).skill(PR)

    assert before_command(OPEN_PR, changed=SRC) is None


def test_a_docs_only_pr_needs_no_tdd(transcript, before_command):
    transcript.prompt(IMPLEMENT).skill(CODE_REVIEW).skill(PR)

    assert before_command(OPEN_PR, changed=DOCS) is None


def test_a_pr_git_cant_read_the_changes_of_needs_no_tdd(transcript, before_command):
    transcript.prompt(IMPLEMENT).skill(CODE_REVIEW).skill(PR)

    assert before_command(OPEN_PR, changed=None) is None


def test_commands_that_open_no_pr_go_ahead(transcript, before_command):
    transcript.prompt(IMPLEMENT)

    read_pr = 'gh api "repos/{owner}/{repo}/pulls/105" -q .head.ref'
    pause = 'gh api "repos/{owner}/{repo}/issues/66/comments" -f body="Paused."'
    assert before_command(read_pr, changed=SRC) is None
    assert before_command("git push -u origin x", changed=SRC) is None
    assert before_command(pause, changed=SRC) is None


def test_a_local_run_on_gh_pr_create_is_held_to_the_skills_too(
    transcript, before_command
):
    transcript.prompt("Follow docs/agents/autopilot-implement.md for Spec #66")

    denied(before_command("git push -u origin x && gh pr create --fill"))


def test_a_command_that_only_names_the_pr_command_goes_ahead(
    transcript, before_command
):
    transcript.prompt(IMPLEMENT)

    file_issue = (
        'gh issue create --title "The hook misfired" --body "The run ran'
        " gh pr create --fill; then gh api repos/{owner}/{repo}/pulls -f base=main"
        ' && gh pr comment 5 --body hi"'
    )
    assert before_command(file_issue, changed=SRC) is None


def test_a_pr_opened_inside_a_command_substitution_is_held_to_the_skills(
    transcript, before_command
):
    transcript.prompt(IMPLEMENT)

    denied(before_command('url="$(gh pr create --fill)" && echo "$url"'))


def test_a_pr_opened_after_a_keyword_or_a_prefix_is_held_to_the_skills(
    transcript, before_command
):
    transcript.prompt(IMPLEMENT)

    denied(before_command("if gh pr create --fill; then echo opened; fi"))
    denied(before_command("! gh pr create --fill"))
    denied(before_command("{ gh pr create --fill; }"))
    denied(before_command("env GH_TOKEN=x gh pr create --fill"))
    denied(before_command("time gh pr create --fill"))
    denied(before_command("n=$((1<<2))\ngh pr create --fill"))
    denied(before_command('cat <<< "hi"\ngh pr create --fill'))
    denied(
        before_command(
            "gh api https://api.github.com/repos/o/r/pulls -f base=main -f head=x"
        )
    )


def test_a_review_run_may_not_comment_before_code_review(transcript, before_command):
    transcript.prompt(REVIEW).bash("git diff origin/main...HEAD")

    reason = denied(before_command(POST_REPORT))

    assert f"/{CODE_REVIEW} origin/main" in reason


def test_a_review_run_comments_once_code_review_ran(transcript, before_command):
    transcript.prompt(REVIEW).skill(CODE_REVIEW)

    assert before_command(POST_REPORT) is None


def test_code_review_in_a_sub_agent_isnt_the_review(transcript, before_command):
    transcript.prompt(REVIEW).skill(CODE_REVIEW, sub_agent=True)

    denied(before_command(POST_REPORT))


def test_a_session_not_following_autopilot_goes_ahead(transcript, before_command):
    transcript.prompt("Open a PR for the README fix")

    assert before_command(OPEN_PR, changed=SRC) is None


def test_a_sub_agents_brief_doesnt_make_the_session_a_run(transcript, before_command):
    transcript.prompt("Tidy the README").sub_agent_prompt(
        "Follow docs/agents/autopilot-implement.md for Spec #66"
    )

    assert before_command(OPEN_PR, changed=SRC) is None


def test_pasting_the_routines_prompt_later_doesnt_make_the_session_a_run(
    transcript, before_command
):
    transcript.prompt("Why did the Implement routine stop?").prompt(
        f"Here's the routine as I set it up:\n\n{IMPLEMENT}"
    )

    assert before_command(OPEN_PR, changed=SRC) is None


def test_a_compaction_summary_quoting_the_routines_prompt_doesnt_make_a_run(
    transcript, before_command
):
    transcript.prompt("Walk me through setting up Autopilot").compaction(
        "This session is being continued from a previous conversation.\n\n"
        f"Summary:\n- The Implement routine's prompt is `{IMPLEMENT}`"
    )

    assert before_command(OPEN_PR, changed=SRC) is None


def test_a_local_run_after_clearing_the_session_is_still_a_run(
    transcript, before_command
):
    transcript.local_command("/clear").prompt(
        "Follow docs/agents/autopilot-implement.md for Spec #66"
    )

    denied(before_command("gh pr create --fill"))


# When the run stops


def test_a_run_that_opened_a_pr_without_the_pr_skill_is_blocked(transcript, stop_hook):
    transcript.prompt(IMPLEMENT).skill(CODE_REVIEW).bash(OPEN_PR)

    reason = blocked(stop_hook(changed=DOCS))

    assert f"/{PR}" in reason
    assert f"/{CODE_REVIEW}" not in reason


def test_a_run_that_opened_a_pr_without_code_review_is_blocked(transcript, stop_hook):
    transcript.prompt(IMPLEMENT).skill(PR).bash(OPEN_PR)

    reason = blocked(stop_hook(changed=DOCS))

    assert f"/{CODE_REVIEW} origin/main" in reason
    assert f"/{PR}" not in reason


def test_a_run_that_opened_a_pr_changing_src_without_tdd_is_blocked_to_hand_back(
    transcript, stop_hook
):
    transcript.prompt(IMPLEMENT).skill(CODE_REVIEW).skill(PR).bash(OPEN_PR)

    reason = blocked(stop_hook(changed=SRC))

    assert f"/{TDD}" in reason
    assert "hand the Ticket back" in reason


def test_a_run_that_used_every_skill_is_let_stop(transcript, stop_hook):
    transcript.prompt(IMPLEMENT).skill(TDD).skill(CODE_REVIEW).skill(PR).bash(OPEN_PR)

    assert stop_hook(changed=SRC) is None


def test_a_run_that_opened_nothing_is_let_stop(transcript, stop_hook):
    transcript.prompt(IMPLEMENT).bash("python3 src/autopilot/autopilot.py next 66")

    assert stop_hook(changed=SRC) is None


def test_a_run_that_filed_an_issue_naming_the_pr_command_is_let_stop(
    transcript, stop_hook
):
    file_issue = (
        "cat > /tmp/issue.md <<'EOF'\n"
        "## What was seen\n"
        "The run opened its PR with\n"
        f"{OPEN_PR}\n"
        "and then gh pr create --fill\n"
        "EOF\n"
        'gh issue create --title "The hook misfired" --body-file /tmp/issue.md'
    )
    transcript.prompt(IMPLEMENT).bash(file_issue)

    assert stop_hook(changed=SRC) is None


def test_a_pr_that_failed_to_open_is_not_opened(transcript, stop_hook):
    transcript.prompt(IMPLEMENT).bash(OPEN_PR, failed=True)

    assert stop_hook(changed=SRC) is None


def test_a_review_run_that_reviewed_without_code_review_is_blocked(
    transcript, stop_hook
):
    transcript.prompt(REVIEW).bash("git diff origin/main...HEAD").bash(POST_REPORT)

    reason = blocked(stop_hook())

    assert f"/{CODE_REVIEW} origin/main" in reason


def test_a_late_review_takes_the_pr_off_the_merge_workflow(transcript, stop_hook):
    transcript.prompt(REVIEW).bash(POST_REPORT)

    reason = blocked(stop_hook())

    assert '"repos/{owner}/{repo}/issues/<pr>/labels/autopilot:merge"' in reason
    assert "ccr/auto_merge" not in reason


def test_a_review_run_that_used_code_review_is_let_stop(transcript, stop_hook):
    transcript.prompt(REVIEW).skill(CODE_REVIEW).bash(POST_REPORT)

    assert stop_hook() is None


def test_a_review_run_that_reviewed_nothing_is_let_stop(transcript, stop_hook):
    transcript.prompt(REVIEW).bash('gh api "repos/{owner}/{repo}/pulls/130"')

    assert stop_hook() is None


def test_a_session_not_following_autopilot_is_let_stop(transcript, stop_hook):
    transcript.prompt("Open a PR for the README fix").bash(OPEN_PR)

    assert stop_hook(changed=SRC) is None


def test_a_run_already_continuing_because_of_the_hook_is_let_stop(
    transcript, stop_hook
):
    transcript.prompt(IMPLEMENT).bash(OPEN_PR)

    assert stop_hook(changed=SRC, stop_hook_active=True) is None
