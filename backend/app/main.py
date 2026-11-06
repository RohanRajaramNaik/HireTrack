"""HireTrack FastAPI application.

Development:  uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload   (Vite on 5173)
Production:   npm run build in frontend/, then the same uvicorn command serves
              the built frontend and the API on http://127.0.0.1:8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .database import init_db
from .errors import AppError
from .logging_setup import setup_logging
from .routers import admin, candidates, jobs, match

log = logging.getLogger("hiretrack")

FIELD_LABELS = {
    "full_name": "Full name",
    "resume_summary": "Resume summary",
    "job_title": "Job title",
    "job_description": "Job description",
    "years_experience": "Years of experience",
    "min_experience": "Minimum experience",
    "level_id": "Education level",
    "min_level_id": "Minimum education",
}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    setup_logging()
    settings.ensure_dirs()
    init_db()
    if not settings.disable_startup_backup:
        from .services import backup_service, seed_service

        try:
            backup_service.startup_backup()
        except Exception:  # pragma: no cover
            log.exception("Start-up backup failed")
        seed_service.warm_embeddings_async()
    log.info("HireTrack started on %s:%s", settings.host, settings.port)
    yield


app = FastAPI(title="HireTrack Matching Engine", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Admin-Passcode"],
)


# ----------------------------------------------------------------- errors
def _friendly(err: dict) -> tuple[str, str | None]:
    """Turn one Pydantic error into (message, field) in plain English."""
    loc = [str(p) for p in err.get("loc", []) if p not in ("body", "query", "path")]
    field = loc[0] if loc else None
    ctx = err.get("ctx") or {}
    original = ctx.get("error")
    if original is not None and getattr(original, "field", None):
        return str(original), original.field
    label = FIELD_LABELS.get(field or "", (field or "Value").replace("_", " ").capitalize())
    t = err.get("type", "")
    if t == "missing":
        return f"{label} is required", field
    if t == "string_too_short":
        n = ctx.get("min_length")
        return (f"{label} is required" if n == 1 else f"{label} must be at least {n} characters"), field
    if t == "string_too_long":
        return f"{label} must be {ctx.get('max_length')} characters or fewer", field
    if t in ("greater_than_equal", "greater_than"):
        return f"{label} cannot be less than {ctx.get('ge', ctx.get('gt'))}", field
    if t in ("less_than_equal", "less_than"):
        return f"{label} cannot be more than {ctx.get('le', ctx.get('lt'))}", field
    msg = err.get("msg", "Invalid value")
    return msg.removeprefix("Value error, "), field


@app.exception_handler(RequestValidationError)
async def _validation_handler(_req: Request, exc: RequestValidationError):
    errors = exc.errors()
    detail, field = _friendly(errors[0]) if errors else ("Invalid request", None)
    return JSONResponse(status_code=422, content={"detail": detail, "field": field})


@app.exception_handler(AppError)
async def _app_error_handler(_req: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "field": exc.field})


@app.exception_handler(IntegrityError)
async def _integrity_handler(_req: Request, exc: IntegrityError):
    log.warning("Integrity error: %s", exc.orig)
    return JSONResponse(status_code=409, content={"detail": "That change conflicts with existing data", "field": None})


@app.exception_handler(StarletteHTTPException)
async def _http_handler(_req: Request, exc: StarletteHTTPException):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail), "field": None})


# ----------------------------------------------------------------- routes
app.include_router(candidates.router)
app.include_router(jobs.router)
app.include_router(match.router)
app.include_router(admin.router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------- built frontend (SPA)
_dist = settings.frontend_dist
if (_dist / "index.html").exists():
    if (_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found", "field": None})
        candidate = (_dist / full_path).resolve()
        if full_path and candidate.is_file() and _dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
