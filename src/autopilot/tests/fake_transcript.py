"""A Claude Code session transcript, built up the way the agent's run went.

Written as the JSONL Claude Code keeps: one entry per line, the prompt as a user
message, tool calls as the assistant's `tool_use` blocks and their outcomes as
the user's `tool_result` blocks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FakeTranscript:
    def __init__(self, path: Path):
        self.path = path
        self._entries: list[dict[str, Any]] = []

    def prompt(self, text: str) -> FakeTranscript:
        self._entries.append({"type": "user", "message": _user(text)})
        return self

    def skill(self, name: str, sub_agent: bool = False) -> FakeTranscript:
        return self._tool("Skill", {"skill": name}, sub_agent=sub_agent)

    def bash(self, command: str, failed: bool = False) -> FakeTranscript:
        return self._tool("Bash", {"command": command}, failed=failed)

    def compaction(self, summary: str) -> FakeTranscript:
        """Claude Code's summary of the conversation so far, when it compacts it."""
        self._entries.append({"type": "system", "subtype": "compact_boundary"})
        self._entries.append(
            {
                "type": "user",
                "message": {"role": "user", "content": summary},
                "isCompactSummary": True,
                "isVisibleInTranscriptOnly": True,
            }
        )
        return self

    def local_command(self, name: str) -> FakeTranscript:
        """A command run in Claude Code itself, such as `/clear`, as it records it."""
        caveat = (
            "<local-command-caveat>The command below was run directly in Claude"
            " Code, not sent to you as a request.</local-command-caveat>"
        )
        record = (
            f"<command-name>{name}</command-name>\n"
            f"<command-message>{name.lstrip('/')}</command-message>\n"
            "<command-args></command-args>"
        )
        self._entries.append(
            {
                "type": "user",
                "message": {"role": "user", "content": caveat},
                "isMeta": True,
            }
        )
        self._entries.append(
            {"type": "user", "message": {"role": "user", "content": record}}
        )
        return self

    def sub_agent_prompt(self, text: str) -> FakeTranscript:
        """A sub-agent's brief, which the parent's transcript may hold too."""
        entry = {"type": "user", "message": _user(text), "isSidechain": True}
        self._entries.append(entry)
        return self

    def write(self) -> str:
        lines = [json.dumps(entry) for entry in self._entries]
        self.path.write_text("\n".join(lines) + "\n")
        return str(self.path)

    def _tool(
        self,
        name: str,
        tool_input: dict[str, str],
        failed: bool = False,
        sub_agent: bool = False,
    ) -> FakeTranscript:
        tool_use_id = f"toolu_{len(self._entries)}"
        self._entries.append(
            {
                "type": "assistant",
                "isSidechain": sub_agent,
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_use_id,
                            "name": name,
                            "input": tool_input,
                        }
                    ],
                },
            }
        )
        result: dict[str, Any] = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": "",
        }
        if failed:
            result["is_error"] = True
        self._entries.append(
            {
                "type": "user",
                "isSidechain": sub_agent,
                "message": {"role": "user", "content": [result]},
            }
        )
        return self


def _user(text: str) -> dict[str, Any]:
    return {"role": "user", "content": [{"type": "text", "text": text}]}
