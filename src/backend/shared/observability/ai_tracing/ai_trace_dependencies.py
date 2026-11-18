"""AI Trace Dependencies — DI wiring for where AI calls are traced (ADR-0002)."""

from functools import lru_cache

from shared.observability.ai_tracing.ai_trace_client import AiTraceClient
from shared.observability.ai_tracing.langfuse_ai_trace_client import (
    LangfuseAiTraceClient,
)
from shared.observability.ai_tracing.null_ai_trace_client import NullAiTraceClient
from shared.observability.ai_tracing.langfuse_config import LangfuseConfig
from shared.config.settings import get_settings


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
