# Domain Architecture Pattern

Layered architecture following **S.O.L.I.D. principles** for maintainability, testability, and separation of concerns.

## Layer Overview

| Layer | Speaks | Responsibility |
|-------|--------|----------------|
| **Resource Access** | SQL | Pure database CRUD (Post-MVP) |
| **Client** | HTTP | External API communication |
| **Logic** | Business Rules | Calculations, validation, data access orchestration |
| **Facade** | Orchestration | Coordinates layers, manages transactions |
| **Router** | HTTP Interface | Request/response, exception mapping |
| **Dependencies** | DI Container | Wires everything together |

```
Router → Facade → Logic → Resource Access/Client
```

**Key Rule:** Facade → Logic → Resource Access/Client. Facade **never** talks directly to Resource Access or Client.

## Coding Standards

### Small Methods
- Each method does **one thing** and is easily understood at a glance
- If a method grows complex, extract sub-steps into private helper methods
- Methods should be **easily testable** in isolation

### DTO-First Design
- **Pass DTOs (Pydantic models) as method parameters** instead of multiple individual arguments
- DTOs for requests, responses, and intermediate data transfer between layers
- All schemas live in `models/dtos/` folder, one file per DTO

```python
# BAD — too many parameters
def greet(name: str, language: str, formal: bool) -> dict:
    ...

# GOOD — DTO as parameter
class HelloRequest(BaseModel):
    name: str
    language: str = "en"
    formal: bool = False

def greet(self, request: HelloRequest) -> HelloResponse:
    ...
```

## File Structure

Flat, layer-based structure. **One class per file. Filename = snake_case of class name.**

```
src/backend/
├── clients/
│   └── example_http_client.py     # ExampleHttpClient (pure HTTP)
├── logic/
│   └── hello_logic.py             # HelloLogic (business rules + orchestration)
├── facade/
│   └── hello_facade.py            # HelloFacade (coordinates Logic)
├── router/
│   └── hello_router.py            # HTTP endpoints
├── models/dtos/
│   ├── hello_request.py           # HelloRequest
│   └── hello_response.py          # HelloResponse
├── exceptions/
│   └── example_api_error.py       # ExampleApiError
├── dependencies/
│   └── hello_dependencies.py      # DI wiring
├── resource_access/               # Post-MVP (no DB yet)
│   └── ...repository.py
└── tests/
    ├── conftest.py                # Shared fixtures
    └── test_hello_logic.py        # Example tests
```

---

## Layer Definitions

### Resource Access (`resource_access/`) — Post-MVP

> **Post-MVP:** This layer is not needed until persistence is added. The MVP is stateless.

Pure database CRUD. No business logic. No commits.

```python
class ExampleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: str) -> ExampleRecord | None:
        return self.db.query(ExampleRecord).filter(ExampleRecord.id == id).first()

    def create(self, dto: ExampleRecordCreate) -> ExampleRecord:
        record = ExampleRecord(**dto.model_dump())
        self.db.add(record)  # No commit - Facade controls this
        return record
```

**Rules:** Only SQLAlchemy, uses DTOs, no `.commit()`, no business logic.

---

### Client (`clients/`)
Pure HTTP communication. No business logic — just requests, responses, and error wrapping.

```python
# clients/example_http_client.py
class ExampleHttpClient:
    async def fetch_uuid(self) -> str: ...
```

**Rules:** Only HTTP, raises domain exceptions, no DB interaction, no business logic.

---

### Logic (`logic/`)
Business rules AND data access orchestration. **Only layer that talks to Resource Access/Client.**

```python
# logic/hello_logic.py
class HelloLogic:
    def __init__(self, example_http_client: ExampleHttpClient):
        self.example_http_client = example_http_client

    async def greet(self, request: HelloRequest) -> HelloResponse: ...
```

**Rules:** Contains all business rules, calls Resource Access/Client, no HTTP knowledge, no `.commit()`.

---

### Facade (`facade/`)
Orchestrates workflows through Logic. Controls transactions (Post-MVP). **Never talks to Resource Access/Client directly.**

```python
# facade/hello_facade.py
class HelloFacade:
    def __init__(self, hello_logic: HelloLogic):
        self.hello_logic = hello_logic

    async def greet(self, request: HelloRequest) -> HelloResponse:
        return await self.hello_logic.greet(request)
```

**Rules:** Only talks to Logic, never to Resource Access or Client directly. Router's only dependency. Post-MVP: only layer that calls `.commit()`.

---

### Dependencies (`dependencies/`)
DI container wiring all layers together.

```python
# dependencies/hello_dependencies.py
def get_example_http_client() -> ExampleHttpClient: ...
def get_hello_logic(
    client: Annotated[ExampleHttpClient, Depends(get_example_http_client)]
) -> HelloLogic: ...
def get_hello_facade(
    logic: Annotated[HelloLogic, Depends(get_hello_logic)]
) -> HelloFacade: ...
```

**Testing:** Use `app.dependency_overrides[get_example_http_client] = mock_fn` to swap implementations.

---

### Router (`router/`)
HTTP interface. Only talks to Facade. Maps exceptions to HTTP codes.

```python
# router/hello_router.py
router = APIRouter(prefix="/api", tags=["hello"])

@router.post("/hello", response_model=HelloResponse)
async def hello(
    request: HelloRequest,
    facade: Annotated[HelloFacade, Depends(get_hello_facade)]
) -> HelloResponse:
    try:
        return await facade.greet(request)
    except ExampleApiError as e:
        raise HTTPException(status_code=502, detail=e.message)
```

**Rules:** Only Facade, maps exceptions to HTTP codes, no business logic.

---

## Transaction Management — Post-MVP

> **Post-MVP:** Transaction management is not needed until persistence is added.

Unit of Work pattern in Facade:
1. Resource Access methods do NOT commit
2. Facade calls `.flush()` for IDs without committing
3. Facade calls `.commit()` after all operations succeed
4. On failure, transaction auto-rolls back

---

## Cross-Module Communication

With a flat, layer-based structure, cross-module communication follows the same rules:

| Rule | Description |
|------|-------------|
| **Logic → Logic** | NOT allowed. Logic only calls its own Resource Access/Client |
| **Facade → other Logic** | Allowed. Cross-module orchestration happens at Facade level |
| **Exception ownership** | Each module owns its exceptions in `exceptions/` |

---

## Quick Reference

| Task | Layer |
|------|-------|
| New database query | Resource Access (Post-MVP) |
| New external API call | Client |
| Parsing / validation / diff rule | Logic |
| Coordinate operations | Facade |
| New endpoint | Router |
| Wire dependency | Dependencies |

| Benefit | How |
|---------|-----|
| Testability | Mock dependencies per layer |
| Maintainability | Change one layer without affecting others |
| SOLID | Single responsibility per layer, dependency inversion via DI |

---

## Agent skills

### Workflow

Ideas go through grill → spec → Reviewer approval → tickets → implement → PR. Specs are published with `needs-review`, not `ready-for-agent`. An approved Spec can be built by Autopilot instead (`docs/adr/0001-autopilot-on-cloud-routines.md`). See `CONTRIBUTING.md` and the overrides in `docs/agents/triage-labels.md`.

### Issue tracker

Issues are tracked in this repo's GitHub Issues via the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
