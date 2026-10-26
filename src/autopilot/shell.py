"""The commands a shell line runs, each as its words, the way the shell reads them.

Only as much of the shell as tells a command from text that names one: quotes,
escapes, comments, heredoc bodies, and the commands `$(…)`, backticks and
`(…)` run. A heredoc's body and a quoted argument are text, so a command named
there isn't run.
"""

from __future__ import annotations

from typing import NamedTuple, Union

_SEPARATORS = ";&|"
_REDIRECTS = "<>"
_DELIMITER_END = " \t\n;&|<>()"
_DROP_QUOTES = str.maketrans("", "", "'\"\\")


class _Command:
    """A command being read, ended by `closer`: `)` or a backtick, "" at the top."""

    def __init__(self, closer: str):
        self.closer = closer
        self.words: list[str] = []
        self.word: str | None = None


class _DoubleQuoted:
    """Inside double quotes, which `$(…)` and backticks still run commands in."""


class _Heredoc(NamedTuple):
    delimiter: str
    strips_tabs: bool


_Frame = Union[_Command, _DoubleQuoted]


def simple_commands(line: str) -> list[list[str]]:
    """Every command the line runs, in the order the reader finishes them."""
    return _Reader(line).read()


class _Reader:
    def __init__(self, line: str):
        self.line = line
        self.at = 0
        self.frames: list[_Frame] = [_Command("")]
        self.heredocs: list[_Heredoc] = []
        self.commands: list[list[str]] = []

    def read(self) -> list[list[str]]:
        while self.at < len(self.line):
            frame = self.frames[-1]
            if isinstance(frame, _Command):
                self._read_command(frame)
            else:
                self._read_double_quoted()
        for frame in reversed(self.frames):
            if isinstance(frame, _Command):
                self._end_command(frame)
        return self.commands

    def _read_command(self, command: _Command) -> None:
        char = self.line[self.at]
        if char == "\n":
            self._end_command(command)
            self.at += 1
            self._skip_heredoc_bodies()
        elif char == "#" and command.word is None:
            self.at = self._find_or_end("\n", self.at)
        elif char == "\\":
            self._read_escape(command, quoted=False)
        elif char == "'":
            self._read_single_quoted(command)
        elif self.line.startswith("<<<", self.at):
            self._append(command, "<<<")
            self.at += 3
        elif self.line.startswith("<<", self.at):
            self._read_heredoc(command)
        elif char == command.closer:
            self._end_command(command)
            self.frames.pop()
            self.at += 1
        elif not self._read_substitution(command):
            self._read_command_char(command, char)

    def _read_command_char(self, command: _Command, char: str) -> None:
        if char in " \t":
            self._end_word(command)
        elif char == '"':
            self._append(command, "")
            self.frames.append(_DoubleQuoted())
        elif char == "(":
            self.frames.append(_Command(")"))
        elif char == ")" or self._separates():
            self._end_command(command)
        else:
            self._append(command, char)
        self.at += 1

    def _read_double_quoted(self) -> None:
        char = self.line[self.at]
        command = self._innermost_command()
        if char == "\\":
            self._read_escape(command, quoted=True)
        elif char == '"':
            self.frames.pop()
            self.at += 1
        elif not self._read_substitution(command):
            self._append(command, char)
            self.at += 1

    def _read_substitution(self, command: _Command) -> bool:
        """`$(…)` and backticks run a command; `$((…))` is arithmetic, so text."""
        if self.line.startswith("$((", self.at):
            self._read_arithmetic(command)
        elif self.line.startswith("$(", self.at):
            self.frames.append(_Command(")"))
            self.at += 2
        elif self.line[self.at] == "`":
            self.frames.append(_Command("`"))
            self.at += 1
        else:
            return False
        self._append(command, "")
        return True

    def _read_arithmetic(self, command: _Command) -> None:
        """To the `)` that closes its first `(`, so its `<<` isn't a heredoc."""
        depth = 0
        end = self.at + 1
        while end < len(self.line):
            depth += {"(": 1, ")": -1}.get(self.line[end], 0)
            end += 1
            if depth == 0:
                break
        self._append(command, self.line[self.at : end])
        self.at = end

    def _read_escape(self, command: _Command, quoted: bool) -> None:
        """A backslash keeps the next character as it is, and before a newline
        both go. In double quotes, it only escapes what's special there."""
        escaped = self.line[self.at + 1 : self.at + 2]
        if escaped == "\n":
            pass
        elif quoted and escaped not in '"\\$`':
            self._append(command, "\\" + escaped)
        else:
            self._append(command, escaped)
        self.at += 2

    def _separates(self) -> bool:
        """`;`, `&` or `|`, but not the `&` of a redirect such as `2>&1`."""
        if self.line[self.at] not in _SEPARATORS:
            return False
        return self.at == 0 or self.line[self.at - 1] not in _REDIRECTS

    def _read_single_quoted(self, command: _Command) -> None:
        end = self._find_or_end("'", self.at + 1)
        self._append(command, self.line[self.at + 1 : end])
        self.at = end + 1

    def _read_heredoc(self, command: _Command) -> None:
        """`<<EOF` or `<<-'EOF'`: its body starts on the next line."""
        self._end_word(command)
        self.at += 2
        strips_tabs = self.line.startswith("-", self.at)
        if strips_tabs:
            self.at += 1
        while self.line[self.at : self.at + 1] in (" ", "\t"):
            self.at += 1
        start = self.at
        while self.at < len(self.line) and self.line[self.at] not in _DELIMITER_END:
            self.at += 1
        delimiter = self.line[start : self.at].translate(_DROP_QUOTES)
        self.heredocs.append(_Heredoc(delimiter, strips_tabs))

    def _skip_heredoc_bodies(self) -> None:
        """Each heredoc begun on the line just read runs to its delimiter's line."""
        for heredoc in self.heredocs:
            while self.at < len(self.line):
                end = self._find_or_end("\n", self.at)
                body_line = self.line[self.at : end]
                self.at = end + 1
                if heredoc.strips_tabs:
                    body_line = body_line.lstrip("\t")
                if body_line == heredoc.delimiter:
                    break
        self.heredocs = []

    def _find_or_end(self, char: str, start: int) -> int:
        """Where `char` next is from `start`, or the end of the line if nowhere."""
        found = self.line.find(char, start)
        return len(self.line) if found == -1 else found

    def _innermost_command(self) -> _Command:
        return next(f for f in reversed(self.frames) if isinstance(f, _Command))

    def _append(self, command: _Command, text: str) -> None:
        command.word = (command.word or "") + text

    def _end_word(self, command: _Command) -> None:
        if command.word is not None:
            command.words.append(command.word)
            command.word = None

    def _end_command(self, command: _Command) -> None:
        self._end_word(command)
        if command.words:
            self.commands.append(command.words)
            command.words = []
