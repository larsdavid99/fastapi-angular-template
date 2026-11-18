# The backend is a modular monolith: feature modules plus shared infrastructure, boundaries checked by import-linter

The backend is one deployable, split into feature modules under `src/backend/modules/`. Each module has its own layers (Router → Facade → Logic → Repository / Client, wired in `dependencies/`), its own DTOs, exceptions and tests, and owns its tables. A module's Facade, with its DTOs and exceptions, is its public API. Modules call each other only Facade to Facade, never join or hold a foreign key into another module's tables. `src/backend/shared/` holds infrastructure only: configuration (`shared/config/`) and observability (`shared/observability/`, including AI call tracing behind the `AiTraceClient` port from ADR-0002). A database with its Unit of Work and a clock join it when the first module needs them. A business rule two modules need lives in one of them, behind its Facade, not in `shared/`.

We chose this over the flat layout the template started with (one `router/ facade/ logic/ clients/` tree for the whole app), because in a flat tree nothing stops one feature from reaching into another's Logic or tables, and the coupling only shows once the features have to be pulled apart. Splitting into separate services would give the same boundaries at the cost of a network hop, a deployment and a database per service. A modular monolith keeps one deployable and lets a module be lifted out later if it needs to be.

Ports belong to Logic: a module's port is a `Protocol` in its `logic/`, and the adapter in `clients/` satisfies it without importing it. A port kept in `clients/` would make every Facade import a Client indirectly through its Logic, which the "Facades only talk to Logic" contract forbids.

## Module map

- **hello**: a reference module that shows every layer end to end: a greeting with a UUID from a `UuidSource` port, implemented by an httpbin adapter. Delete it once the first real module exists, and replace this list with the real one.

## Consequences

- `lint-imports` runs in CI (`pyproject.toml` holds the contracts). A new module is added to the layers contract's `containers` and gets its own "Facades only talk to Logic" and "only through its Facade" contracts.
- Each module's tests live in its `tests/` folder; app-wide fixtures are in `src/backend/conftest.py`.
- Each new module is added to the module map above, and its terms to `GLOSSARY.md`, before its code is written.
