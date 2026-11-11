"""Demo and seed data loading.

- load_demo:  wipe business data and load seed/dummy_candidates.json (18 candidates, 3 jobs).
              Used by the guided demo and by most tests because it is small.
- load_full:  the realistic dataset described in the installation guide:
              600 candidates, 33 jobs, ~800 applications with stage history,
              staff, 12 projects and allocations. Used by seed/seed_database.py
              and by Admin > "Load full dataset".
- load_large: load_full plus ~2,000 extra generated candidates (scale testing).
- demo_start: guided demo; loads the small demo data ONLY when the database is empty.

User accounts are never wiped. A safety backup is taken before every
destructive load started from the Admin screen. All data is fictitious.
"""
from __future__ import annotations

import json
import logging
import random
import sys
import threading
import time
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..engine.allocation import Booking, check_new_booking
from ..engine.embeddings import embedder
from ..engine.pipeline import FLOW
from ..engine.skills import normaliser
from ..models import (
    Allocation,
    Application,
    ApplicationEvent,
    Candidate,
    CandidateSkill,
    JobSkill,
    JobSpecification,
    MatchResult,
    MatchRun,
    Project,
    Skill,
    StaffMember,
    User,
)
from . import backup_service
from .candidate_service import get_or_create_skills

log = logging.getLogger("hiretrack.seed")

DEMO_JOB_TITLE = "Cloud Data Engineer"
FULL_CANDIDATES = 600  # 18 hand-written + 582 generated
LEVEL_IDS = {
    "matric": 1, "higher certificate": 2, "diploma": 3, "bachelor's degree": 4,
    "honours": 5, "master's": 6, "doctorate": 7,
}


def _seed_module(name: str):
    """Import a module from the top-level seed/ package."""
    root = str(settings.seed_dir.parent)
    if root not in sys.path:
        sys.path.insert(0, root)
    return __import__(f"seed.{name}", fromlist=["*"])


def _seed_file() -> dict:
    return json.loads((settings.seed_dir / "dummy_candidates.json").read_text(encoding="utf-8"))


def _level(value) -> int:
    if isinstance(value, int):
        return value
    return LEVEL_IDS[str(value).strip().lower()]


def _wipe(db: Session) -> None:
    """Delete all business data (children first). User accounts are kept."""
    for model in (
        Allocation, Project, StaffMember, ApplicationEvent, Application,
        MatchResult, MatchRun, JobSkill, CandidateSkill, JobSpecification, Candidate, Skill,
    ):
        db.execute(delete(model))
    db.flush()


def _insert_candidates(db: Session, rows: list[dict]) -> int:
    all_names = {n for r in rows for n in normaliser.normalise_many(r["skills"])}
    skills = get_or_create_skills(db, sorted(all_names))
    for r in rows:
        c = Candidate(
            full_name=r["full_name"],
            email=r.get("email"),
            phone=r.get("phone"),
            location=r.get("location"),
            years_experience=r["years_experience"],
            level_id=_level(r["education"]),
            previous_titles=r.get("previous_titles"),
            resume_summary=r["resume_summary"],
        )
        c.skills = [
            CandidateSkill(skill_id=skills[canon].skill_id, entered_as=entered[:60])
            for canon, entered in normaliser.normalise_with_source(r["skills"])
        ]
        db.add(c)
    db.flush()
    return len(rows)


def _insert_job(db: Session, j: dict, created_by: str | None = None) -> JobSpecification:
    req = normaliser.normalise_many(j["required_skills"])
    pref = [p for p in normaliser.normalise_many(j.get("preferred_skills", [])) if p not in req]
    skills = get_or_create_skills(db, req + pref)
    w = j.get("weights", {})
    job = JobSpecification(
        job_title=j["job_title"],
        created_by=j.get("created_by") or created_by,
        location=j.get("location", "Johannesburg"),
        status=j.get("status", "open"),
        min_experience=j["min_experience"],
        min_level_id=_level(j["min_education"]),
        job_description=j["job_description"],
        w_skills=w.get("skills", 40),
        w_experience=w.get("experience", 25),
        w_education=w.get("education", 15),
        w_semantic=w.get("semantic", 20),
    )
    job.skills = [JobSkill(skill_id=skills[n].skill_id, skill_type="required") for n in req] + [
        JobSkill(skill_id=skills[n].skill_id, skill_type="preferred") for n in pref
    ]
    db.add(job)
    db.flush()
    return job


