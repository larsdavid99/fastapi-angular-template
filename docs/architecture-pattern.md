# Architecture Pattern

Layered architecture following **S.O.L.I.D. principles**.

```
Router → Facade → Logic → Resource Access / Client
```

**Key Rule:** Facade only talks to Logic. Logic only talks to Resource Access/Client.

## Layers

| Layer | Responsibility | Rules |
|-------|---------------|-------|
| **Resource Access** | Database CRUD (Post-MVP) | No `.commit()`, no business logic |
| **Client** | External HTTP APIs | Raises domain exceptions, no DB, no logic |
| **Logic** | Business rules, data orchestration | Only layer that talks to Resource Access/Client |
| **Facade** | Coordinates Logic classes | Only layer that calls `.commit()` (Post-MVP) |
| **Router** | HTTP endpoints | Only talks to Facade, maps exceptions to HTTP codes |
| **Dependencies** | DI wiring | Builds bottom-up: Client → Logic → Facade |

## Coding Standards

- **Small methods** — each does one thing, easily testable in isolation
- **DTO-first** — pass Pydantic models as parameters, not loose args
- **One class per file** — filename = snake_case of class name (`example_http_client.py` → `ExampleHttpClient`)

```python
# BAD
def greet(name: str, language: str, formal: bool) -> dict: ...

# GOOD
def greet(self, request: HelloRequest) -> HelloResponse: ...
```

## File Structure

```
src/backend/
├── clients/
│   └── example_http_client.py    # ExampleHttpClient (pure HTTP)
├── logic/
│   └── hello_logic.py            # HelloLogic (rules + orchestration)
├── facade/
│   └── hello_facade.py           # HelloFacade (coordinates Logic)
├── router/
│   └── hello_router.py
├── models/dtos/
│   ├── hello_request.py          # HelloRequest
│   └── hello_response.py         # HelloResponse
├── exceptions/
│   └── example_api_error.py      # ExampleApiError
├── dependencies/
│   └── hello_dependencies.py
├── resource_access/              # Post-MVP
│   └── ...repository.py
└── tests/
    ├── conftest.py               # Shared fixtures
    └── test_hello_logic.py       # HelloLogic tests
```

## Layer Examples

### Client — pure HTTP, no logic

The Client layer is deliberately "dumb" — it only knows how to make HTTP requests and wrap errors. This means you can test all business logic without mocking HTTP.

```python
# clients/example_http_client.py
class ExampleHttpClient:
    """Pure HTTP calls. No parsing, no business rules — just request/response."""

    async def fetch_uuid(self) -> str:
        """GET https://httpbin.org/uuid and return the uuid value."""
        ...
```

### Logic — business rules, delegates to Client/Resource Access

Each Logic class owns one domain. It orchestrates the HTTP calls through the Client and applies business rules.

```python
# logic/hello_logic.py — business rules + orchestration
class HelloLogic:
    def __init__(self, example_http_client: ExampleHttpClient):
        self.example_http_client = example_http_client

    async def greet(self, request: HelloRequest) -> HelloResponse:
        uuid = await self.example_http_client.fetch_uuid()
        message = self._build_message(request.name)
        return HelloResponse(message=message, uuid=uuid)

    def _build_message(self, name: str) -> str:
        return f"Hello {name}"
```

### Facade — orchestrates Logic classes

Since Logic → Logic is not allowed, the Facade is the place for cross-domain orchestration.

```python
# facade/hello_facade.py
class HelloFacade:
    def __init__(self, hello_logic: HelloLogic):
        self.hello_logic = hello_logic

    async def greet(self, request: HelloRequest) -> HelloResponse:
        return await self.hello_logic.greet(request)
```

### Dependencies — DI wiring (bottom-up)

```python
# dependencies/hello_dependencies.py
def get_example_http_client() -> ExampleHttpClient:
    return ExampleHttpClient()

def get_hello_logic(
    client: Annotated[ExampleHttpClient, Depends(get_example_http_client)]
) -> HelloLogic:
    return HelloLogic(client)

def get_hello_facade(
    logic: Annotated[HelloLogic, Depends(get_hello_logic)]
) -> HelloFacade:
    return HelloFacade(logic)
```

### Router — HTTP interface

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

## Cross-Module Rules

| Rule | Description |
|------|-------------|
| Logic → Logic | **Not allowed.** Each Logic class only calls its own Client/Resource Access |
| Facade → multiple Logic | **Allowed.** Cross-module orchestration happens at Facade level |
| Exception ownership | Each module owns its exceptions in `exceptions/` |

## Testing

**Stateless logic needs no mocks** — a pure function class has no dependencies:

```python
def test_build_message():
    logic = HelloLogic(example_http_client=None)
    assert logic._build_message("World") == "Hello World"
```

**Logic with Client dependency** — mock the Client with `AsyncMock`:

```python
async def test_greet():
    mock_client = AsyncMock(spec=ExampleHttpClient)
    mock_client.fetch_uuid.return_value = "fake-uuid"

    logic = HelloLogic(example_http_client=mock_client)
    result = await logic.greet(HelloRequest(name="World"))
    assert result.message == "Hello World"
    assert result.uuid == "fake-uuid"
```

**Integration tests** — swap dependencies via `app.dependency_overrides`:

```python
app.dependency_overrides[get_example_http_client] = lambda: mock_http_client
```

## Transaction Management — Post-MVP

> Not needed until persistence is added. The MVP is stateless.

When added: Resource Access never commits. Facade calls `.flush()` for IDs, `.commit()` after all operations succeed. Failures auto-rollback.

## Quick Reference

| Task | Layer |
|------|-------|
| New database query | Resource Access (Post-MVP) |
| New external API call | Client |
| Calculation / validation / diff | Logic |
| Coordinate operations | Facade |
| New endpoint | Router |
| Wire dependency | Dependencies |
