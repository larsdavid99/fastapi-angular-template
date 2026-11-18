"""Null AI Trace Client — used when no Langfuse keys are configured."""

from clients.ai_trace_client import AiTraceClient
from models.dtos.ai_trace import AiTrace


class NullAiTraceClient(AiTraceClient):
    def record(self, trace: AiTrace) -> None:
        pass
