"""The hook that holds Autopilot's runs to their skills, whatever the change's size.

Claude Code runs it (`.claude/settings.json`) with the moment's details as JSON
on stdin, and it reads the session's transcript for what the run has done:

- Before a shell command, it refuses an Implement run's PR until `tdd` (for a
  change to `src/`), `code-review` and `pr` have run, and a Review run's first
  PR comment until `code-review` has.
- When the run stops, it sends back one that opened or reviewed a PR without
  them anyway.

It judges only Autopilot's runs: sessions whose first prompt starts with
`Follow docs/agents/autopilot-implement.md` (an Implement run) or `Follow
docs/agents/autopilot-review.md` (a Review run), as the routines' prompts and
the Driver's local ones do. A later prompt quoting one, such as pasted set-up
text or the summary Claude Code writes when it compacts, doesn't make a run.
Any other session goes on as it would. And only a command that runs `gh pr` or
`gh api` counts, not a quoted argument or heredoc that names one (`shell.py`).

    python3 src/autopilot/skills_hook.py < <hook input>
"""

from __future__ import annotations

import itertools
import json
import os
import re
import sys
from typing import Any, Callable, TextIO

import git
import shell
from hook_input import BEFORE_COMMAND, STOP, HookInput
from labels import MERGE
from transcript import Transcript

CODE_REVIEW = "mattpocock-skills:code-review"
PR = "mattpocock-skills:pr"
TDD = "mattpocock-skills:tdd"

ChangedPaths = Callable[[str], "list[str] | None"]
"""What the branch checked out in this directory changes, or None if git can't tell."""

# The routines' prompts, and the Driver's local ones, start with which file to
# follow. A later prompt may quote them without the session being a run.
_IMPLEMENT_RUN = re.compile(r"\s*follow\s+docs/agents/autopilot-implement\.md\b", re.I)
_REVIEW_RUN = re.compile(r"\s*follow\s+docs/agents/autopilot-review\.md\b", re.I)

_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")
# What may come before a command's name: the shell's keywords, and commands
# that run the command after them.
_BEFORE_COMMAND = {"!", "{", "if", "then", "elif", "else", "while", "until", "do"}
_BEFORE_COMMAND |= {"time", "env", "command", "exec", "nohup"}
_REPO = r"(?:https://[^/]+)?/?repos/[^/]+/[^/]+"
_PULLS = re.compile(_REPO + r"/pulls(?:\?.*)?")
_COMMENTS = re.compile(_REPO + r"/issues/[^/]+/comments(?:\?.*)?")
_LONG_FIELDS = ("--field", "--raw-field", "--input")
# GitHub refuses these GraphQL commands in a routine, but a local run may use them.
_GH_PR_CREATE = {("pr", "create")}
_GH_PR_COMMENT = {("pr", "comment"), ("pr", "review")}

_RUN_CODE_REVIEW = (
    f"run `/{CODE_REVIEW} origin/main` in this session, fix what it finds and run"
    " the checks in step 6 again"
)
_RUN_PR = f"write the PR's title and body with `/{PR}`"

_REVIEW_FIRST = (
    f"Run `/{CODE_REVIEW} origin/main` in this session before you comment on the"
    " PR, as step 2 of docs/agents/autopilot-review.md says. A review written"
    " without it isn't a review, however small the PR."
)

# By the time a Review run stops, the gate has acted. A second round of fixes
# would break the one-round rule, so the late report waits for a person.
_REVIEWED_WITHOUT_CODE_REVIEW = (
    f"You reviewed this PR without `/{CODE_REVIEW}`, and a review written without"
    " it isn't a review (docs/agents/autopilot-review.md). Before you stop, run"
    f" `/{CODE_REVIEW} origin/main` in this session and post its report as a PR"
    f" comment, numbered as in step 2. If the PR is still open, take `{MERGE}` off"
    ' it (`gh api -X DELETE "repos/{owner}/{repo}/issues/<pr>/labels/'
    f"{MERGE}\"`; a refusal because it isn't on is fine), assign the Driver,"
    f" and comment `This review ran late, without /{CODE_REVIEW}, so the PR waits for the"
    " Driver.` Don't start the fixer again."
)


def main(stdin: TextIO, changed_paths: ChangedPaths) -> None:
    hook = HookInput.from_json(json.load(stdin))
    reason = decide(hook, changed_paths)
    if reason:
        print(json.dumps(_refusal(hook.event, reason)))


def decide(hook: HookInput, changed_paths: ChangedPaths) -> str | None:
    """Why the command or the stop can't go ahead, or None when it can."""
    if hook.event == BEFORE_COMMAND:
        return _before_command(hook, changed_paths)
    if hook.event == STOP and not hook.stop_hook_active:
        return _before_stop(hook, changed_paths)
    return None


def _before_command(hook: HookInput, changed_paths: ChangedPaths) -> str | None:
    transcript = Transcript.read(hook.transcript_path)
    skills = transcript.skills()
    if _follows(transcript, _IMPLEMENT_RUN) and _opens_pr(hook.command):
        if _built_without_tdd(skills, lambda: changed_paths(hook.cwd)):
            return _hand_back_untested("don't open the PR: push the branch")
        steps = _missing_steps(skills)
        return f"Before you open the PR, {steps}. Then open it." if steps else None
    if _follows(transcript, _REVIEW_RUN) and _comments_on_pr(hook.command):
        return None if CODE_REVIEW in skills else _REVIEW_FIRST
    return None