def _load(db: Session, extra: list[dict] | None = None, extra_jobs: list[dict] | None = None) -> dict:
    data = _seed_file()
    try:
        _wipe(db)
        n = _insert_candidates(db, data["candidates"])
        if extra:
            n += _insert_candidates(db, extra)
        jobs = [_insert_job(db, j) for j in data["jobs"]]
        recruiter = db.scalar(select(User.full_name).where(User.role == "recruiter").limit(1))
        jobs += [_insert_job(db, j, created_by=recruiter) for j in (extra_jobs or [])]
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Seeding failed; rolled back")
        raise
    log.info("Seeded %d candidates and %d jobs", n, len(jobs))
    return {"candidates": n, "jobs": len(jobs)}


def load_demo(db: Session, backup: bool = True) -> dict:
    safety = backup_service.create_backup("pre-seed") if backup else None
    out = _load(db)
    warm_embeddings_async()
    out["safety_backup"] = safety["file"] if safety else None
    return out


def build_full(db: Session, extra_candidates: int = FULL_CANDIDATES - 18, today: date | None = None) -> dict:
    """Wipe and load the full realistic dataset. No backup; callers decide."""
    generate = _seed_module("generate_large_dataset").generate
    catalogue = _seed_module("catalogue")
    out = _load(db, extra=generate(extra_candidates), extra_jobs=catalogue.JOBS)
    try:
        activity = _seed_activity(db, catalogue, today or date.today())
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Seeding pipeline/resource data failed; rolled back")
        raise
    out.update(activity)
    return out


def load_full(db: Session, backup: bool = True) -> dict:
    safety = backup_service.create_backup("pre-seed") if backup else None
    out = build_full(db)
    warm_embeddings_async()
    out["safety_backup"] = safety["file"] if safety else None
    return out


def load_large(db: Session) -> dict:
    safety = backup_service.create_backup("pre-seed")
    out = build_full(db, extra_candidates=FULL_CANDIDATES - 18 + 2000)
    warm_embeddings_async()
    out["safety_backup"] = safety["file"]
    return out


def demo_start(db: Session) -> dict:
    seeded = False
    if (db.scalar(select(func.count(Candidate.candidate_id))) or 0) == 0:
        _load(db)
        warm_embeddings_async()
        seeded = True
    job = db.scalar(
        select(JobSpecification)
        .where(JobSpecification.job_title == DEMO_JOB_TITLE)
        .order_by(JobSpecification.job_id)
        .limit(1)
    )
    if job is None:
        spec = next(j for j in _seed_file()["jobs"] if j["job_title"] == DEMO_JOB_TITLE)
        job = _insert_job(db, spec)
        db.commit()
    return {"job_id": job.job_id, "seeded": seeded}


# --------------------------------------------------------------------------
# Pipeline and resource-allocation activity for the full dataset
# --------------------------------------------------------------------------
# Share of applications that end at each stage (rejections are added separately).
_STAGE_MIX = [("applied", 34), ("screened", 22), ("interview", 14), ("offer", 5), ("rejected", 25)]


def _when(base: datetime, rng: random.Random, max_days: int) -> datetime:
    return base + timedelta(days=rng.randint(1, max(1, max_days)), hours=rng.randint(0, 8), minutes=rng.randint(0, 59))


def _spread(start: datetime, end: datetime, steps: int, rng: random.Random) -> list[datetime]:
    """`steps` increasing times after `start` and before `end` (working hours only)."""
    out, at = [], start
    for i in range(steps):
        left = (end - at).total_seconds()
        share = left / (steps - i + 1)
        at = at + timedelta(seconds=share * rng.uniform(0.35, 1.0))
        at = at.replace(hour=max(8, min(at.hour, 16)), minute=rng.randint(0, 59))
        if at <= (out[-1] if out else start):
            at = (out[-1] if out else start) + timedelta(hours=1)
        out.append(min(at, end))
    return out


