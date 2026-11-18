# Patterns: details and examples

Read with the root `CLAUDE.md`. The examples continue its `payments` module.

## Unit of Work

One transaction per use case. Repositories add and flush; the Facade opens the Unit of Work, and it commits only when the block finishes without an exception.

```python
# shared/database/unit_of_work.py
class UnitOfWork:
    def __init__(self, db: Session):
        self.db = db

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, exc_type, *_) -> None:
        if exc_type is None:
            self.db.commit()
        else:
            self.db.rollback()
```

## Ports, adapters, and test doubles

Each external system has one port and one or more adapters. A **null adapter** is a valid adapter for an optional feature or for local development; a **fake** is the adapter tests use.

```python
class NullPaymentGateway:  # implements PaymentGateway
    """Approves every charge; used when no Stripe key is configured."""

    def charge(self, charge: GatewayCharge) -> GatewayOutcome:
        return GatewayOutcome(provider_reference=f"null-{charge.idempotency_key}", approved=True)


class FakePaymentGateway:  # implements PaymentGateway, for tests
    def __init__(self, approve: bool = True):
        self.approve = approve
        self.charges = 0

    def charge(self, charge: GatewayCharge) -> GatewayOutcome:
        self.charges += 1
        return GatewayOutcome(provider_reference=f"fake-{self.charges}", approved=self.approve)
```

An adapter is tested against a fake transport, so the test pins the vendor's shape without the network:

```python
def test_stripe_decline_maps_to_our_outcome():
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=STRIPE_DECLINED))
    gateway = StripePaymentGateway(httpx.Client(transport=transport, base_url="https://stripe.test"))
    assert gateway.charge(a_gateway_charge()).decline_code == "insufficient_funds"
```

Swap an adapter in an end-to-end test through the DI container:

```python
app.dependency_overrides[get_payment_gateway] = lambda: FakePaymentGateway(approve=False)
```

## Shared helper

When two Logics need the same behaviour, a class without the `Logic` suffix is injected into both. It never calls a Logic and never commits.

```python
# modules/payments/logic/money_rounding.py
class MoneyRounding:
    """Injected into PaymentLogic and RefundLogic so both round alike."""

    def to_minor_units(self, amount: Decimal, currency: Currency) -> int: ...
```

## Idempotency keys

Every inbound event that causes a side effect carries an external ID with a **unique constraint**, and the first step of handling it is "have we seen this ID?". `PaymentLogic.charge` in the root file shows the check for an API request. The constraint and the webhook version:

```python
class PaymentRecord(Base):
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)


class WebhookEventRecord(Base):
    provider_event_id: Mapped[str] = mapped_column(String(255), unique=True)


def receive(self, event: ProviderEvent) -> ProviderEvent | None:
    if self.webhook_event_repository.exists(event.provider_event_id):
        logger.info("webhook.duplicate", provider_event_id=event.provider_event_id)
        return None
    self.webhook_event_repository.create(WebhookEventCreate.from_event(event))
    return event
```

Outbound calls that the vendor supports with idempotency keys send one (the `Idempotency-Key` header in `StripePaymentGateway`). The test that pins it:

```python
def test_retried_charge_does_not_charge_twice():
    gateway = FakePaymentGateway(approve=True)
    logic = PaymentLogic(gateway, InMemoryPaymentRepository())
    logic.charge(a_charge_order(idempotency_key="k1"))
    logic.charge(a_charge_order(idempotency_key="k1"))
    assert gateway.charges == 1
```

## Added when the need is real (record each in an ADR)

### Outbox
When losing an event after a commit is unacceptable. Write the event to an outbox table in the same transaction, and have a worker publish it.

```python
with self.unit_of_work:
    result = self.payment_logic.charge(request)  # also writes a PaymentSucceeded outbox row
# A scheduled job reads unsent outbox rows, publishes each one, then marks it sent.
```

### Domain events
When a module must react to another (orders reacting to "payment succeeded") and a direct Facade-to-Facade call would make the modules depend on each other in both directions. Before adding a bus, a plain return value listing what happened is often enough:

```python
class ChargeOutcome(BaseModel):
    result: ChargeResult
    succeeded: PaymentSucceeded | None = None  # what happened, for the Facade to pass on


if outcome.succeeded is not None:
    self.order_facade.mark_paid(outcome.succeeded)
```

### Strategy
When there is more than one adapter for a port in production at the same time (two payment providers).

```python
class PaymentLogic:
    def __init__(self, gateways: dict[Provider, PaymentGateway], ...): ...

    def charge(self, request: ChargeOrder) -> ChargeResult:
        gateway = self.gateways[self._provider_for(request.order.currency)]
        ...
```
