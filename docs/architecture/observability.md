# Observability: setup and examples

Read with the root `CLAUDE.md`, which holds the rules. Everything here lives in `shared/observability/` and is configured once at startup.

## Logging setup

One chain of processors renders structlog and stdlib records (uvicorn, SQLAlchemy) as the same JSON line. Redaction runs before any sink sees the line.

```python
# shared/observability/logging_config.py
shared_processors = [
    structlog.contextvars.merge_contextvars,  # correlation_id, trace_id
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.format_exc_info,
    redact_processor,
]
# structlog.configure(...) uses the chain; stdlib handlers get
# structlog.stdlib.ProcessorFormatter(foreign_pre_chain=shared_processors, ...).
# Route uvicorn's loggers to root so they use the same formatter.
```

A rendered line:

```json
{"event": "payment.charged", "payment_id": 7, "order_id": 42, "amount_minor": 1999,
 "level": "info", "timestamp": "2026-11-18T09:12:03Z", "correlation_id": "…", "trace_id": "…"}
```

## Correlation ID middleware

```python
# shared/observability/correlation_id_middleware.py (inside __call__)
incoming = Headers(scope=scope).get("X-Correlation-ID")
correlation_id = incoming if incoming and VALID_ID.fullmatch(incoming) else str(uuid.uuid4())
structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
trace.get_current_span().set_attribute("correlation_id", correlation_id)
# ...the response's start message gets the same X-Correlation-ID header,
# and the outcome is logged once:
logger.info("request.completed", method="POST", path="/api/payments", status=200, duration_ms=84.2)
```

The 500 handler reads the bound ID and sets the same header. A scheduled job binds its own ID when it starts:

```python
structlog.contextvars.bind_contextvars(correlation_id=f"job-{uuid.uuid4()}")
```

## Levels

```python
logger.debug("gateway.payload_built", fields=12)               # development detail
logger.info("order.placed", order_id=42)                       # a business event
logger.warning("payment.provider_failed", order_id=42)         # an expected failure, handled
logger.error("outbox.stuck", oldest_minutes=45)                # a human must look
```

## Log an exception once, where it is handled

```python
# Client: wraps and raises, no log line
except httpx.HTTPError as e:
    raise PaymentProviderError("Payment provider unavailable") from e

# Logic: handles it, so it logs it, once
try:
    outcome = self.gateway.charge(charge)
except PaymentProviderError:
    logger.warning("payment.provider_failed", order_id=request.order.order_id)
    return ChargeResult(approved=False, decline_reason=DeclineReason.PROVIDER_DOWN)
```

## Fields are an allowlist; redaction is the backstop

```python
# GOOD: chosen fields, masked phone number
logger.info("customer.notified", customer_id=customer.id, phone=mask_phone(customer.phone))

# BAD: everything the DTO holds, including whatever is added to it later
logger.info("customer.notified", customer=customer.model_dump())
```

```python
# shared/observability/redaction.py
_SECRET_QUERY_VALUE = re.compile(r"(?i)([?&](?:secret|password|token|api_key)=)[^&#\s]*")

def redact_processor(_, __, event_dict: dict) -> dict:
    return {key: _redact(value) if isinstance(value, str) else value for key, value in event_dict.items()}
```

The same `_redact` wraps the span exporter (below), so stdout, exported logs, and traces are all covered.

## Audit trail

Records the business must keep go to a table, inside the use case's transaction:

```python
self.audit_repository.create(AuditEntry(action="payment.charged", actor_id=user_id, subject_id=payment.id))
```

## Testing log events

```python
def test_provider_failure_is_logged_as_warning():
    logic = PaymentLogic(FailingPaymentGateway(), InMemoryPaymentRepository())
    with structlog.testing.capture_logs() as logs:
        logic.charge(a_charge_order(order_id=42))
    assert {"event": "payment.provider_failed", "order_id": 42, "log_level": "warning"} in logs
```

## Tracing setup

```python
# shared/observability/tracing.py
provider = TracerProvider(resource=Resource.create({"service.name": settings.otel_service_name}))
if settings.otel_exporter_otlp_endpoint:  # empty: instrumented, nothing exported
    exporter = RedactingSpanExporter(OTLPSpanExporter(endpoint=f"{settings.otel_exporter_otlp_endpoint}/v1/traces"))
    provider.add_span_processor(BatchSpanProcessor(exporter))
FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
SQLAlchemyInstrumentor().instrument(engine=engine, tracer_provider=provider)
HTTPXClientInstrumentor().instrument(tracer_provider=provider)
```

Log lines go to the same OTLP endpoint (`/v1/logs`) with their trace context, so a line links to its trace.

## LLM call tracing

The tracer is a port like any other Client. Personal data is replaced before the trace leaves the app:

```python
self.ai_trace_client.record(AiTrace(
    prompt_version="interpret-v3",
    model=settings.ai_model,
    input=self.placeholders.replace(text),  # "Anna paid" → "Person1 paid"
    input_tokens=usage.input_tokens,
    output_tokens=usage.output_tokens,
    latency_ms=elapsed_ms,
))
```

## Health endpoint

```
GET /health → 200 {"status": "ok", "checks": {"database": "ok", "stripe": "ok"}}
GET /health → 503 {"status": "degraded", "checks": {"database": "ok", "stripe": "down"}}
```
