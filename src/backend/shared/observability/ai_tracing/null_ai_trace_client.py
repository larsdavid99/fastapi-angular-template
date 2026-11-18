"""Null AI Trace Client — used when no Langfuse keys are configured."""

from shared.observability.ai_tracing.ai_trace_client import AiTraceClient
from shared.observability.ai_tracing.ai_trace import AiTrace


class NullAiTraceClient(AiTraceClient):
    def record(self, trace: AiTrace) -> None:
        pass
