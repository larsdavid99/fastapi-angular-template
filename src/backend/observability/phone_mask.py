"""Phone masking for logs: phone numbers never appear in full (ADR-0002)."""

_VISIBLE_DIGITS = 2


def mask_phone(number: str) -> str:
    """'+46701234567' -> '*********67'; short or non-phone values are fully masked."""
    if len(number) <= _VISIBLE_DIGITS * 2:
        return "*" * len(number)
    return "*" * (len(number) - _VISIBLE_DIGITS) + number[-_VISIBLE_DIGITS:]
