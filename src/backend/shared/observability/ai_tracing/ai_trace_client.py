"""AI Trace Client — the port AI calls are traced through (ADR-0002)."""

from typing import Protocol

from shared.observability.ai_tracing.ai_trace import AiTrace


class AiTraceClient(Protocol):
    """
    Gets traces with personal data already replaced; Logic does that.
    Adapters subclass it to inherit flush(), which most don't need.
    """

    def record(self, trace: AiTrace) -> None:
        """Send one AI call. Never raises: tracing must not stop the use case."""
        ...

    def flush(self) -> None:
        """Send what is still queued; called when the app stops."""
