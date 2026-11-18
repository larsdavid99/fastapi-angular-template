"""Langfuse AI Trace Client — AI calls as Langfuse generations (ADR-0002)."""

import json
from datetime import datetime, timedelta

from langfuse import Langfuse, LangfuseOtelSpanAttributes
from opentelemetry.context import Context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter
from opentelemetry.util.types import AttributeValue

from shared.observability.ai_tracing.ai_trace_client import AiTraceClient
from shared.observability.ai_tracing.ai_trace import AiTrace
from shared.observability.ai_tracing.langfuse_config import LangfuseConfig

Attr = LangfuseOtelSpanAttributes


class LangfuseAiTraceClient(AiTraceClient):
    """
    Langfuse ingests OpenTelemetry spans. This client has its own tracer
    provider, so the app's request, database and HTTP spans never reach
    Langfuse and these spans never reach the app's trace backend. Each call
    is written as one span after it happened, with its real start and end,
    so Langfuse shows its latency; spans are exported in the background.

    Langfuse keeps one set of resources per public key for the process, so
    make one client per key (the app makes one for its lifetime).
    """

    _TRACER_NAME = "app.ai"

    def __init__(
        self, config: LangfuseConfig, span_exporter: SpanExporter | None = None
    ):
        self.config = config
        self._provider = TracerProvider()
        # Attaches Langfuse's exporting span processor to our provider.
        self._langfuse = Langfuse(
            public_key=config.public_key,
            secret_key=config.secret_key,
            base_url=config.base_url,
            environment=config.environment,
            tracer_provider=self._provider,
            should_export_span=lambda span: True,  # the provider holds only ours
            span_exporter=span_exporter,
        )
        self._tracer = self._provider.get_tracer(self._TRACER_NAME)

    def record(self, trace: AiTrace) -> None:
        span = self._tracer.start_span(
            trace.name,
            context=Context(),  # a root: the app's request span isn't in Langfuse
            start_time=self._nanoseconds(trace.started_at),
            attributes=self._attributes(trace),
        )
        span.end(
            end_time=self._nanoseconds(
                trace.started_at + timedelta(milliseconds=trace.latency_ms)
            )
        )

    def flush(self) -> None:
        """Export every recorded span now."""
        self._provider.force_flush()

    def shutdown(self) -> None:
        """Stop Langfuse's background work; it also does this at process exit."""
        self._langfuse.shutdown()

    def _attributes(self, trace: AiTrace) -> dict[str, AttributeValue]:
        attributes: dict[str, AttributeValue | None] = {
            Attr.TRACE_NAME: trace.name,
            Attr.ENVIRONMENT: self.config.environment,
            Attr.OBSERVATION_TYPE: "generation",
            Attr.OBSERVATION_MODEL: trace.model,
            # The observation's version: our prompts live in code, not in
            # Langfuse's prompt management, which the prompt.* attributes link to.
            Attr.VERSION: trace.prompt_version,
            Attr.OBSERVATION_INPUT: trace.input,
            Attr.OBSERVATION_OUTPUT: trace.output,
            Attr.OBSERVATION_USAGE_DETAILS: self._usage(trace),
            Attr.OBSERVATION_COST_DETAILS: self._cost(trace),
            f"{Attr.OBSERVATION_METADATA}.prompt_version": json.dumps(
                trace.prompt_version
            ),
            **self._correlation(trace),
            **self._error(trace),
        }
        return {key: value for key, value in attributes.items() if value is not None}

    def _usage(self, trace: AiTrace) -> str | None:
        if trace.input_tokens is None or trace.output_tokens is None:
            return None
        return json.dumps({"input": trace.input_tokens, "output": trace.output_tokens})

    def _cost(self, trace: AiTrace) -> str | None:
        return None if trace.cost_usd is None else json.dumps({"total": trace.cost_usd})

    def _correlation(self, trace: AiTrace) -> dict[str, AttributeValue | None]:
        """Metadata values are JSON, so Langfuse can filter traces on them."""
        value = json.dumps(trace.correlation_id)
        return {
            f"{Attr.TRACE_METADATA}.correlation_id": value,
            f"{Attr.OBSERVATION_METADATA}.correlation_id": value,
        }

    def _error(self, trace: AiTrace) -> dict[str, AttributeValue | None]:
        if trace.error is None:
            return {}
        return {
            Attr.OBSERVATION_LEVEL: "ERROR",
            Attr.OBSERVATION_STATUS_MESSAGE: trace.error,
        }

    def _nanoseconds(self, moment: datetime) -> int:
        return int(moment.timestamp() * 1_000_000_000)
