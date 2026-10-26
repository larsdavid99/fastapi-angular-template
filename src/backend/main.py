import env_config  # noqa: F401 - must be first to load .env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from router.hello_router import router as hello_router

app = FastAPI(
    title="App API",
    description="FastAPI + Angular template",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hello_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {"message": "Welcome to App API"}
