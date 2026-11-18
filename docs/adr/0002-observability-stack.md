# Observability: structlog + OpenTelemetry to Grafana, Langfuse for AI calls behind a port

Application logs are structured JSON (structlog). Uvicorn's and every other stdlib logger go through the same formatter, so every line has the same shape. Middleware gives each inbound request a correlation ID, reusing a well-formed incoming `X-Correlation-ID`, binds it to every log line and span, and echoes it on the response. Traces use OpenTelemetry auto-instrumentation (FastAPI and httpx, plus SQLAlchemy once the app has a database), and the same JSON log lines are exported over OpenTelemetry too, each carrying its trace ID. Both go over OTLP/HTTP to `grafana/otel-lgtm` (Grafana, Tempo, Loki and Prometheus in one container) locally, and to any OTLP backend when deployed, such as Grafana Cloud's free tier. Changing the backend is configuration, not code.

AI calls are traced in Langfuse for prompt versions, token cost and latency. Logic records each call through the `AiTraceClient` port, so Langfuse is one adapter (`LangfuseAiTraceClient`) and can be replaced by writing another. `NullAiTraceClient` is used while no Langfuse keys are set. The Langfuse adapter has its own tracer provider, so the app's request spans never reach Langfuse, and its AI spans never reach Grafana.

## Personal data

Phone numbers and secrets in query strings are masked in every span and exported log line by a redaction step on each exporter, as a backstop. Request and response bodies are never recorded, and outbound calls' query strings are dropped from their spans. AI call input and output reach Langfuse only after `Placeholders` has replaced names and phone numbers with `<NAME_n>` and `<PHONE_n>`.

## Consequences

- Each app adds its own personal data (emails, addresses, positions) to `shared/observability/redaction.py` and records what counts as personal data here.
- `Placeholders` can only replace names the caller knows and passes in. A name it was never told reaches Langfuse as written. Accept this, or run named-entity recognition before tracing.
- Logs are not the audit trail: a record the business must keep is written to a table inside the use case's transaction.
