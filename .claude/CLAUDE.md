# Project Guide

<!-- Fill in: one paragraph on what this app does, who uses it, and the stack. -->

## Commands

<!-- Fill in: one line each (install, run, test, lint + types + lint-imports, migrate). -->

## Read before you start

- Adding a pattern (Unit of Work, null or fake adapter, shared helper, idempotency, outbox, domain events, strategy) → `../docs/architecture/patterns.md`
- Touching logging, tracing, redaction, the health check, or a log test → `../docs/architecture/observability.md`
- Creating a module, a cross-module call, or an import-linter contract → `../docs/architecture/boundaries.md`

---

## Architecture

A **modular monolith**: one deployable, split into feature modules, each a layered API in which dependencies point inward, toward the business rules. *Interface* means your language's version (C# `interface`, Python `Protocol`, TypeScript `interface`, Go `interface`, Rust `trait`). Examples are Python and follow a `payments` module that charges orders from an `orders` module.

```
Router → Facade → Logic → Repository / Client
```

| Layer | Speaks | Owns |
|-------|--------|------|
| **Router** | HTTP | Request/response, maps exceptions to status codes |
| **Facade** | Orchestration | One use case end to end; the transaction boundary; the module's public API |
| **Logic** | Business rules | Decisions, validation, calculations |
| **Repository** | SQL / ORM | Pure CRUD on our own data |
| **Client** | HTTP / SDK | One outside system: a vendor API, the clock, the filesystem |
| **Dependencies** | DI container | Wiring; the only place concrete adapters are chosen |

**The direction rule:** inside a module, each layer calls only the layer below it. Between modules, only Facades talk. An import linter enforces both in CI.

### Router
Parses the request into a DTO, calls one Facade method, maps domain exceptions to HTTP codes.

```python
@router.post("", response_model=ChargeResponse)
def charge(
    request: ChargeRequest,
    facade: Annotated[PaymentFacade, Depends(get_payment_facade)],
) -> ChargeResponse:
    try:
        return facade.charge(request)
    except OrderNotPayableError as e:
        raise HTTPException(status_code=409, detail=e.message)
```

### Facade
Runs one use case as a short list of steps across its module's Logics, and calls another module's Facade when the use case spans modules. It is the **only layer that commits** (Unit of Work). When a method grows, extract side effects (sending, notifying) into a Facade helper.

```python
class PaymentFacade:
    def charge(self, request: ChargeRequest) -> ChargeResponse:
        order = self.order_facade.payable(request.order_id)  # other module: its Facade
        with self.unit_of_work:  # commits on success, rolls back on an exception
            result = self.payment_logic.charge(
                ChargeOrder(order=order, idempotency_key=request.idempotency_key)
            )
        return ChargeResponse.from_result(result)
```

### Logic
All business decisions live here, and Logic depends on **ports**, never on vendors.

- A **port** is an interface Logic owns, named in the domain's terms: `PaymentGateway.charge(...)`, not `StripeClient.create_payment_intent(...)`. If the interface mirrors the vendor's API, it is not a port yet.
- One Logic never calls another. Shared behaviour goes in a **shared helper** (no `Logic` suffix, e.g. `MoneyRounding`) injected into both; cooperation is coordinated by the Facade.
- Split a Logic along separable paths: reads and writes, or do and undo (`PaymentLogic.charge`, `RefundLogic.refund`).

```python
class PaymentLogic:
    def __init__(self, gateway: PaymentGateway, payment_repository: PaymentRepository):
        self.gateway = gateway
        self.payment_repository = payment_repository

    def charge(self, request: ChargeOrder) -> ChargeResult:
        previous = self.payment_repository.get_by_key(request.idempotency_key)
        if previous is not None:  # a retried request: answer as before, charge nothing
            return ChargeResult.from_record(previous)
        outcome = self.gateway.charge(self._gateway_charge(request))
        payment = self.payment_repository.create(self._payment(request, outcome))
        self._log(payment)
        return ChargeResult.from_record(payment)
```

### Repository
Queries in, records out. It may `flush()` for generated IDs; commits and rules live above it.

```python
class PaymentRepository:
    def create(self, dto: PaymentCreate) -> PaymentRecord:
        record = PaymentRecord(**dto.model_dump())
        self.db.add(record)
        self.db.flush()  # the caller needs the generated ID; the Facade commits
        return record
```

### Client (adapter)
**Thin**: auth, the request, retries and timeouts, and mapping the response into our DTOs. What a response *means* is decided in Logic.

- Each Client implements a port. It is the **anti-corruption layer**: vendor names, IDs and quirks stop here, and vendor errors become our exceptions.
- Prompt templates, request builders and mappers go in modules beside the Client. Split a large vendor API by resource (`OrdersClient`, `CustomersClient`).
- Time, randomness and the filesystem are Clients too (`Clock`), so tests control them.

```python
class PaymentGateway(Protocol):  # the port, in our terms
    def charge(self, charge: GatewayCharge) -> GatewayOutcome: ...


class StripePaymentGateway:  # the adapter
    def charge(self, charge: GatewayCharge) -> GatewayOutcome:
        try:
            response = self.http.post(
                "/v1/payment_intents",
                data=self._payload(charge),
                headers={"Idempotency-Key": charge.idempotency_key},
            )
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise PaymentProviderError("Payment provider unavailable") from e
        return self._outcome(response.json())  # Stripe's names stop in _outcome
```