def _seed_activity(db: Session, catalogue, today: date) -> dict:
    rng = random.Random(20261109)
    users = {u.role: u.user_id for u in db.scalars(select(User).order_by(User.user_id))}
    recruiter_id = users.get("recruiter") or users.get("admin")
    # Activity ends a little before "now" so nothing appears to happen in the future.
    if today == date.today():
        now = datetime.now() - timedelta(hours=2)
    else:
        now = datetime.combine(today, datetime.min.time()) + timedelta(hours=17)

    # Candidate skill sets, for choosing realistic applicants for each job.
    cand_skills: dict[int, set[str]] = {}
    for cid, name in db.execute(
        select(CandidateSkill.candidate_id, Skill.name).join(Skill, Skill.skill_id == CandidateSkill.skill_id)
    ):
        cand_skills.setdefault(cid, set()).add(name)
    cands = {c.candidate_id: c for c in db.scalars(select(Candidate))}
    jobs = list(db.scalars(select(JobSpecification).order_by(JobSpecification.job_id)))
    hired_ids: set[int] = set()
    n_apps = 0
    n_events = 0

    for job in jobs:
        req = {s.skill.name for s in job.skills if s.skill_type == "required"}
        pref = {s.skill.name for s in job.skills if s.skill_type == "preferred"}
        # Rank the pool by overlap so most applicants are plausible, then add some noise.
        scored = sorted(
            cands,
            key=lambda cid: (len(cand_skills.get(cid, set()) & req) * 3 + len(cand_skills.get(cid, set()) & pref), rng.random()),
            reverse=True,
        )
        plausible = scored[:80]
        take = rng.randint(14, 34)
        chosen = rng.sample(plausible, k=min(take, len(plausible)))
        chosen += rng.sample(scored[80:], k=min(rng.randint(1, 4), len(scored) - 80))
        hires_left = 1 if job.status == "open" else rng.randint(1, 2)
        opened = now - timedelta(days=rng.randint(20, 120))
        for cid in chosen:
            stage = rng.choices([s for s, _ in _STAGE_MIX], [w for _, w in _STAGE_MIX])[0]
            if hires_left and cid not in hired_ids and rng.random() < (0.5 if job.status == "closed" else 0.06):
                stage = "hired"
            if stage == "hired":
                hires_left -= 1
                hired_ids.add(cid)
            applied_at = min(_when(opened, rng, 25), now - timedelta(days=1))
            app = Application(candidate_id=cid, job_id=job.job_id, stage=stage, applied_at=applied_at)
            # Build the stage history up to the final stage.
            path = list(FLOW[: FLOW.index(stage) + 1]) if stage != "rejected" else None
            if path is None:
                stop = rng.choices(["applied", "screened", "interview", "offer"], [45, 30, 20, 5])[0]
                path = list(FLOW[: FLOW.index(stop) + 1]) + ["rejected"]
            times = [applied_at] + _spread(applied_at, now, len(path) - 1, rng)
            at = applied_at
            prev = None
            notes = {
                "screened": "CV meets the minimum requirements",
                "interview": "Invited to a technical interview",
                "offer": "Offer sent",
                "hired": "Offer accepted",
                "rejected": rng.choice(
                    ["Not enough relevant experience", "Missing required skills", "Withdrew application",
                     "Position filled by another candidate", "Did not attend interview"]
                ),
            }
            for st, at in zip(path, times):
                app.events.append(
                    ApplicationEvent(
                        from_stage=prev, to_stage=st, changed_by=recruiter_id, changed_at=at,
                        note=None if st == "applied" else notes.get(st),
                    )
                )
                prev = st
                n_events += 1
            app.updated_at = at
            db.add(app)
            n_apps += 1
    db.flush()

    # Someone who accepted an offer withdraws from their other open applications.
    for a in db.scalars(select(Application).where(Application.candidate_id.in_(hired_ids))).unique().all():
        if a.stage in ("hired", "rejected"):
            continue
        at = min(now, a.updated_at + timedelta(days=1, hours=2))
        a.events.append(
            ApplicationEvent(
                from_stage=a.stage, to_stage="rejected", changed_by=recruiter_id, changed_at=at,
                note="Withdrew: accepted another offer",
            )
        )
        a.stage = "rejected"
        a.updated_at = at
        n_events += 1
    db.flush()

    # Staff: everyone hired through the pipeline, plus existing staff.
    hired_apps = db.scalars(select(Application).where(Application.stage == "hired")).all()
    staff: list[tuple[StaffMember, str]] = []
    family_of_title = {t: fam for fam, titles in catalogue.STAFF_ROLES.items() for t in titles}
    for a in hired_apps:
        c = cands[a.candidate_id]
        s = StaffMember(
            full_name=c.full_name, email=c.email, role_title=a.job.job_title,
            location=c.location or a.job.location, candidate_id=c.candidate_id, source="hired",
        )
        db.add(s)
        staff.append((s, _family_for_title(a.job.job_title)))
    gen = _seed_module("generate_large_dataset")
    used_names = {c.full_name for c in cands.values()}
    for fam, titles in catalogue.STAFF_ROLES.items():
        for _ in range({"software": 9, "data": 7, "cloud": 6, "bi": 6, "qa": 5, "security": 4, "support": 6}[fam]):
            name = f"{rng.choice(gen.FIRST_NAMES)} {rng.choice(gen.SURNAMES)}"
            while name in used_names:
                name = f"{rng.choice(gen.FIRST_NAMES)} {rng.choice(gen.SURNAMES)}"
            used_names.add(name)
            title = rng.choice(titles)
            s = StaffMember(
                full_name=name,
                email=name.lower().replace(" ", ".") + "@staff.hiretrack.local",
                role_title=title,
                location=rng.choices(gen.LOCATIONS, gen.LOCATION_WEIGHTS)[0],
                source="existing",
            )
            db.add(s)
            staff.append((s, family_of_title.get(title, fam)))
    db.flush()

    # Projects and allocations. A share of staff is deliberately left on the bench.
    projects = []
    for p in catalogue.PROJECTS:
        proj = Project(
            name=p["name"], client=p["client"], description=p["description"], status=p["status"],
            start_date=today + timedelta(days=p["start"]), end_date=today + timedelta(days=p["end"]),
        )
        db.add(proj)
        projects.append(proj)
    db.flush()
    bookings: dict[int, list[Booking]] = {}
    # About one in eight people is left on the bench, which is realistic and
    # gives the Resource Manager someone to allocate in a demonstration.
    bench = {s.staff_id for s, _ in rng.sample(staff, k=max(1, len(staff) // 8))}
    n_alloc = 0

    def book(s, proj, pct, start, end) -> bool:
        nonlocal n_alloc
        if end < start:
            return False
        new = Booking(pct, start, end)
        if proj.status in ("planned", "active"):
            try:
                check_new_booking(bookings.get(s.staff_id, []), new)
            except ValueError:
                return False
            bookings.setdefault(s.staff_id, []).append(new)
        db.add(
            Allocation(
                staff_id=s.staff_id, project_id=proj.project_id, allocation_percent=pct,
                start_date=start, end_date=end, role_on_project=s.role_title,
            )
        )
        n_alloc += 1
        return True

    for proj in projects:
        needs = catalogue.PROJECT_NEEDS.get(proj.name, ["software"])
        pool = [s for s, fam in staff if fam in needs and s.staff_id not in bench]
        rng.shuffle(pool)
        for s in pool[: rng.randint(4, 9)]:
            pct = rng.choice([20, 30, 40, 50, 50, 60, 80, 100])
            start = proj.start_date + timedelta(days=rng.randint(0, 20))
            end = min(proj.end_date, start + timedelta(days=rng.randint(60, 240)))
            book(s, proj, pct, start, end)

    # Second pass: anyone still free today (and not on the bench list) joins an
    # active project that needs their skills, from today to the project's end.
    active = [p for p in projects if p.status == "active" and p.start_date <= today <= p.end_date]
    for s, fam in staff:
        if s.staff_id in bench or any(b.start <= today <= b.end for b in bookings.get(s.staff_id, [])):
            continue
        fits = [p for p in active if fam in catalogue.PROJECT_NEEDS.get(p.name, [])] or active
        if fits:
            p = rng.choice(fits)
            book(s, p, rng.choice([40, 50, 60, 80, 100]), today - timedelta(days=rng.randint(0, 14)), p.end_date)
    db.flush()
    log.info("Seeded %d applications, %d events, %d staff, %d projects, %d allocations",
             n_apps, n_events, len(staff), len(projects), n_alloc)
    return {
        "applications": n_apps,
        "events": n_events,
        "staff": len(staff),
        "projects": len(projects),
        "allocations": n_alloc,
    }


def _family_for_title(title: str) -> str:
    t = title.lower()
    for key, fam in (
        ("data scien", "data"), ("data", "data"), ("analytics", "data"), ("bi ", "bi"), ("analyst", "bi"),
        ("security", "security"), ("penetration", "security"), ("cloud", "cloud"), ("devops", "cloud"),
        ("reliability", "cloud"), ("azure", "cloud"), ("qa", "qa"), ("test", "qa"), ("network", "support"),
        ("support", "support"), ("service desk", "support"), ("database", "support"), ("project", "support"),
    ):
        if key in t:
            return fam
    return "software"


# --------------------------------------------------------------------------
# Embedding warm-up: encode every CV summary in the background so the first
# match on a large dataset is fast.
# --------------------------------------------------------------------------
_warm_lock = threading.Lock()


def warm_embeddings(batch: int = 256, wait: bool = False) -> None:
    """Encode every CV summary not yet cached, then persist the cache to disk.

    wait=False (background use) returns at once if a warm-up is already running;
    wait=True blocks until that run has finished and then tops up.
    """
    from ..database import SessionLocal

    if not _warm_lock.acquire(blocking=wait):
        return
    try:
        started = time.perf_counter()
        embedder.warm_up()
        with SessionLocal() as db:
            texts = list(db.scalars(select(Candidate.resume_summary)))
        for i in range(0, len(texts), batch):
            embedder.encode(texts[i : i + batch])
        embedder.save()
        log.info("Embedding cache warm: %d texts in %.1fs", len(texts), time.perf_counter() - started)
    except Exception:  # pragma: no cover
        log.exception("Embedding warm-up failed")
    finally:
        _warm_lock.release()


def warm_embeddings_async() -> None:
    threading.Thread(target=warm_embeddings, name="embedding-warmup", daemon=True).start()
