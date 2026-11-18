"""AI Trace Dependencies — DI wiring for where AI calls are traced (ADR-0002)."""

from functools import lru_cache

from clients.ai_trace_client import AiTraceClient
from clients.langfuse_ai_trace_client import LangfuseAiTraceClient
from clients.null_ai_trace_client import NullAiTraceClient
from models.dtos.langfuse_config import LangfuseConfig
from settings import get_settings


@lru_cache
def get_ai_trace_client() -> AiTraceClient:
    """One client (and export queue) for the app's lifetime."""
    settings = get_settings()
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return NullAiTraceClient()
    return LangfuseAiTraceClient(
        LangfuseConfig(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            base_url=settings.langfuse_base_url,
            environment=settings.environment,
        )
    )
