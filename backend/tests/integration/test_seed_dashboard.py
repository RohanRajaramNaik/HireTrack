"""The full seed dataset and the dashboard built from it."""
from collections import Counter

import pytest
from sqlalchemy import func, select

from tests.helpers import make_application, make_candidate, make_job, move


@pytest.fixture()
def seeded(client):
    from app.database import SessionLocal
    from app.services import seed_service

    with SessionLocal() as db:
        out = seed_service.build_full(db)
    return out


def test_full_dataset_sizes(seeded):
    assert seeded["candidates"] == 600
    assert seeded["jobs"] == 33
    assert seeded["applications"] >= 500
    assert seeded["projects"] == 12
    assert seeded["staff"] >= 50
    assert seeded["allocations"] >= 30


def test_seed_is_deterministic(client):
    from app.database import SessionLocal
    from app.models import Application, Candidate
    from app.services import seed_service

    def snapshot():
        with SessionLocal() as db:
            seed_service.build_full(db)
            names = list(db.scalars(select(Candidate.full_name).order_by(Candidate.candidate_id).limit(40)))
            stages = Counter(db.scalars(select(Application.stage)))
        return names, stages

    assert snapshot() == snapshot()


def test_every_application_history_matches_its_stage(seeded):
    from app.database import SessionLocal
    from app.engine.pipeline import check_move
    from app.models import Application

    with SessionLocal() as db:
        for app in db.scalars(select(Application)).unique():
            ev = app.events
            assert ev[0].from_stage is None and ev[0].to_stage == "applied"
            assert ev[-1].to_stage == app.stage
            for e in ev[1:]:
                check_move(e.from_stage, e.to_stage)  # every recorded move was a legal move
            assert [e.changed_at for e in ev] == sorted(e.changed_at for e in ev)


def test_seeded_staff_never_over_allocated(seeded):
    from app.database import SessionLocal
    from app.engine.allocation import peak_load
    from app.services.resource_service import _bookings, list_staff
    from app.models import StaffMember

    with SessionLocal() as db:
        for s in db.scalars(select(StaffMember)).unique():
            b = _bookings(s.allocations)
            if b:
                start = min(x.start for x in b)
                end = max(x.end for x in b)
                assert peak_load(b, start, end)[0] <= 100
        bands = Counter(x.band for x in list_staff(db))
    assert bands["bench"] > 0 and (bands["healthy"] + bands["full"] + bands["light"]) > 0


def test_every_hire_is_on_staff(seeded):
    from app.database import SessionLocal
    from app.models import Application, StaffMember

    with SessionLocal() as db:
        hired = set(db.scalars(select(Application.candidate_id).where(Application.stage == "hired")))
        staffed = set(db.scalars(select(StaffMember.candidate_id).where(StaffMember.candidate_id.is_not(None))))
        assert hired and hired == staffed
        assert db.scalar(select(func.count()).select_from(Application).where(Application.stage == "hired")) == len(hired)


def test_dashboard_on_full_dataset(client, seeded):
    d = client.get("/api/dashboard").json()
    c = d["counts"]
    assert c["candidates"] == 600 and c["jobs_total"] == 33 and c["jobs_open"] == 30
    assert c["applications_active"] > 0 and c["staff_active"] == seeded["staff"]
    stages = [f["stage"] for f in d["funnel"]]
    assert stages == ["applied", "screened", "interview", "offer", "hired", "rejected"]
    reached = [f["reached"] for f in d["funnel"][:5]]
    assert reached == sorted(reached, reverse=True) and reached[0] == seeded["applications"]
    assert len(d["applications_per_job"]) == 8
    assert len(d["hires_per_month"]) == 6
    assert sum(d["utilisation_bands"].values()) == c["staff_active"]
    assert len(d["recent_activity"]) == 8


def test_dashboard_empty(client):
    d = client.get("/api/dashboard").json()
    assert d["counts"]["candidates"] == 0 and d["counts"]["average_utilisation"] is None
    assert d["applications_per_job"] == [] and d["recent_activity"] == []
    assert d["matching"]["last_run_at"] is None


def test_dashboard_counts_new_activity(client):
    c = make_candidate(client)
    j = make_job(client)
    a = make_application(client, c["candidate_id"], j["job_id"])
    for s in ("screened", "interview", "offer", "hired"):
        move(client, a["application_id"], s)
    d = client.get("/api/dashboard").json()
    assert d["counts"]["hires_30_days"] == 1
    assert d["hires_per_month"][-1]["count"] == 1
    assert d["recent_activity"][0]["to_stage"] == "hired"
    assert d["recent_activity"][0]["candidate_name"] == "Ayanda Zulu"
    assert d["counts"]["staff_bench"] == 1


def test_admin_load_full_dataset_endpoint(client, admin_headers):
    r = client.post("/api/admin/seed-full", headers=admin_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["candidates"] == 600 and body["safety_backup"].endswith("preseed.db")
    # user accounts survive a reset
    assert len(client.get("/api/users").json()) == 3
