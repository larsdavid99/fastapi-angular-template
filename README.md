# FastAPI + Angular Template

A production-ready starting point for full-stack projects with:

- **Backend:** Python 3.13 + FastAPI with a layered architecture (Router → Facade → Logic → Client)
- **Frontend:** Angular 21+ with standalone components, signals, and a dark-theme design system
- **Docker Compose:** hot reload for both services, `debugpy` attach on `:5678`
- **Architecture docs:** `.claude/CLAUDE.md` (backend) and `.claude/frontend-CLAUDE.md` (frontend)
- **Minimal "hello" feature** end-to-end so you can start by copy-and-modify
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

On the home page, type a name and click **Submit**. The request flows through every layer of the stack and returns a greeting plus a UUID from `httpbin.org`.

## Layout

```
.
├── .claude/                   # Architecture docs, and settings: the mattpocock plugin, the Autopilot skills hook
├── .github/workflows/         # CI, and the workflows that start Autopilot and merge its PRs
├── .vscode/                   # debugpy launch configs, Black + Flake8 settings
├── docs/                      # architecture-pattern.md, docker-setup.md, adr/, agents/ (skill config, Autopilot routine instructions)
├── docker-compose.yml
├── CONTRIBUTING.md            # Roles, labels, the idea → merge workflow, Autopilot
├── bin/rename.sh              # One-shot project rename
├── bin/setup-autopilot.sh     # Labels and main's ruleset on GitHub
└── src/
    ├── autopilot/             # The `autopilot` command, which decides each step of the Autopilot loop, and its skills hook (own tests)
    ├── backend/               # FastAPI
    │   ├── clients/           # Pure HTTP (one class per file)
    │   ├── logic/             # Business rules + orchestration
    │   ├── facade/            # Coordinates Logic
    │   ├── router/            # HTTP endpoints
    │   ├── models/dtos/       # Pydantic request/response models
    │   ├── exceptions/        # Domain exceptions
    │   ├── dependencies/      # FastAPI DI wiring
    │   └── tests/             # pytest + AsyncMock examples
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
```

### Frontend

```bash
# Run unit tests
docker compose exec frontend npm test

# Build for production
docker compose exec frontend npm run build
```

### CI

GitHub Actions runs on every pull request (`.github/workflows/ci.yml`). Each job is its own check: `pytest`, `black` and `flake8` for the backend, `frontend build`, and the `autopilot …` checks for the `autopilot` command. The backend checks install `requirements-dev.txt`, which pins black and flake8, so local runs and CI agree. Pushes to a branch without a PR don't trigger it.

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

1. Pick a domain name (e.g. `user`). Create: `models/dtos/user_*.py`, `exceptions/user_*.py`, `clients/user_http_client.py`, `logic/user_logic.py`, `facade/user_facade.py`, `router/user_router.py`, `dependencies/user_dependencies.py`, `tests/test_user_logic.py`.
2. Register the router in `main.py`.
3. On the frontend: add `models/user-*.model.ts`, `services/data-services/user-data.service.ts`, `services/logic-services/user-logic.service.ts`, and a `pages/user/` or `components/user/` folder.
4. The `hello` feature is a working reference — delete it once you have your own.

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

Layered architecture keeps each layer independently testable:

- **Client** knows HTTP, nothing else.
- **Logic** knows business rules, orchestrates its Client / Resource Access.
- **Facade** coordinates multiple Logic classes and (post-MVP) owns transactions.
- **Router** is a thin mapping of HTTP to Facade calls.
- **Dependencies** wires it all bottom-up via FastAPI's `Depends`.

On the frontend, the same shape applies: components consume Logic Services (signal-based state), which consume Data Services (HTTP), which extend `BaseHttpClient`.

See [docs/architecture-pattern.md](docs/architecture-pattern.md) and [.claude/CLAUDE.md](.claude/CLAUDE.md) for the full explanation.
