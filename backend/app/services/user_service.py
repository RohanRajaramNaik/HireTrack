"""User accounts: sign-in, profile and administration."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..errors import AppError, Conflict, NotFound, Unauthorized
from ..models import User, utcnow
from ..schemas import LoginIn, PasswordChangeIn, TokenOut, UserIn, UserOut
from ..security import (
    TOKEN_HOURS,
    check_not_locked,
    clear_failures,
    create_token,
    hash_password,
    record_failure,
    verify_password,
)

log = logging.getLogger("hiretrack.users")


def login(db: Session, data: LoginIn) -> TokenOut:
    check_not_locked(data.email)
    user = db.scalar(select(User).where(User.email == data.email))
    # Same message whether the email or the password is wrong, so the
    # response does not reveal which accounts exist.
    if user is None or not verify_password(data.password, user.password_hash):
        record_failure(data.email)
        log.warning("Failed sign-in")
        raise Unauthorized("Incorrect email or password", field="password")
    if not user.is_active:
        raise Unauthorized("This account has been deactivated. Contact the administrator.", field="email")
    clear_failures(data.email)
    user.last_login_at = utcnow()
    db.commit()
    log.info("User id=%s signed in", user.user_id)
    return TokenOut(
        access_token=create_token(user.user_id, user.role),
        expires_in=TOKEN_HOURS * 3600,
        user=UserOut.model_validate(user),
    )


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.role, func.lower(User.full_name))))


def _get(db: Session, user_id: int) -> User:
    u = db.get(User, user_id)
    if u is None:
        raise NotFound(f"User {user_id} not found")
    return u


def _email_taken(db: Session, email: str, except_id: int | None = None) -> bool:
    q = select(User.user_id).where(User.email == email)
    if except_id is not None:
        q = q.where(User.user_id != except_id)
    return db.scalar(q) is not None


def _active_admins(db: Session) -> int:
    return db.scalar(select(func.count(User.user_id)).where(User.role == "admin", User.is_active.is_(True))) or 0


def create_user(db: Session, data: UserIn) -> User:
    if not data.password:
        raise AppError("Set a password for the new user", field="password", status_code=422)
    if _email_taken(db, data.email):
        raise Conflict("A user with this email already exists", field="email")
    u = User(
        full_name=data.full_name,
        email=data.email,
        role=data.role,
        is_active=data.is_active,
        password_hash=hash_password(data.password),
    )
    db.add(u)
    db.commit()
    log.info("Created user id=%s role=%s", u.user_id, u.role)
    return u


def update_user(db: Session, user_id: int, data: UserIn, acting: User) -> User:
    u = _get(db, user_id)
    if _email_taken(db, data.email, except_id=user_id):
        raise Conflict("A user with this email already exists", field="email")
    losing_admin = u.role == "admin" and u.is_active and (data.role != "admin" or not data.is_active)
    if losing_admin and _active_admins(db) <= 1:
        raise AppError("There must always be at least one active administrator", field="role", status_code=422)
    if u.user_id == acting.user_id and not data.is_active:
        raise AppError("You cannot deactivate your own account", field="is_active", status_code=422)
    u.full_name = data.full_name
    u.email = data.email
    u.role = data.role
    u.is_active = data.is_active
    if data.password:
        u.password_hash = hash_password(data.password)
    db.commit()
    log.info("Updated user id=%s", user_id)
    return u


def change_password(db: Session, user: User, data: PasswordChangeIn) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise Unauthorized("Your current password is incorrect", field="current_password")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    log.info("User id=%s changed their password", user.user_id)
