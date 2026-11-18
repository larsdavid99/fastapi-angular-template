"""OpenTelemetry export of the app's log lines, for Loki (ADR-0002)."""

import logging

from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    LogRecordExporter,
    SimpleLogRecordProcessor,
)

from observability.logging_config import json_formatter
from observability.otlp_log_handler import OtlpLogHandler
from observability.otlp_settings import otlp_headers, otlp_resource, otlp_url
from settings import Settings


def configure_log_export(settings: Settings) -> LoggerProvider:
    """
    The app's logger provider. Every log line also goes over OTLP/HTTP when
    an endpoint is configured, to the same backend as the traces (Loki in
    grafana/otel-lgtm locally, e.g. Grafana Cloud when deployed). Call it after
    configure_logging, which replaces the root logger's handlers.
    """
    provider = LoggerProvider(resource=otlp_resource(settings))
    if settings.otel_exporter_otlp_endpoint:
        export_logs(provider, _otlp_exporter(settings))
    logging.getLogger().addHandler(OtlpLogHandler(provider, json_formatter()))
    set_logger_provider(provider)
    return provider


def export_logs(
    provider: LoggerProvider, exporter: LogRecordExporter, batch: bool = True
) -> None:
    """batch=False exports each line as it's logged."""
    processor = (
        BatchLogRecordProcessor(exporter)
        if batch
        else SimpleLogRecordProcessor(exporter)
    )
    provider.add_log_record_processor(processor)


def _otlp_exporter(settings: Settings) -> OTLPLogExporter:
    return OTLPLogExporter(
        endpoint=otlp_url(settings, "logs"), headers=otlp_headers(settings)
    )
