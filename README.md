# FastAPI + Angular Template

A production-ready starting point for full-stack projects with:

- **Backend:** Python 3.13 + FastAPI as a modular monolith: feature modules, each layered Router → Facade → Logic → Repository / Client, plus `shared/` infrastructure, with the boundaries checked by import-linter ([ADR-0003](docs/adr/0003-modular-monolith.md))
- **Frontend:** Angular 21+ with standalone components, signals, and a dark-theme design system
- **Docker Compose:** hot reload for both services, `debugpy` attach on `:5678`
- **Observability:** structured JSON logs with a correlation ID and trace ID on every line, OpenTelemetry traces and logs to a local Grafana (`grafana/otel-lgtm`), and AI call tracing in Langfuse behind a port ([ADR-0002](docs/adr/0002-observability-stack.md))
- **Architecture docs:** `.claude/CLAUDE.md` (backend) and `.claude/frontend-CLAUDE.md` (frontend)
- **Minimal `hello` module** end-to-end, with a port and an adapter, so you can start by copy-and-modify
- **Agent workflow:** idea → spec → tickets with the [mattpocock skills](https://github.com/mattpocock/skills), and **Autopilot**, which builds an approved spec one ticket at a time on Claude cloud routines ([`CONTRIBUTING.md`](CONTRIBUTING.md))
- **CI** on every PR, which Autopilot's merge gate relies on

## Using this template

### Option A — GitHub "Use this template" (recommended)

1. Push this directory to a GitHub repo (see "Publishing" below).
2. On the repo page: **Settings → General → Template repository** → enable.
3. Future projects: click **Use this template** on GitHub, or:
   ```bash
   gh repo create my-new-app --template <owner>/<template-repo> --private --clone
   cd my-new-app
   ./bin/rename.sh my-new-app
   ./bin/setup-autopilot.sh   # labels + main's ruleset, see CONTRIBUTING.md
   docker compose up --build
   ```

### Option B — `degit` (no git history)

```bash
npx degit <owner>/<template-repo> my-new-app
cd my-new-app
./bin/rename.sh my-new-app
git init && git add . && git commit -m "Initial commit"
docker compose up --build
```

### Option C — plain clone

```bash
git clone <template-repo-url> my-new-app
cd my-new-app
rm -rf .git && git init
./bin/rename.sh my-new-app
docker compose up --build
```

## Quick start

```bash
# Copy env template (edit as needed)
cp .env.example src/backend/.env

# Build and run
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/health |
| debugpy | tcp://localhost:5678 |
| Grafana (traces, logs) | http://localhost:3000 (admin/admin) |

On the home page, type a name and click **Submit**. The request flows through every layer of the stack and returns a greeting plus a UUID from `httpbin.org`.

## Layout

```
.
├── .claude/                   # Architecture docs, and settings: the mattpocock plugin, the Autopilot skills hook
├── .github/workflows/         # CI, and the workflows that start Autopilot and merge its PRs
├── .vscode/                   # debugpy launch configs, Black + Flake8 settings
├── docs/                      # architecture/ (patterns, observability, boundaries), docker-setup.md, adr/, agents/ (skill config, Autopilot routine instructions)
├── docker-compose.yml
├── CONTRIBUTING.md            # Roles, labels, the idea → merge workflow, Autopilot
├── bin/rename.sh              # One-shot project rename
├── bin/setup-autopilot.sh     # Labels and main's ruleset on GitHub
└── src/
    ├── autopilot/             # The `autopilot` command, which decides each step of the Autopilot loop, and its skills hook (own tests)
    ├── backend/               # FastAPI
    │   ├── main.py            # Mounts each module's router and the health router
    │   ├── conftest.py        # App-wide test fixtures
    │   ├── modules/           # One folder per feature module; its Facade is its public API
    │   │   └── hello/
    │   │       ├── router/        # HTTP endpoints, exceptions → status codes
    │   │       ├── facade/        # One use case end to end; the transaction boundary
    │   │       ├── logic/         # Business rules, and the ports they depend on
    │   │       ├── clients/       # Adapters to outside systems (one class per file)
    │   │       ├── models/dtos/   # Pydantic request/response models
    │   │       ├── exceptions/    # Domain exceptions
    │   │       ├── dependencies/  # FastAPI DI wiring; picks each port's adapter
    │   │       └── tests/         # pytest, with fake ports
    │   └── shared/            # Infrastructure only, never imports a module
    │       ├── config/            # Settings, .env loading
    │       └── observability/     # structlog JSON logging, correlation IDs, OpenTelemetry, redaction, /health, ai_tracing/
    └── frontend/              # Angular
        └── src/app/
            ├── pages/hello/         # Example page
            ├── services/
            │   ├── data-services/   # BaseHttpClient + one subclass per API
            │   └── logic-services/  # Signal-based state; components only touch these
            └── models/              # TypeScript interfaces
```

## Development

### Backend

```bash
# Run tests
docker compose exec backend pytest

# Attach debugger in VS Code
# Use the "Docker: Attach to FastAPI" launch config (see .vscode/launch.json)

# Format
docker compose exec backend black .
docker compose exec backend flake8 .

# Check module and layer boundaries (contracts in pyproject.toml)
docker compose exec backend lint-imports
```

### Observability

Every log line is one JSON object carrying the request's `correlation_id` and `trace_id`. The middleware logs one `request.completed` line per request and echoes `X-Correlation-ID` on every response, the 500 included. Modules log with `structlog.get_logger(__name__)` and an event name (`order.placed`), with details as fields.

- **Traces and logs:** with `docker compose up`, the backend sends both to Grafana at http://localhost:3000. Open **Explore → Tempo** for traces and **Explore → Loki** for logs. From a log line you can jump to its trace. To use Grafana Cloud instead, set `OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS` (see `.env.example`). Nothing is exported while the endpoint is empty.
- **Redaction:** spans and exported log lines are passed through `shared/observability/redaction.py` on the way out, which masks query-string secrets and phone numbers. Add your app's personal data to it.
- **AI calls:** Logic records each call through the `AiTraceClient` port, after `Placeholders` has replaced names and phone numbers. `LangfuseAiTraceClient` is used when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, `NullAiTraceClient` otherwise. To switch vendor, write another adapter and choose it in `shared/observability/ai_tracing/ai_trace_dependencies.py`.

### Frontend

```bash
# Run unit tests
docker compose exec frontend npm test

# Build for production
docker compose exec frontend npm run build
```

### CI

GitHub Actions runs on every pull request (`.github/workflows/ci.yml`). Each job is its own check: `pytest`, `black`, `flake8` and `lint-imports` for the backend, `frontend build`, and the `autopilot …` checks for the `autopilot` command. The backend checks install `requirements-dev.txt`, which pins black, flake8 and import-linter, so local runs and CI agree. Pushes to a branch without a PR don't trigger it.

When you add a check, add its name to `REQUIRED_CHECKS` in `bin/setup-autopilot.sh` and run the script again, so `main` requires it.

### Autopilot

Autopilot builds an approved Spec one Ticket at a time, with no one at the keyboard: cloud agents write, review and fix the code, and the `autopilot` command in `src/autopilot/` decides what happens next. How to set it up, start, stop and read it is in [the Autopilot section of `CONTRIBUTING.md`](CONTRIBUTING.md#autopilot).

To check a change to the command locally, as CI's `autopilot` job does, run these on the host. Use Python 3.10 or newer (the pinned mypy needs it), ideally in a virtualenv:

```bash
cd src/autopilot
pip install -r requirements-dev.txt
python -m pytest        # tests
black --check .         # format
flake8 .                # lint
mypy .                  # type-check
```

The command needs only the standard library and the `gh` CLI. It promises to run on Python 3.9, so CI also runs `autopilot pytest (3.9)`.

## Starting a new feature

1. Decide which module it belongs to. A new bounded context gets a new module: add it to the module map in [ADR-0003](docs/adr/0003-modular-monolith.md) and its terms to `GLOSSARY.md` first.
2. Create `src/backend/modules/<name>/` with only the layers it needs (`router/`, `facade/`, `logic/`, `resource_access/`, `clients/`, `models/dtos/`, `exceptions/`, `dependencies/`, `tests/`). One class per file.
3. Give each outside system a port: a `Protocol` in `logic/` named in the domain's terms, an adapter in `clients/`, and a fake in `tests/`. Choose the adapter in `dependencies/`.
4. Add the module to the import-linter contracts in `pyproject.toml`.
5. Mount its router in `main.py`.
6. On the frontend: add `models/<name>-*.model.ts`, `services/data-services/<name>-data.service.ts`, `services/logic-services/<name>-logic.service.ts`, and a `pages/<name>/` or `components/<name>/` folder.
7. The `hello` module is a working reference — delete it once you have your own.

## Publishing this template

From inside this directory:

```bash
git init
git add .
git commit -m "Initial template scaffolding"
gh repo create fastapi-angular-template --public --source=. --push
gh repo edit --template    # marks as template on GitHub
```

## Philosophy

The backend is a modular monolith: one deployable, split into feature modules that talk only through each other's Facades. Inside a module, dependencies point inward, toward the business rules, so each layer can be tested on its own:

- **Router** maps HTTP to one Facade call, and domain exceptions to status codes.
- **Facade** runs one use case end to end, owns its transaction, and is the module's public API.
- **Logic** holds the business rules and depends on ports, never on vendors.
- **Repository / Client** do CRUD on the module's own tables, or talk to one outside system. A Client is the anti-corruption layer: vendor names and errors stop there.
- **Dependencies** wires it all via FastAPI's `Depends`, and is the only place adapters are chosen.

On the frontend, the same shape applies: components consume Logic Services (signal-based state), which consume Data Services (HTTP), which extend `BaseHttpClient`.

See [.claude/CLAUDE.md](.claude/CLAUDE.md) for the rules and [docs/architecture/](docs/architecture/) for the details and examples.
