"""What Claude Code tells a hook about the moment it runs at."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

BEFORE_COMMAND = "PreToolUse"
STOP = "Stop"


@dataclass(frozen=True)
class HookInput:
    event: str
    transcript_path: str
    cwd: str
    command: str
    """The shell command about to run, or empty when it isn't one."""
    stop_hook_active: bool
    """The agent is already carrying on because a Stop hook sent it back."""

    @classmethod
    def from_json(cls, hook: dict[str, Any]) -> HookInput:
        tool_input = hook.get("tool_input") or {}
        return cls(
            event=hook["hook_event_name"],
            transcript_path=hook["transcript_path"],
            cwd=hook["cwd"],
            command=str(tool_input.get("command", "")),
            stop_hook_active=bool(hook.get("stop_hook_active")),
        )
