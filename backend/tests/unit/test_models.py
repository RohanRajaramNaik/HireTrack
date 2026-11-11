"""Model / database tests: constraints are the last line of defence (Design 4.5).

These write directly through the ORM, bypassing API validation, to prove the
SQLite CHECK, UNIQUE and FOREIGN KEY rules reject bad data on their own.
"""
from datetime import date

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError


@pytest.fixture()
def db(anon):
    from app.database import SessionLocal

    with SessionLocal() as s:
        yield s
        s.rollback()


def _cand(**over):
    from app.models import Candidate

    data = dict(full_name="Test Person", years_experience=3, level_id=4, resume_summary="x" * 30)
    data.update(over)
    return Candidate(**data)


def _job(**over):
    from app.models import JobSpecification

    data = dict(job_title="Tester", location="Durban", min_experience=1, min_level_id=3, job_description="y" * 30)
    data.update(over)
    return JobSpecification(**data)


def _commit_fails(db, obj):
    db.add(obj)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.parametrize(
    "over", [{"years_experience": -1}, {"years_experience": 51}, {"full_name": "A"}, {"resume_summary": "short"}, {"level_id": 9}]
)
def test_candidate_checks(db, over):
    _commit_fails(db, _cand(**over))


@pytest.mark.parametrize(
    "over",
    [{"w_skills": 50}, {"status": "paused"}, {"location": "X"}, {"min_experience": 60}, {"job_description": "short"}],
)
def test_job_checks(db, over):
    _commit_fails(db, _job(**over))


def test_application_unique_and_stage(db):
    from app.models import Application

    c, j = _cand(), _job()
    db.add_all([c, j])
    db.commit()
    db.add(Application(candidate_id=c.candidate_id, job_id=j.job_id, stage="applied"))
    db.commit()
    _commit_fails(db, Application(candidate_id=c.candidate_id, job_id=j.job_id, stage="applied"))
    c2 = _cand(full_name="Other Person")
    db.add(c2)
    db.commit()
    _commit_fails(db, Application(candidate_id=c2.candidate_id, job_id=j.job_id, stage="archived"))


def test_foreign_keys_enforced(db):
    from app.models import Application

    _commit_fails(db, Application(candidate_id=9999, job_id=9999, stage="applied"))


def test_cascade_delete_candidate_removes_applications_and_events(db):
    from app.models import Application, ApplicationEvent

    c, j = _cand(), _job()
    db.add_all([c, j])
    db.commit()
    a = Application(candidate_id=c.candidate_id, job_id=j.job_id, stage="applied")
    a.events.append(ApplicationEvent(from_stage=None, to_stage="applied"))
    db.add(a)
    db.commit()
    db.delete(c)
    db.commit()
    assert db.scalars(select(Application)).all() == []
    assert db.scalars(select(ApplicationEvent)).all() == []


@pytest.mark.parametrize("over", [{"allocation_percent": 0}, {"allocation_percent": 101}, {"end_date": date(2025, 12, 31)}])
def test_allocation_checks(db, over):
    from app.models import Allocation, Project, StaffMember

    s = StaffMember(full_name="Staff One", role_title="Dev")
    p = Project(name="P1", client="C1", start_date=date(2026, 1, 1), end_date=date(2026, 12, 31))
    db.add_all([s, p])
    db.commit()
    data = dict(staff_id=s.staff_id, project_id=p.project_id, allocation_percent=50,
                start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
    data.update(over)
    _commit_fails(db, Allocation(**data))


def test_project_dates_and_status(db):
    from app.models import Project

    _commit_fails(db, Project(name="Bad", client="C", start_date=date(2026, 2, 1), end_date=date(2026, 1, 1)))
    _commit_fails(db, Project(name="Bad2", client="C", start_date=date(2026, 1, 1), end_date=date(2026, 2, 1), status="x"))


def test_user_role_and_email_rules(db):
    from app.models import User

    _commit_fails(db, User(full_name="A B", email="x@y.z", password_hash="h", role="superuser"))
    _commit_fails(db, User(full_name="A B", email="Upper@Case.z", password_hash="h", role="admin"))
    _commit_fails(db, User(full_name="A B", email="admin@hiretrack.local", password_hash="h", role="admin"))


def test_staff_candidate_link_unique(db):
    from app.models import StaffMember

    c = _cand()
    db.add(c)
    db.commit()
    db.add(StaffMember(full_name="S One", role_title="Dev", candidate_id=c.candidate_id, source="hired"))
    db.commit()
    _commit_fails(db, StaffMember(full_name="S Two", role_title="Dev", candidate_id=c.candidate_id, source="hired"))


def test_default_users_created_once(anon):
    from sqlalchemy import func

    from app.database import SessionLocal, init_db
    from app.models import User

    init_db()
    init_db()
    with SessionLocal() as s:
        assert s.scalar(select(func.count(User.user_id))) == 3


def test_upgrade_adds_missing_columns(tmp_path):
    """A Phase 4 database (no location/status/phone) is upgraded in place."""
    import sqlite3

    from sqlalchemy import create_engine

    from app import database

    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE candidate (candidate_id INTEGER PRIMARY KEY, full_name TEXT)")
    con.execute("CREATE TABLE job_specification (job_id INTEGER PRIMARY KEY, job_title TEXT)")
    con.execute("INSERT INTO job_specification (job_title) VALUES ('Old job')")
    con.commit()
    con.close()
    old_engine = database.engine
    database.engine = create_engine(f"sqlite:///{path.as_posix()}")
    try:
        database._upgrade_schema()
    finally:
        database.engine.dispose()
        database.engine = old_engine
    con = sqlite3.connect(path)
    cols = {r[1] for r in con.execute("PRAGMA table_info(job_specification)")}
    assert {"location", "status"} <= cols
    assert con.execute("SELECT location, status FROM job_specification").fetchone() == ("Johannesburg", "open")
    assert {"phone", "location"} <= {r[1] for r in con.execute("PRAGMA table_info(candidate)")}
    con.close()