### Dependencies
Wiring only; picks the adapter for each port. Tests swap adapters with `app.dependency_overrides`.

```python
def get_payment_gateway(settings: Annotated[Settings, Depends(get_settings)]) -> PaymentGateway:
    if not settings.stripe_api_key:
        return NullPaymentGateway()  # local development without Stripe keys
    return StripePaymentGateway(httpx.Client(base_url=settings.stripe_url, timeout=10))
```

---

## Patterns

Use by default:

- **Ports and adapters**, with null adapters for optional features and fakes for tests.
- **Interfaces only where something swaps**: ports and module Facades. `PaymentLogic` has one implementation, so no interface.
- **DTO-first**: one DTO in, one DTO out, one class per file in the module's `models/dtos/`.

  ```python
  class ChargeRequest(BaseModel):
      order_id: int
      idempotency_key: str = Field(..., max_length=64)

  def charge(self, request: ChargeRequest) -> ChargeResponse: ...  # not (order_id, amount, currency, key)
  ```

- **Result objects for expected outcomes** (declined, refused, not delivered); exceptions for the unexpected.

  ```python
  class ChargeResult(BaseModel):
      approved: bool
      decline_reason: DeclineReason | None = None  # CARD_DECLINED, PROVIDER_DOWN, ...
  ```

- **Idempotency keys**: every inbound side-effecting event has an external ID with a **unique constraint**, checked first (see `PaymentLogic.charge`). Outbound calls send the vendor's idempotency key where it has one.
- **Unit of Work**: one transaction per use case, committed by the Facade.

Add only when the need is real, with an ADR: **outbox**, **domain events**, **strategy**.

---

## Structure

```
src/
├── modules/
│   ├── payments/
│   │   ├── CLAUDE.md          # this module's conventions, once it has some
│   │   ├── router/  facade/  logic/  resource_access/  clients/
│   │   ├── models/dtos/  models/orm/  exceptions/  dependencies/  tests/
│   └── orders/ ...
├── shared/                    # infrastructure only: database + UnitOfWork, observability, clock
└── main.py                    # mounts each module's router
```

One class per file; filename = snake_case of the class. A module starts with only the layers it needs.

**Module rules:**
- A module's **Facade is its public API**, with its DTOs and exceptions. Its Logic, Repositories, Clients and ORM models are private.
- Cross-module calls go **Facade to Facade**.
- Each module **owns its tables**. Other modules ask its Facade and hold its records' IDs, never a join or foreign key into its tables.
- `shared/` holds infrastructure. A business rule two modules need belongs to one of them, behind its Facade.
- Module boundaries follow **bounded contexts**: record the module map in an ADR and each module's terms in `GLOSSARY.md` before writing its code.

---

## Observability

Configured once in `shared/observability/`; modules call `structlog.get_logger(__name__)`.

**Logging**
- **Structured JSON only**; framework loggers go through the same formatter.
- **Events, not sentences**: a stable `<area>.<what_happened>` name plus fields. Renaming one breaks dashboards.

  ```python
  logger.info("payment.charged", payment_id=payment.id, order_id=order.order_id, amount_minor=1999)
  # not: logger.info(f"Charged order {order.order_id} for {amount}")
  ```

- **Every line has a correlation ID and a trace ID.** Middleware reuses a valid incoming `X-Correlation-ID` or generates one, binds it, echoes it on every response (500s too), and logs one `request.completed` line. Background jobs bind their own.
- **Levels:** `debug` dev detail · `info` a business event · `warning` an expected failure handled · `error` a human must look.
- **Log an exception once, where it is handled.** Clients and Repositories raise; the Logic that handles the exception logs it; middleware logs anything unhandled.
- **Fields are an allowlist**: IDs, counts, durations, statuses, masked values. No whole DTOs, bodies, message text, tokens or secrets. A **redaction processor on every sink** (stdout, log export, span export) is the backstop.
- **Logs are not the audit trail.** Records the business must keep go to a table, in the use case's transaction.
- Tests assert on event name and fields, not formatted text.

**Tracing**
- **OpenTelemetry** auto-instruments the web framework, database and HTTP client. Traces, metrics and logs go to one OTLP endpoint; the backend is configuration.
- LLM calls are traced (prompt version, model, tokens, cost, latency) with personal data replaced by placeholders.
- A **health endpoint** reports each dependency.

---

## Coding standards

- **Small methods**: one job each, readable at a glance; sub-steps become private helpers named for what they decide (`PaymentLogic.charge` is the target shape).
- **Testable in isolation**: Logic with fake ports, adapters against a fake transport, a few end-to-end tests through the Router.
- **One meaning, one place**: each rule, constant or mapping lives in one file.
- **Comments say why**, in one line: `# Stripe keeps keys for 24 h; our retries finish well within that`.

---

## Context for Claude

- This file holds rules for everywhere. A module's own conventions (vocabulary, invariants, the vendors it wraps) go in that module's `CLAUDE.md`, which loads only when Claude works there. Work on one module per task.
- Write down the *why* and the gotchas; leave out what config, scripts or the folder layout already say.
- Decisions go in `../docs/adr/` (one numbered file each), terms in `GLOSSARY.md`. Use glossary terms in code, tests and prompts.
