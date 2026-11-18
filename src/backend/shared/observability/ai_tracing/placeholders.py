"""Placeholders — names and phone numbers never reach AI tracing (ADR-0002)."""

import json
import re
from collections.abc import Iterable
from typing import Any

# Seven or more digits, however they are spaced or punctuated.
_PHONE_LIKE = re.compile(r"\+?\d(?:[\s\-().]*\d){6,}")
_NON_DIGITS = re.compile(r"\D")


class Placeholders:
    """
    Replaces each name with <NAME_n> and each phone number with <PHONE_n>,
    numbered in order of first sight. One instance per AI call, so a person
    keeps one placeholder across its input and output and the trace still
    reads like the original.

    A text can only be cleaned of names the caller knows and passes in.
    Names match whole words in any case, so a name that is also a word
    ("Will") is replaced wherever the word is.
    """

    def __init__(self, names: Iterable[str]):
        self._names = self._name_pattern(names)
        self._numbered: dict[str, str] = {}

    def apply_json(self, document: str) -> str:
        """
        Replace inside a JSON document's string values, after unescaping them
        (a model may write "J\\u00f6ns"); a document that isn't JSON is treated
        as plain text.
        """
        try:
            parsed = json.loads(document)
        except ValueError:
            return self.apply(document)
        return json.dumps(self._apply_values(parsed), ensure_ascii=False)

    def apply(self, text: str) -> str:
        text = _PHONE_LIKE.sub(self._phone, text)
        if self._names is not None:
            text = self._names.sub(self._name, text)
        return text

    def _apply_values(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.apply(value)
        if isinstance(value, list):
            return [self._apply_values(item) for item in value]
        if isinstance(value, dict):
            return {key: self._apply_values(item) for key, item in value.items()}
        return value

    def _phone(self, match: re.Match[str]) -> str:
        return self._placeholder("PHONE", _NON_DIGITS.sub("", match.group()))

    def _name(self, match: re.Match[str]) -> str:
        return self._placeholder("NAME", match.group().casefold())

    def _placeholder(self, kind: str, key: str) -> str:
        """The same key always gets the same placeholder."""
        key = f"{kind}:{key}"
        if key not in self._numbered:
            count = sum(1 for k in self._numbered if k.startswith(f"{kind}:"))
            self._numbered[key] = f"<{kind}_{count + 1}>"
        return self._numbered[key]

    def _name_pattern(self, names: Iterable[str]) -> re.Pattern[str] | None:
        cleaned = {name.strip() for name in names if name and name.strip()}
        if not cleaned:
            return None
        # Longest first, so "Anna-Lisa" isn't read as "Anna" followed by "-Lisa".
        alternatives = sorted(cleaned, key=len, reverse=True)
        pattern = "|".join(re.escape(name) for name in alternatives)
        return re.compile(rf"(?<!\w)(?:{pattern})(?!\w)", re.IGNORECASE)
