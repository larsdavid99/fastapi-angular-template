# Project Guide

<!-- Fill in: one paragraph on what this app does, who uses it, and the stack. -->

## Commands

<!-- Fill in: install, run, test, lint, type-check, migrate. One line each. -->

---

## Architecture

A modular monolith (see **Structure**): the app is split into feature modules, and inside each module a layered API in which dependencies point inward, toward the business rules. The design is language-agnostic: an *interface* below means whatever your language uses (C# `interface`, Python `Protocol`/ABC, TypeScript `interface`, Go `interface`, Rust `trait`).

```
Router → Facade → Logic → Repository / Client
```

| Layer | Speaks | Owns |
|-------|--------|------|
| **Router** | HTTP | Request/response, maps exceptions to status codes |
| **Facade** | Orchestration | One use case end to end; the transaction boundary |
| **Logic** | Business rules | Decisions, validation, calculations |
| **Repository** | SQL / ORM | Pure CRUD on our own data |
| **Client** | HTTP / SDK | One outside system: a vendor API, the clock, the filesystem |
| **Dependencies** | DI container | Wiring; the only place concrete adapters are chosen |

**The direction rule:** inside a module, each layer calls only the layer below it. A Router calls a Facade, a Facade calls Logic, and Logic calls Repositories and Clients. Between modules, only Facades talk. Enforce this with an import linter in CI (`import-linter`, `dependency-cruiser`, ArchUnit, NetArchTest) so the rule is checked by a machine, not remembered.

### Router
Parses the request into a DTO, calls one Facade method, and maps domain exceptions to HTTP codes. A handler is a few lines long.

### Facade
Runs one use case as a short, readable list of steps across one or more Logics in its module, and is the module's public API to the rest of the app. When a use case spans modules, it calls the other module's Facade. It is the **only layer that commits** (Unit of Work): repositories add and flush, and the Facade commits once everything has succeeded. When a Facade method grows, extract the side effects (sending messages, notifying other modules) into a Facade helper so the main method still reads as the use case.

### Logic
All business decisions live here. Logic depends on **ports**, never on vendors:

- A **port** is an interface Logic owns, named in the domain's terms: `PaymentGateway.charge(ChargeRequest)`, not `StripeClient.createPaymentIntent(...)`. Test: if the interface mirrors the vendor's API, it is not a port yet.
- One Logic never calls another. When two Logics need the same behaviour, extract a **shared helper** (a class without the `Logic` suffix) that both receive by injection; it never calls a Logic and never commits. When two Logics need to cooperate, the Facade coordinates them.
- Split a Logic when it holds two separable paths. Reads and writes, or "do" and "undo", are the usual seams (CQRS-lite).

### Repository
Pure persistence on our own data: queries in, records out. It may `flush()` to obtain generated IDs. Business rules and commits belong to the layers above.

### Client (adapter)
A Client is **thin**: authentication, sending the request, retries and timeouts, and mapping the vendor's response into our DTOs. Every decision about what a response *means* belongs in Logic.

- Each Client implements a port, and Logic only sees the port.
- The Client is the **anti-corruption layer**: vendor names, IDs, and quirks are translated at this boundary and never appear in a DTO.
- It wraps vendor errors in our own domain exceptions.
- Large payloads such as prompt templates, request builders, or response mappers go in their own modules beside the Client, which keeps the Client to "send, parse, wrap errors".
- When the vendor API is large, split the Client by resource (`OrdersClient`, `CustomersClient`).
- Time, randomness, and the filesystem are Clients too (`Clock`), so tests can control them.

---

## Patterns

Use these by default:

- **Ports and adapters**: described under Logic and Client. Each external system has one port and one or more adapters. A *null adapter* (`NullPlacesClient`) is a valid adapter for an optional feature or for local development.
- **Interfaces where they earn their keep**: on ports and on module Facades. Concrete Logic, Repository, and Facade classes go without an interface unless something genuinely swaps them.
- **DTO-first**: methods take and return DTOs (one request DTO instead of a long parameter list). Each module keeps its DTOs in its own `models/dtos/`, one class per file.
- **Result objects for expected outcomes**: an expected failure such as a declined card, a refusal, or a failed delivery comes back as a result value the caller must handle. Exceptions are for the unexpected.
- **Idempotency keys**: every inbound event that causes a side effect carries an external ID with a **unique constraint**, and the first step of handling it is "have we seen this ID?". Webhook providers retry, and a retried webhook must not charge, log, or send twice. Outbound calls that the vendor supports with idempotency keys send one.
- **Unit of Work**: one transaction per use case, committed by the Facade.

Add these when the need is real, and record the decision in an ADR:

- **Outbox**: when losing an event after a commit is unacceptable. Write the event to an outbox table in the same transaction, and have a worker publish it.
- **Domain events**: when a module must react to another (orders reacting to "payment succeeded") and a direct Facade-to-Facade call would make the modules depend on each other in both directions. Before adding a bus, a plain return value listing what happened ("logged", "ended") is often enough.
- **Strategy**: when there is more than one adapter for a port in production at the same time (two payment providers).

---

## Structure: modules first

The app is a **modular monolith**: one deployable, split into feature modules. Each module is a **bounded context**, a group of concepts that share one vocabulary (payments, orders, catalogue), and each module contains the full set of layers. One class per file; filename = snake_case (or the language's convention) of the class.

```
src/
├── modules/
│   ├── payments/
│   │   ├── CLAUDE.md          # this module's rules only (add when it has some)
│   │   ├── router/
│   │   ├── facade/            # the module's public API
│   │   ├── logic/
│   │   ├── resource_access/   # repositories
│   │   ├── clients/           # ports and their adapters
│   │   ├── models/dtos/
│   │   ├── exceptions/
│   │   ├── dependencies/
│   │   └── tests/
│   └── orders/
│       └── ...                # same layers
├── shared/                    # the shared kernel: kept small
│   ├── database/              # engine, session, Unit of Work
│   ├── observability/         # logging, tracing, correlation IDs
│   └── clock/                 # Clock port + system adapter
└── main                       # app startup: mounts each module's router
```

### Module rules

- **A module's Facade is its public API.** Another module reaches it only through that Facade (or through the DTOs that Facade accepts and returns). Its Logic, Repositories, Clients, and ORM models are private.
- **Cross-module calls happen Facade to Facade.** A Facade may call another module's Facade to orchestrate a use case that spans modules; Logic stays inside its own module.
- **Each module owns its data.** Its tables are read and written only by its own Repositories. Another module that needs that data asks the owning Facade, and refers to the module's records by ID rather than by foreign key into its tables.
- **`shared/` holds infrastructure, not business rules.** When two modules want the same business rule, one module owns it and exposes it through its Facade.
- **The import linter enforces the boundaries:** the layer rules inside every module, plus "module A imports only `modules.b.facade` and `modules.b.models.dtos` from module B".

Draw the module map in an ADR and put each module's vocabulary in `GLOSSARY.md` before writing its code. A new module starts with only the layers it needs (a module with no outside system has no `clients/`).

---

## Observability

All of it lives in `shared/observability/`, configured once at startup. Modules only ever call `get_logger(__name__)`.

### Logging

- **Structured JSON only**, from one logging library (structlog, Serilog, pino, zap, slog). Framework and third-party loggers are routed through the same formatter, so every line in the output is the same shape.
- **Events, not sentences.** The message is a stable event name, `<area>.<what_happened>` in past tense (`payment.charged`, `outbound.failed`, `request.completed`), and the details are key-value fields. Dashboards and alerts query these names, so a rename is a breaking change.
- **Every line carries a correlation ID and a trace ID.** Middleware reuses a well-formed incoming `X-Correlation-ID` or generates one, binds it to the logging context for the request, and echoes it on every response, the 500 included. A background job binds its own ID when it starts. An ID that arrives in a webhook or queue message is kept, so one flow can be followed across services.
- **The middleware logs one line per request**: method, path, status, and duration. Handlers add only what that line cannot say.
- **Levels have fixed meanings:**
  - `debug`: development detail, off in production.
  - `info`: a business event happened (`order.placed`).
  - `warning`: an expected failure was handled (vendor down, retry, rate limit, invalid input).
  - `error`: something a human must look at.
- **Log an exception once, where it is handled.** A layer that re-raises or wraps an exception leaves the logging to the layer that catches it. The request middleware logs anything unhandled, with its stack trace.
- **Each layer logs what it decides.** Logic logs business events and decisions, and the Facade logs the outcome of a use case. Clients and Repositories raise domain exceptions, and the Logic that handles them logs the failure.
- **Fields are an allowlist.** Log IDs, counts, durations, statuses, and masked values (`+46*****123`), choosing each field by name. Whole DTOs, request bodies, message text, tokens, and secrets stay out of logs. A **redaction processor** on *every* sink (stdout, the log exporter, the span exporter) masks secrets, credentials in query strings, and personal data as a backstop.
- **Logs are not the audit trail.** A record the business must keep (who did what, what the AI decided, what was sent) is written to a table through a Repository, inside the use case's transaction. Logs may be sampled, rotated, or lost.
- **Tests assert on important events** by capturing log output and checking the event name and fields, never the formatted text.

### Tracing and metrics

- **OpenTelemetry**, auto-instrumented for the web framework, the database driver, and the HTTP client. Traces, metrics, and the log lines go to one OTLP endpoint, so changing the backend is a configuration change.
- **The correlation ID is set on the request's span**, and the trace ID is on every log line, so a log line links to its trace and back.
- **LLM calls are traced** in an LLM observability tool (prompt version, model, tokens, cost, latency), with personal data replaced by placeholders before the call is sent to it.
- **A health endpoint** checks each dependency (database, required vendors) and reports which one is down.

Record the observability stack and what counts as personal data in an ADR.

## Coding standards

- **Small methods:** each method does one thing and reads at a glance. Extract sub-steps into private helpers named for what they decide.
- **Testable in isolation:** every Logic is unit-tested with fake ports; adapters are tested against a recorded or fake transport; a few end-to-end tests go through the Router.
- **One meaning, one place:** a rule, constant, or mapping lives in exactly one file.
- **Comments explain why**, in one line; the name explains what.

---

## Context for Claude

- Keep this root file to rules that apply everywhere. Each module gets a short `CLAUDE.md` once it has its own conventions: its vocabulary, its invariants, the outside systems it wraps. It loads only when Claude works in that module, so point Claude at one module per task.
- Leave out anything Claude can look up in config, scripts, or the folder layout. Write down the *why* behind a choice and the gotchas no config reveals.
- Decisions live in `docs/adr/` (one numbered file per decision) and domain terms in `GLOSSARY.md`. Use glossary terms in code, tests, and prompts.
