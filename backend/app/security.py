"""Authentication and role-based access control.

- Passwords are stored only as bcrypt hashes (passlib).
- After login the browser receives a signed JWT (HS256) that it sends back in
  the Authorization header. The token carries the user id and role and expires
  after TOKEN_HOURS hours.
- Every protected route declares the roles it allows with require_roles(...).
- Destructive admin actions (reset data, restore a backup) also need the
  admin's password again in the X-Confirm-Password header.
"""
from __future__ import annotations

import logging
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .errors import AppError, Forbidden, Unauthorized

log = logging.getLogger("hiretrack.security")
# 12 rounds in normal use; tests lower it (HIRETRACK_BCRYPT_ROUNDS=4) to stay fast.
pwd_context = CryptContext(
    schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=int(os.getenv("HIRETRACK_BCRYPT_ROUNDS", "12"))
)

TOKEN_HOURS = 8
ALGORITHM = "HS256"

ROLE_LABELS = {"admin": "Administrator", "recruiter": "Recruiter (HR)", "resource_manager": "Resource Manager"}

# Shorthand role groups used by the routers.
ANY_ROLE = ("admin", "recruiter", "resource_manager")
HIRING = ("admin", "recruiter")
RESOURCING = ("admin", "resource_manager")
ADMIN = ("admin",)


# ------------------------------------------------------------------ passwords
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str | None, password_hash: str | None) -> bool:
    if not password or not password_hash:
        return False
    try:
        return pwd_context.verify(password, password_hash)
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------- JWT secret
_secret_lock = threading.Lock()
_secret: str | None = None


def jwt_secret() -> str:
    """JWT_SECRET from .env, otherwise a random secret kept in data/.jwt_secret.

    Generating it on first run means a fresh install needs no manual step, and
    keeping it in a file means logins survive a restart.
    """
    global _secret
    if settings.jwt_secret:
        return settings.jwt_secret
    with _secret_lock:
        if _secret:
            return _secret
        path = settings.data_dir / ".jwt_secret"
        if path.exists():
            _secret = path.read_text(encoding="utf-8").strip()
        if not _secret:
            _secret = secrets.token_urlsafe(48)
            path.write_text(_secret, encoding="utf-8")
        return _secret


def create_token(user_id: int, role: str, hours: float = TOKEN_HOURS) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + timedelta(hours=hours)}
    return jwt.encode(payload, jwt_secret(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, jwt_secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("Your session has expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise Unauthorized("Please sign in to continue.") from exc


# ------------------------------------------------------- login rate limiting
# Simple in-memory lockout: 5 failed attempts for one email locks it for 60 s.
MAX_FAILS = 5
LOCK_SECONDS = 60
_fails: dict[str, list[float]] = {}
_fails_lock = threading.Lock()


def check_not_locked(email: str) -> None:
    with _fails_lock:
        recent = [t for t in _fails.get(email, []) if time.monotonic() - t < LOCK_SECONDS]
        _fails[email] = recent
        if len(recent) >= MAX_FAILS:
            wait = int(LOCK_SECONDS - (time.monotonic() - recent[0])) + 1
            raise AppError(
                f"Too many failed sign-in attempts. Try again in {wait} seconds.", field="password", status_code=429
            )


def record_failure(email: str) -> None:
    with _fails_lock:
        _fails.setdefault(email, []).append(time.monotonic())


def clear_failures(email: str) -> None:
    with _fails_lock:
        _fails.pop(email, None)


# ---------------------------------------------------------- dependencies
def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """FastAPI dependency: the logged-in, active user (or 401)."""
    from .models import User

    if not authorization or not authorization.lower().startswith("bearer "):
        raise Unauthorized("Please sign in to continue.")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    try:
        user_id = int(payload.get("sub", ""))
    except ValueError as exc:
        raise Unauthorized("Please sign in to continue.") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise Unauthorized("This account is no longer active.")
    return user


def require_roles(*roles: str):
    """Dependency factory: allow only users whose role is in `roles` (else 403)."""

    def _check(user=Depends(current_user)):
        if user.role not in roles:
            log.warning("Denied user id=%s role=%s (needs %s)", user.user_id, user.role, "/".join(roles))
            raise Forbidden("Your role does not have access to this action.")
        return user

    return _check


def require_confirmed_admin(
    x_confirm_password: str | None = Header(default=None),
    user=Depends(require_roles(*ADMIN)),
):
    """Admin AND the admin's own password re-entered (for destructive actions)."""
    if not verify_password(x_confirm_password, user.password_hash):
        log.warning("Rejected destructive admin action: password not confirmed (user id=%s)", user.user_id)
        raise Unauthorized("Incorrect password", field="password")
    return user
