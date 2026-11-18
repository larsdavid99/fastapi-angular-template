# Boundaries: enforcing layers and modules

Read with the root `CLAUDE.md`, which holds the rules. This file shows how they are enforced and documented.

## Import-linter contracts

Run `lint-imports` in CI. Add each new module to the `containers` list and give it its own boundary contract.

```toml
# pyproject.toml
[tool.importlinter]
root_package = "modules"

[[tool.importlinter.contracts]]
name = "Layers inside each module"
type = "layers"
containers = ["modules.payments", "modules.orders"]
layers = ["router", "facade", "logic", "resource_access | clients"]

[[tool.importlinter.contracts]]
name = "Facades only talk to Logic"
type = "forbidden"
source_modules = ["modules.payments.facade", "modules.orders.facade"]
forbidden_modules = [
    "modules.payments.resource_access", "modules.payments.clients",
    "modules.orders.resource_access", "modules.orders.clients",
]

[[tool.importlinter.contracts]]
name = "Other modules use orders only through its Facade, DTOs and exceptions"
type = "forbidden"
source_modules = ["modules.payments"]
forbidden_modules = [
    "modules.orders.router", "modules.orders.logic",
    "modules.orders.resource_access", "modules.orders.clients", "modules.orders.models.orm",
]
```

Other stacks: `dependency-cruiser` (TypeScript), ArchUnit (Java/Kotlin), NetArchTest or ArchUnitNET (C#), `go-arch-lint` (Go).

Violations that are not imports (a Facade reaching through `self.logic.repository`) are the code review's job.

## Data ownership

```python
# GOOD: payments stores order_id as a plain column and asks orders for the rest
order = self.order_facade.payable(request.order_id)

# BAD: payments joins orders' table
select(PaymentRecord, OrderRecord).join(OrderRecord)
```

## Documenting a module

The module map goes in an ADR, each module's terms in `GLOSSARY.md`, and the module's own conventions in its `CLAUDE.md`.

```markdown
<!-- docs/adr/0002-module-map.md -->
# Modules: orders, payments, catalogue
Orders owns the order lifecycle; payments owns charges and refunds; catalogue
owns products and prices. Payments asks orders for a payable order and tells
it when one is paid. We accept a Facade call in each direction for now and will
switch the "paid" call to a domain event if a third module needs it.
```

```markdown
<!-- GLOSSARY.md -->
**Charge**: one attempt to take money for an Order. May be approved or declined.
**Payment**: an approved Charge. An Order has at most one.
```

```markdown
<!-- modules/payments/CLAUDE.md -->
# Payments
- Amounts are integers in minor units (`amount_minor`); Decimal only at the edges.
- Every charge carries an idempotency key, sent to Stripe as `Idempotency-Key`.
- Stripe test cards and webhook replay: see docs/payments-testing.md.
```
