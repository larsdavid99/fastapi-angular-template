"""Where traces and log lines are exported over OTLP/HTTP, and as whom (ADR-0002)."""

from urllib.parse import unquote

from opentelemetry.sdk.resources import Resource

from settings import Settings


def otlp_resource(settings: Settings) -> Resource:
    """The service every exported span and log line is labelled with."""
    return Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment.name": settings.environment,
        }
    )


def otlp_url(settings: Settings, signal: str) -> str:
    """The endpoint's URL for one signal, e.g. 'traces' or 'logs'."""
    return f"{settings.otel_exporter_otlp_endpoint.rstrip('/')}/v1/{signal}"


def otlp_headers(settings: Settings) -> dict[str, str]:
    """OTEL_EXPORTER_OTLP_HEADERS format: 'key=value,key2=value2', URL-encoded."""
    value = settings.otel_exporter_otlp_headers
    pairs = (item.split("=", 1) for item in value.split(",") if "=" in item)
    return {key.strip(): unquote(header.strip()) for key, header in pairs}
