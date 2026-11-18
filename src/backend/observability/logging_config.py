"""structlog JSON logging for the app and every stdlib logger (ADR-0002)."""

import logging
import sys
from typing import TextIO

import structlog

_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]

# Uvicorn's own handlers would bypass the JSON formatter; send them to root instead.
_UVICORN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")


def configure_logging(level: str = "INFO", stream: TextIO | None = None) -> None:
    """Render every log line, structlog or stdlib, as one JSON object."""
    _configure_structlog()
    _configure_root_logger(level, stream or sys.stdout)
    _route_uvicorn_to_root()


def _configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *_SHARED_PROCESSORS,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def json_formatter() -> logging.Formatter:
    """Renders a structlog or stdlib record as the app's JSON log line."""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_SHARED_PROCESSORS,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )


def _configure_root_logger(level: str, stream: TextIO) -> None:
    handler = logging.StreamHandler(stream)
    handler.setFormatter(json_formatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


def _route_uvicorn_to_root() -> None:
    for name in _UVICORN_LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
    # CorrelationIdMiddleware logs each request with its ID; skip the duplicate.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
