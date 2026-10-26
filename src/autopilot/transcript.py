"""A Claude Code session's transcript: what the person asked and what the agent ran.

Only the session's own turns count. A sub-agent's turns are its own: the fixer's
brief, say, isn't the session's prompt.
"""

from __future__ import annotations

import json
from typing import Any, Iterator

# How Claude Code records a command run in it, and what that command printed.
_LOCAL_COMMAND = ("<command-name>", "<local-command-")


class Transcript:
    def __init__(self, entries: list[dict[str, Any]]):
        self._entries = [e for e in entries if not e.get("isSidechain")]

    @classmethod
    def read(cls, path: str) -> Transcript:
        """A line that isn't JSON is skipped, and a missing file is an empty one."""
        try:
            with open(path, encoding="utf-8") as lines:
                return cls([entry for entry in map(_parsed, lines) if entry])
        except OSError:
            return cls([])

    def prompts(self) -> list[str]:
        """What the person typed, in order. Claude Code's own insertions, such as
        its record of a command like `/clear`, aren't."""
        typed = map(_typed_text, self._entries)
        return [text for text in typed if text is not None]

    def skills(self) -> set[str]:
        """Every skill the agent called through the Skill tool."""
        return {
            str(tool["input"].get("skill"))
            for tool in self._tool_uses()
            if tool.get("name") == "Skill"
        }

    def commands(self) -> list[str]:
        """The shell commands the agent ran, leaving out those that failed."""
        failed = self._failed_tool_use_ids()
        return [
            str(tool["input"].get("command", ""))
            for tool in self._tool_uses()
            if tool.get("name") == "Bash" and tool.get("id") not in failed
        ]

    def _tool_uses(self) -> Iterator[dict[str, Any]]:
        for entry in self._entries:
            if entry.get("type") == "assistant":
                for block in _blocks(entry):
                    if block.get("type") == "tool_use":
                        yield block

    def _failed_tool_use_ids(self) -> set[str]:
        return {
            str(block.get("tool_use_id"))
            for entry in self._entries
            if entry.get("type") == "user"
            for block in _blocks(entry)
            if block.get("type") == "tool_result" and block.get("is_error")
        }


def _parsed(line: str) -> dict[str, Any] | None:
    try:
        entry = json.loads(line)
    except ValueError:
        return None
    return entry if isinstance(entry, dict) else None


def _typed_text(entry: dict[str, Any]) -> str | None:
    """The entry's text if the person typed it, or None."""
    if entry.get("type") != "user" or entry.get("isMeta"):
        return None
    blocks = _blocks(entry)
    if any(b.get("type") == "tool_result" for b in blocks):
        return None
    text = "".join(b["text"] for b in blocks if b.get("type") == "text")
    return None if text.startswith(_LOCAL_COMMAND) else text


def _blocks(entry: dict[str, Any]) -> list[dict[str, Any]]:
    """A message's content blocks. Plain-string content is one text block."""
    content = entry.get("message", {}).get("content")
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if isinstance(content, list):
        return [block for block in content if isinstance(block, dict)]
    return []
