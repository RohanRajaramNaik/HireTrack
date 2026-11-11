"""SQLAlchemy engine/session setup for SQLite.

PRAGMA foreign_keys=ON is applied on *every* new DBAPI connection so cascades
and FK checks are always enforced.
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

EDUCATION_LEVELS: list[tuple[int, str]] = [
    (1, "Matric"),
    (2, "Higher Certificate"),
    (3, "Diploma"),
    (4, "Bachelor's Degree"),
    (5, "Honours"),
    (6, "Master's"),
    (7, "Doctorate"),
]


class Base(DeclarativeBase):
    pass


settings.ensure_dirs()

engine: Engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    future=True,
)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _record) -> None:  # pragma: no cover - trivial
    cur = dbapi_connection.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Default accounts created on first run (one per role). The installation guide
# lists them and tells the administrator to change the passwords.
DEFAULT_USERS: list[dict] = [
    {"full_name": "System Administrator", "email": "admin@hiretrack.local", "password": "Admin@123", "role": "admin"},
    {"full_name": "Nomvula Khumalo", "email": "recruiter@hiretrack.local", "password": "Recruiter@123", "role": "recruiter"},
    {"full_name": "Pieter Botha", "email": "manager@hiretrack.local", "password": "Manager@123", "role": "resource_manager"},
]

# Columns added in Phase 5. Databases (and backups) made by the Phase 4 build
# do not have them, so they are added in place with a safe default.
_UPGRADE_COLUMNS = [
    ("candidate", "phone", "VARCHAR(30)"),
    ("candidate", "location", "VARCHAR(80)"),
    ("job_specification", "location", "VARCHAR(80) NOT NULL DEFAULT 'Johannesburg'"),
    ("job_specification", "status", "VARCHAR(10) NOT NULL DEFAULT 'open'"),
]


def _upgrade_schema() -> None:
    with engine.begin() as conn:
        for table, column, ddl in _UPGRADE_COLUMNS:
            cols = {row[1] for row in conn.exec_driver_sql(f"PRAGMA table_info({table})")}
            if cols and column not in cols:
                conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    """Create tables, the fixed education_level rows and the default users."""
    from . import models  # noqa: F401  (register models)
    from .security import hash_password

    Base.metadata.create_all(engine)
    _upgrade_schema()
    with SessionLocal() as db:
        existing = set(db.scalars(select(models.EducationLevel.level_id)))
        for level_id, name in EDUCATION_LEVELS:
            if level_id not in existing:
                db.add(models.EducationLevel(level_id=level_id, level_name=name))
        if db.scalar(select(models.User.user_id).limit(1)) is None:
            for u in DEFAULT_USERS:
                db.add(
                    models.User(
                        full_name=u["full_name"],
                        email=u["email"],
                        password_hash=hash_password(u["password"]),
                        role=u["role"],
                    )
                )
        db.commit()
