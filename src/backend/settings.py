"""Application settings loaded from the environment."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Typed view of the environment variables the app reads."""

    environment: str = "development"
    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"] = "INFO"
    # OpenTelemetry (ADR-0002): OTLP/HTTP base URL, e.g. http://otel-lgtm:4318;
    # nothing is exported while it is empty. Headers as in the OTel spec
    # ("Authorization=Basic%20..." for Grafana Cloud).
    otel_exporter_otlp_endpoint: str = ""
    otel_exporter_otlp_headers: str = ""
    otel_service_name: str = "app-backend"
    # AI call tracing (ADR-0002); off while either key is empty.
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "https://cloud.langfuse.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
