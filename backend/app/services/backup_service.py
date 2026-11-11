"""Database backups using SQLite's online backup API.

- automatic start-up backup, at most once per calendar day
- safety backup before every seed and every restore
- manual backup from the Admin screen
- only the 10 most recent backups are kept
- PRAGMA integrity_check is run on a backup before it is restored
"""
from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from ..config import settings
from ..database import engine
from ..errors import AppError, NotFound

log = logging.getLogger("hiretrack.backup")

NAME_RE = re.compile(r"^hiretrack-(\d{8}-\d{6}(?:-\d{3})?)-([a-z]+)\.db$")
REASONS = {"startup", "manual", "pre-seed", "pre-restore"}


def _reason_slug(reason: str) -> str:
    return reason.replace("-", "")


def _list_paths() -> list[Path]:
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    files = [p for p in settings.backup_dir.glob("hiretrack-*.db") if NAME_RE.match(p.name)]
    return sorted(files, key=lambda p: p.name, reverse=True)


def list_backups() -> list[dict]:
    out = []
    for p in _list_paths():
        m = NAME_RE.match(p.name)
        stamp = m.group(1)
        created = datetime.strptime(stamp[:15], "%Y%m%d-%H%M%S").astimezone()  # local, tz-aware
        out.append(
            {
                "file": p.name,
                "size_bytes": p.stat().st_size,
                "created_at": created,
                "reason": {"preseed": "Before loading data", "prerestore": "Before restore",
                           "startup": "Daily start-up", "manual": "Manual"}.get(m.group(2), m.group(2)),
            }
        )
    return out


def create_backup(reason: str = "manual") -> dict:
    """Copy the live database to backups/ with the online backup API."""
    assert reason in REASONS
    settings.backup_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    name = f"hiretrack-{now:%Y%m%d-%H%M%S}-{now.microsecond // 1000:03d}-{_reason_slug(reason)}.db"
    dest_path = settings.backup_dir / name
    src = sqlite3.connect(settings.db_path)
    dest = sqlite3.connect(dest_path)
    try:
        with dest:
            src.backup(dest)
    finally:
        dest.close()
        src.close()
    log.info("Backup created: %s (%s)", name, reason)
    prune()
    return next(b for b in list_backups() if b["file"] == name)


def prune(keep: int | None = None) -> None:
    keep = keep or settings.max_backups
    for old in _list_paths()[keep:]:
        try:
            old.unlink()
            log.info("Pruned old backup %s", old.name)
        except OSError:  # pragma: no cover
            log.warning("Could not delete old backup %s", old.name)


def startup_backup() -> None:
    """Back up once per day when the app starts (skipped for an empty/new DB)."""
    if not settings.db_path.exists() or settings.db_path.stat().st_size == 0:
        return
    today = datetime.now().strftime("%Y%m%d")
    if any(p.name.startswith(f"hiretrack-{today}") and p.name.endswith("-startup.db") for p in _list_paths()):
        return
    create_backup("startup")


def _resolve(file_name: str) -> Path:
    # Only accept our own naming pattern: no path separators, no traversal.
    if not NAME_RE.match(file_name):
        raise AppError("Unknown backup file name", field="file")
    path = settings.backup_dir / file_name
    if not path.exists():
        raise NotFound(f"Backup {file_name} not found", field="file")
    return path


def integrity_ok(path: Path) -> bool:
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        return con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    except sqlite3.DatabaseError:
        return False
    finally:
        con.close()


def restore_backup(file_name: str) -> dict:
    """Integrity-check a backup, take a safety backup, then copy it over the live DB."""
    path = _resolve(file_name)
    if not integrity_ok(path):
        raise AppError("This backup failed its integrity check and was not restored.", field="file")
    # Load the chosen backup into memory first: the safety backup below may
    # prune the oldest file, which could be the one being restored.
    mem = sqlite3.connect(":memory:")
    src = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        src.backup(mem)
    finally:
        src.close()
    safety = create_backup("pre-restore")
    engine.dispose()  # close pooled connections before overwriting
    dest = sqlite3.connect(settings.db_path)
    try:
        with dest:
            mem.backup(dest)
    finally:
        mem.close()
        dest.close()
    engine.dispose()
    # A backup made by an older build may be missing newer tables or columns
    # (or the user accounts); init_db adds them without touching existing rows.
    from ..database import init_db

    init_db()
    log.info("Restored database from %s (safety backup %s)", file_name, safety["file"])
    return {"restored": file_name, "safety_backup": safety["file"]}
