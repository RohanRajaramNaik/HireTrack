"""FastAPI application entry point (skeleton; routers added in step 3)."""
from fastapi import FastAPI

from .database import init_db

app = FastAPI(title="HireTrack Matching Engine")


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
