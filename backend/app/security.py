"""Admin passcode check (bcrypt hash stored in .env as ADMIN_PASSCODE_HASH)."""
from __future__ import annotations

import logging

from fastapi import Header
from passlib.context import CryptContext

from .config import settings
from .errors import AppError, Unauthorized

log = logging.getLogger("hiretrack.security")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_passcode(passcode: str) -> str:
    return pwd_context.hash(passcode)


def verify_passcode(passcode: str | None) -> bool:
    if not passcode or not settings.admin_passcode_hash:
        return False
    try:
        return pwd_context.verify(passcode, settings.admin_passcode_hash)
    except (ValueError, TypeError):
        return False


def require_admin(x_admin_passcode: str | None = Header(default=None)) -> None:
    """FastAPI dependency: the passcode travels in the X-Admin-Passcode header."""
    if not settings.admin_passcode_hash:
        raise AppError(
            "Admin passcode is not set up. Run: python -m app.hash_passcode <passcode> --write",
            field="passcode",
            status_code=503,
        )
    if not verify_passcode(x_admin_passcode):
        log.warning("Rejected admin request: wrong or missing passcode")
        raise Unauthorized("Incorrect passcode", field="passcode")
