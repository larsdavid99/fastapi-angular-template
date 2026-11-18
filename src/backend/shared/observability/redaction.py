"""Redaction — no secrets or phone numbers leave in traces or logs (ADR-0002)."""

import re

from shared.observability.phone_mask import mask_phone

# Credentials ride in query strings, e.g. a webhook's ?secret= or a vendor's ?api_key=.
_SECRET_QUERY_VALUE = re.compile(
    r"(?i)([?&](?:secret|password|token|key|api_key)=)[^&#\s\"']*"
)
# International numbers, as written or URL-encoded ("%2B"), however spaced.
# Bare digit runs are left alone, since span IDs and UUID correlation IDs are
# full of them.
_PHONE = re.compile(r"(?i)(?:\+|%2B)\d(?:[\s\-().]*\d){6,}")


def redact(text: str) -> str:
    """Query-string secrets replaced and phone numbers masked."""
    text = _SECRET_QUERY_VALUE.sub(r"\1REDACTED", text)
    return _PHONE.sub(lambda match: mask_phone(match.group()), text)