def _before_stop(hook: HookInput, changed_paths: ChangedPaths) -> str | None:
    """The backstop for a PR that got past the check before its command."""
    transcript = Transcript.read(hook.transcript_path)
    skills = transcript.skills()
    commands = transcript.commands()
    if _follows(transcript, _IMPLEMENT_RUN) and any(map(_opens_pr, commands)):
        return _opened_without_skills(skills, lambda: changed_paths(hook.cwd))
    if _follows(transcript, _REVIEW_RUN) and any(map(_comments_on_pr, commands)):
        return None if CODE_REVIEW in skills else _REVIEWED_WITHOUT_CODE_REVIEW
    return None


def _opened_without_skills(
    skills: set[str], changed_paths: Callable[[], list[str] | None]
) -> str | None:
    if _built_without_tdd(skills, changed_paths):
        # Closing the PR stops the Review routine auto-merging it.
        return _hand_back_untested(
            'close the PR (`gh api -X PATCH "repos/{owner}/{repo}/pulls/<pr>"'
            " -f state=closed`)"
        )
    steps = _missing_steps(skills)
    if not steps:
        return None
    return (
        "You opened a PR without the skills docs/agents/autopilot-implement.md"
        f" names. Before you stop, {steps}, push, and update the PR with"
        ' `gh api -X PATCH "repos/{owner}/{repo}/pulls/<pr>" -f title="<title>"'
        " -F body=@<file>`."
    )


def _hand_back_untested(what_to_do_with_the_pr: str) -> str:
    """Tests can't be written first once the code is built, so the Ticket goes back."""
    return (
        f"This Ticket changes src/, and it was built without `/{TDD}`, which"
        " docs/agents/autopilot-implement.md asks for on every Ticket that changes"
        " src/, however small. Tests can't be written first after the fact, so"
        f" {what_to_do_with_the_pr} and hand the Ticket back as in its Handing a"
        f" Ticket back, with `built without /{TDD}; its branch is <branch>` as what"
        " failed. Then stop."
    )


def _follows(transcript: Transcript, instructions: re.Pattern[str]) -> bool:
    return any(instructions.match(prompt) for prompt in transcript.prompts()[:1])


def _built_without_tdd(
    skills: set[str], changed_paths: Callable[[], list[str] | None]
) -> bool:
    """When git can't tell, the Ticket may be docs only, so it isn't held back."""
    if TDD in skills:
        return False
    return any(path.startswith("src/") for path in changed_paths() or [])


def _missing_steps(skills: set[str]) -> str:
    """Review first: its fixes change what the PR body describes."""
    steps = []
    if CODE_REVIEW not in skills:
        steps.append(_RUN_CODE_REVIEW)
    if PR not in skills:
        steps.append(_RUN_PR)
    return "; then ".join(steps)


def _opens_pr(command: str) -> bool:
    return _runs(command, _GH_PR_CREATE, _PULLS)


def _comments_on_pr(command: str) -> bool:
    return _runs(command, _GH_PR_COMMENT, _COMMENTS)


def _runs(line: str, gh_pr: set[tuple[str, str]], endpoint: re.Pattern[str]) -> bool:
    """Whether any command the line runs is one of those `gh pr` ones, or a POST
    to that REST endpoint. Text that names one, quoted or in a heredoc, isn't."""
    for words in shell.simple_commands(line):
        arguments = _gh_arguments(words)
        if tuple(arguments[:2]) in gh_pr or _posts_to(arguments, endpoint):
            return True
    return False


def _gh_arguments(words: list[str]) -> list[str]:
    """What `gh` was given, or [] for another command."""
    words = list(itertools.dropwhile(_comes_before_command, words))
    if words and os.path.basename(words[0]) == "gh":
        return words[1:]
    return []


def _comes_before_command(word: str) -> bool:
    return word in _BEFORE_COMMAND or bool(_ASSIGNMENT.match(word))


def _posts_to(arguments: list[str], endpoint: re.Pattern[str]) -> bool:
    """`gh api` sends a POST when it's given fields, unless told another method."""
    if arguments[:1] != ["api"] or not any(map(endpoint.fullmatch, arguments)):
        return False
    method = _method(arguments)
    if method:
        return method.upper() == "POST"
    return any(_is_field(argument) for argument in arguments)


def _method(arguments: list[str]) -> str | None:
    for flag, value in zip(arguments, arguments[1:] + [""]):
        if flag in ("-X", "--method"):
            return value
        if flag.startswith("--method="):
            return flag[len("--method=") :]
        if flag.startswith("-X"):
            return flag[2:]
    return None


def _is_field(argument: str) -> bool:
    """`-f key=value`, `--field=key=value` or `-fkey=value`."""
    return argument[:2] in ("-f", "-F") or argument.split("=")[0] in _LONG_FIELDS


def _refusal(event: str, reason: str) -> dict[str, Any]:
    """In the shape Claude Code reads for that event."""
    if event == BEFORE_COMMAND:
        return {
            "hookSpecificOutput": {
                "hookEventName": BEFORE_COMMAND,
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    return {"decision": "block", "reason": reason}


if __name__ == "__main__":
    main(sys.stdin, git.changed_paths)
