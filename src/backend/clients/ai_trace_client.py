"""AI Trace Client — where AI calls are traced (ADR-0002)."""

from abc import ABC, abstractmethod

from models.dtos.ai_trace import AiTrace


class AiTraceClient(ABC):
    """Gets traces with personal data already replaced; Logic does that."""

    @abstractmethod
    def record(self, trace: AiTrace) -> None:
        """Send one AI call. Never raises: tracing must not stop the use case."""

    def flush(self) -> None:
        """Send what is still queued; called when the app stops."""
