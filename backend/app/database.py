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


def init_db() -> None:
    """Create tables and the fixed education_level lookup rows."""
    from . import models  # noqa: F401  (register models)

    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        existing = set(db.scalars(select(models.EducationLevel.level_id)))
        for level_id, name in EDUCATION_LEVELS:
            if level_id not in existing:
                db.add(models.EducationLevel(level_id=level_id, level_name=name))
        db.commit()
