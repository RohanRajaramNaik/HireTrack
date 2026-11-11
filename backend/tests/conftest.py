"""Test configuration: isolate every test run in a temporary data folder.

Environment variables are set before `app` is imported so the engine/session
point at the temporary database, not the real data/hiretrack.db.

Fixtures
- client:        TestClient signed in as the default Administrator
- anon:          TestClient with no sign-in (for 401 tests)
- login(role):   returns Authorization headers for admin / recruiter / resource_manager
- admin_headers: the X-Confirm-Password header destructive admin actions need
"""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="hiretrack-test-")
os.environ["HIRETRACK_DATA_DIR"] = os.path.join(_tmp, "data")
os.environ["HIRETRACK_BACKUP_DIR"] = os.path.join(_tmp, "backups")
os.environ["HIRETRACK_LOG_DIR"] = os.path.join(_tmp, "logs")
os.environ["HIRETRACK_DISABLE_STARTUP_BACKUP"] = "1"
os.environ["HIRETRACK_BCRYPT_ROUNDS"] = "4"  # fast hashing in tests only
os.environ["JWT_SECRET"] = "test-secret-not-used-in-production-0123456789"
# Fast unit tests use the deterministic fallback embedder unless the perf
# tests explicitly opt into the real model (HIRETRACK_REAL_MODEL=1).
if os.environ.get("HIRETRACK_REAL_MODEL") != "1":
    os.environ["HIRETRACK_DISABLE_MODEL"] = "1"

import pytest  # noqa: E402

PASSWORDS = {
    "admin": ("admin@hiretrack.local", "Admin@123"),
    "recruiter": ("recruiter@hiretrack.local", "Recruiter@123"),
    "resource_manager": ("manager@hiretrack.local", "Manager@123"),
}


def _reset_database():
    """Empty every table, then recreate the lookup rows and the default users."""
    from sqlalchemy import delete

    from app import security
    from app.database import SessionLocal, init_db
    from app.models import User
    from app.services.seed_service import _wipe

    init_db()
    with SessionLocal() as db:
        _wipe(db)
        db.execute(delete(User))
        db.commit()
    init_db()
    security._fails.clear()


@pytest.fixture()
def anon():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        _reset_database()
        yield c


def _token(c, role: str) -> str:
    email, password = PASSWORDS[role]
    r = c.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def client(anon):
    anon.headers.update({"Authorization": f"Bearer {_token(anon, 'admin')}"})
    yield anon


@pytest.fixture()
def login(anon):
    """login('recruiter') -> {'Authorization': 'Bearer ...'} for that role."""

    def _login(role: str) -> dict:
        return {"Authorization": f"Bearer {_token(anon, role)}"}

    return _login


@pytest.fixture()
def admin_headers():
    return {"X-Confirm-Password": PASSWORDS["admin"][1]}
