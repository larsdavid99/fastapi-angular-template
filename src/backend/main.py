import env_config  # noqa: F401 - must be first to load .env

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dependencies.ai_trace_dependencies import get_ai_trace_client
from observability.correlation_id_middleware import CorrelationIdMiddleware
from observability.internal_error_handler import internal_error_handler
from observability.log_export import configure_log_export
from observability.logging_config import configure_logging
from observability.tracing import configure_tracing, instrument
from router.hello_router import router as hello_router
from settings import get_settings

settings = get_settings()
configure_logging(level=settings.log_level)
configure_log_export(settings)
tracer_provider = configure_tracing(settings)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    # Flush, not shut down: the providers shut down at process exit, and the
    # app may be started again in the same process (tests, reloads).
    get_ai_trace_client().flush()
    tracer_provider.force_flush()


app = FastAPI(
    title="App API",
    description="FastAPI + Angular template",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # So the frontend can read the ID and quote it in a bug report.
    expose_headers=[CorrelationIdMiddleware.HEADER],
)
app.add_exception_handler(Exception, internal_error_handler)
app.include_router(hello_router)
instrument(app, tracer_provider)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {"message": "Welcome to App API"}
