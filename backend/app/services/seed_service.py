"""Demo data loading.

- load_demo:  wipe everything and load seed/dummy_candidates.json (18 + 3 jobs)
- load_large: same, plus ~2,000 generated candidates (seed/generate_large_dataset.py)
- demo_start: guided demo; loads demo data ONLY when the database is empty
A safety backup is taken before every destructive load.
"""
from __future__ import annotations

import json
import logging
import threading
import time

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..engine.embeddings import embedder
from ..engine.skills import normaliser
from ..models import (
    Candidate,
    CandidateSkill,
    JobSkill,
    JobSpecification,
    MatchResult,
    MatchRun,
    Skill,
)
from . import backup_service
from .candidate_service import get_or_create_skills

log = logging.getLogger("hiretrack.seed")

DEMO_JOB_TITLE = "Cloud Data Engineer"
LEVEL_IDS = {
    "matric": 1, "higher certificate": 2, "diploma": 3, "bachelor's degree": 4,
    "honours": 5, "master's": 6, "doctorate": 7,
}


def _seed_file() -> dict:
    return json.loads((settings.seed_dir / "dummy_candidates.json").read_text(encoding="utf-8"))


def _level(value) -> int:
    if isinstance(value, int):
        return value
    return LEVEL_IDS[str(value).strip().lower()]


def _wipe(db: Session) -> None:
    for model in (MatchResult, MatchRun, JobSkill, CandidateSkill, JobSpecification, Candidate, Skill):
        db.execute(delete(model))
    db.flush()


def _insert_candidates(db: Session, rows: list[dict]) -> int:
    all_names = {n for r in rows for n in normaliser.normalise_many(r["skills"])}
    skills = get_or_create_skills(db, sorted(all_names))
    for r in rows:
        c = Candidate(
            full_name=r["full_name"],
            email=r.get("email"),
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


def _insert_job(db: Session, j: dict) -> JobSpecification:
    req = normaliser.normalise_many(j["required_skills"])
    pref = [p for p in normaliser.normalise_many(j.get("preferred_skills", [])) if p not in req]
    skills = get_or_create_skills(db, req + pref)
    w = j.get("weights", {})
    job = JobSpecification(
        job_title=j["job_title"],
        created_by=j.get("created_by"),
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


def _load(db: Session, extra: list[dict] | None = None) -> dict:
    data = _seed_file()
    try:
        _wipe(db)
        n = _insert_candidates(db, data["candidates"])
        if extra:
            n += _insert_candidates(db, extra)
        jobs = [_insert_job(db, j) for j in data["jobs"]]
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Seeding failed; rolled back")
        raise
    log.info("Seeded %d candidates and %d jobs", n, len(jobs))
    warm_embeddings_async()
    return {"candidates": n, "jobs": len(jobs)}


def load_demo(db: Session, backup: bool = True) -> dict:
    safety = backup_service.create_backup("pre-seed") if backup else None
    out = _load(db)
    out["safety_backup"] = safety["file"] if safety else None
    return out


def load_large(db: Session) -> dict:
    import sys

    if str(settings.seed_dir.parent) not in sys.path:
        sys.path.insert(0, str(settings.seed_dir.parent))
    from seed.generate_large_dataset import generate

    safety = backup_service.create_backup("pre-seed")
    out = _load(db, extra=generate())
    out["safety_backup"] = safety["file"]
    return out


def demo_start(db: Session) -> dict:
    seeded = False
    if (db.scalar(select(func.count(Candidate.candidate_id))) or 0) == 0:
        _load(db)
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
