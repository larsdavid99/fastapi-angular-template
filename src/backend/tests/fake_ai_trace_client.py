"""Fake AI Trace Client for Seam 1: records what would have reached Langfuse."""

from clients.ai_trace_client import AiTraceClient
from models.dtos.ai_trace import AiTrace


class FakeAiTraceClient(AiTraceClient):
    def __init__(self) -> None:
        self.traces: list[AiTrace] = []

    def record(self, trace: AiTrace) -> None:
        self.traces.append(trace)
