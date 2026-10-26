from __future__ import annotations

import io
import json
from typing import Any, Callable

import pytest

from autopilot import main
from skills_hook import main as skills_hook_main
from tests.fake_github import FakeGitHub
from tests.fake_transcript import FakeTranscript

HookRun = Callable[..., "dict[str, Any] | None"]


@pytest.fixture
def github() -> FakeGitHub:
    return FakeGitHub()


@pytest.fixture
def slept() -> list[float]:
    """The seconds the command waited, wait by wait, without waiting."""
    return []


@pytest.fixture
def autopilot(github, slept, capsys) -> Callable[..., str]:
    """Runs the command against the fake and returns what it printed."""

    def run(*argv: str) -> str:
        main(list(argv), gh=github, sleep=slept.append)
        printed: str = capsys.readouterr().out
        return printed.strip()

    return run


@pytest.fixture
def transcript(tmp_path) -> FakeTranscript:
    return FakeTranscript(tmp_path / "session.jsonl")


@pytest.fixture
def skills_hook(transcript, tmp_path, capsys) -> HookRun:
    """Runs the hook as Claude Code does, with the transcript written so far.

    Returns the decision it printed, or None when it lets the agent go on.
    `changed` is what `git diff origin/main...HEAD --name-only` lists, or None
    when git can't tell.
    """

    def run(
        event: dict[str, Any], changed: list[str] | None = None
    ) -> dict[str, Any] | None:
        hook_input = {
            "session_id": "session",
            "transcript_path": transcript.write(),
            "cwd": str(tmp_path),
            **event,
        }
        skills_hook_main(io.StringIO(json.dumps(hook_input)), lambda cwd: changed)
        printed = capsys.readouterr().out.strip()
        decision: dict[str, Any] | None = json.loads(printed) if printed else None
        return decision

    return run


@pytest.fixture
def before_command(skills_hook: HookRun) -> HookRun:
    """The agent is about to run a shell command."""

    def run(command: str, changed: list[str] | None = None) -> dict[str, Any] | None:
        event = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }
        return skills_hook(event, changed)

    return run


@pytest.fixture
def stop_hook(skills_hook: HookRun) -> HookRun:
    """The agent is about to stop."""

    def run(
        changed: list[str] | None = None, stop_hook_active: bool = False
    ) -> dict[str, Any] | None:
        event = {"hook_event_name": "Stop", "stop_hook_active": stop_hook_active}
        return skills_hook(event, changed)

    return run
