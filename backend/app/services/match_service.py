"""Runs the matching engine for a job and persists/reads results.

The engine itself (engine/scoring.py) knows nothing about the database. This
service loads rows, converts them into engine inputs, and saves every result
for a run in ONE transaction (rolled back entirely on any error).
"""
from __future__ import annotations

import csv
import io
import logging
import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..engine.embeddings import embedder
from ..engine.scoring import (
    CandidateProfile,
    JobCriteria,
    Weights,
    calculation_string,
    score_candidates,
)
from ..errors import AppError
from ..models import Candidate, CandidateSkill, MatchResult, MatchRun, utcnow
from ..schemas import ResultRow, ResultsOut, RunInfo
from .job_service import get_job, job_out

log = logging.getLogger("hiretrack.match")


def _profiles(db: Session) -> list[CandidateProfile]:
    cands = db.scalars(
        select(Candidate).options(selectinload(Candidate.skills).joinedload(CandidateSkill.skill))
    ).all()
    return [
        CandidateProfile(
            candidate_id=c.candidate_id,
            skills=[cs.skill.name for cs in c.skills],
            years_experience=c.years_experience,
            level=c.level_id,
            resume_summary=c.resume_summary,
            full_name=c.full_name,  # tie-break only
            skills_as_entered={cs.skill.name: (cs.entered_as or cs.skill.name) for cs in c.skills},
        )
        for c in cands
    ]


def run_match(db: Session, job_id: int) -> ResultsOut:
    job = get_job(db, job_id)
    weights = Weights(job.w_skills, job.w_experience, job.w_education, job.w_semantic)
    criteria = JobCriteria(
        required=[s.skill.name for s in job.skills if s.skill_type == "required"],
        preferred=[s.skill.name for s in job.skills if s.skill_type == "preferred"],
        min_experience=job.min_experience,
        min_level=job.min_level_id,
        description=job.job_description,
        weights=weights,
    )
    started = time.perf_counter()
    profiles = _profiles(db)
    if not profiles:
        raise AppError("There are no candidates to match. Add candidates or load the demo data first.")
    scores = score_candidates(criteria, profiles, embedder.encode)
    duration_ms = int((time.perf_counter() - started) * 1000)
    try:
        embedder.save()  # keep newly encoded CVs for next time (no-op if nothing new)
    except Exception:  # pragma: no cover
        log.warning("Could not save embedding cache")

    run_at = utcnow()
    try:
        db.add(
            MatchRun(
                job_id=job_id,
                run_at=run_at,
                duration_ms=duration_ms,
                candidate_count=len(scores),
                w_skills=weights.skills,
                w_experience=weights.experience,
                w_education=weights.education,
                w_semantic=weights.semantic,
            )
        )
        db.add_all(
            [
                MatchResult(
                    candidate_id=s.candidate_id,
                    job_id=job_id,
                    skills_score=s.skills,
                    experience_score=s.experience,
                    education_score=s.education,
                    semantic_score=s.semantic,
                    overall_score=s.overall,
                    rank=s.rank,
                    matched_skills={
                        "required": s.skill_match.matched_required,
                        "preferred": s.skill_match.matched_preferred,
                        "aliases": s.alias_hits,
                    },
                    missing_skills={
                        "required": s.skill_match.missing_required,
                        "preferred": s.skill_match.missing_preferred,
                    },
                    explanation=s.explanation,
                    insights=s.keyword_insights,
                    run_at=run_at,
                )
                for s in scores
            ]
        )
        db.commit()
    except Exception:
        db.rollback()
        log.exception("Saving match results failed for job id=%s; rolled back", job_id)
        raise
    log.info("Match run job id=%s candidates=%d duration_ms=%d", job_id, len(scores), duration_ms)
    return get_results(db, job_id)


def latest_run(db: Session, job_id: int) -> MatchRun | None:
    return db.scalar(select(MatchRun).where(MatchRun.job_id == job_id).order_by(MatchRun.run_at.desc()).limit(1))


def latest_scores(db: Session, job_id: int) -> dict[int, float]:
    """{candidate_id: overall score} from the latest run for a job (empty if never run)."""
    run = latest_run(db, job_id)
    if run is None:
        return {}
    rows = db.execute(
        select(MatchResult.candidate_id, MatchResult.overall_score).where(
            MatchResult.job_id == job_id, MatchResult.run_at == run.run_at
        )
    ).all()
    return {cid: score for cid, score in rows}


def get_results(db: Session, job_id: int) -> ResultsOut:
    job = get_job(db, job_id)
    run = latest_run(db, job_id)
    if run is None:
        return ResultsOut(job=job_out(db, job), run=None, results=[])
    weights = Weights(run.w_skills, run.w_experience, run.w_education, run.w_semantic)
    rows = db.scalars(
        select(MatchResult)
        .where(MatchResult.job_id == job_id, MatchResult.run_at == run.run_at)
        .order_by(MatchResult.rank)
    ).all()
    from ..models import Application

    stages = dict(
        db.execute(select(Application.candidate_id, Application.stage).where(Application.job_id == job_id)).all()
    )
    out: list[ResultRow] = []
    for r in rows:
        c = r.candidate
        m, x = r.matched_skills or {}, r.missing_skills or {}
        out.append(
            ResultRow(
                result_id=r.result_id,
                rank=r.rank,
                candidate_id=r.candidate_id,
                full_name=c.full_name,
                previous_titles=c.previous_titles,
                years_experience=c.years_experience,
                level_name=c.level.level_name,
                location=c.location,
                pipeline_stage=stages.get(r.candidate_id),
                skills_score=r.skills_score,
                experience_score=r.experience_score,
                education_score=r.education_score,
                semantic_score=r.semantic_score,
                overall_score=r.overall_score,
                matched={"required": m.get("required", []), "preferred": m.get("preferred", [])},
                missing={"required": x.get("required", []), "preferred": x.get("preferred", [])},
                aliases=m.get("aliases", {}),
                explanation=r.explanation or "",
                insights=r.insights or [],
                calculation=_calc(r, weights),
            )
        )
    return ResultsOut(
        job=job_out(db, job),
        run=RunInfo(
            run_at=run.run_at,
            duration_ms=run.duration_ms,
            candidate_count=run.candidate_count,
            w_skills=run.w_skills,
            w_experience=run.w_experience,
            w_education=run.w_education,
            w_semantic=run.w_semantic,
        ),
        results=out,
    )


def _calc(r: MatchResult, w: Weights) -> str:
    from types import SimpleNamespace

    ns = SimpleNamespace(
        skills=r.skills_score,
        experience=r.experience_score,
        education=r.education_score,
        semantic=r.semantic_score,
        overall=r.overall_score,
    )
    return calculation_string(ns, w)


def _csv_safe(value) -> str:
    """Prevent spreadsheet formula injection in exported cells."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def results_csv(db: Session, job_id: int) -> tuple[str, str]:
    res = get_results(db, job_id)
    if res.run is None:
        raise AppError("This job has not been matched yet. Run a match first.", status_code=404)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "Rank", "Candidate", "Overall", "Skills", "Experience", "Education", "Semantic",
            "Matched required", "Missing required", "Matched preferred", "Missing preferred",
            "Explanation", "Calculation",
        ]
    )
    for r in res.results:
        w.writerow(
            [_csv_safe(v) for v in (
                r.rank, r.full_name, r.overall_score, r.skills_score, r.experience_score,
                r.education_score, r.semantic_score,
                "; ".join(r.matched.required), "; ".join(r.missing.required),
                "; ".join(r.matched.preferred), "; ".join(r.missing.preferred),
                r.explanation, r.calculation,
            )]
        )
    slug = "".join(ch if ch.isalnum() else "-" for ch in res.job.job_title.lower()).strip("-")
    fname = f"hiretrack-{slug}-{res.run.run_at:%Y%m%d-%H%M}.csv"
    return buf.getvalue(), fname


def stats(db: Session) -> dict:
    from ..models import JobSpecification

    n_cand = db.scalar(select(func.count(Candidate.candidate_id))) or 0
    n_jobs = db.scalar(select(func.count(JobSpecification.job_id))) or 0
    last = db.scalar(select(MatchRun).order_by(MatchRun.run_at.desc()).limit(1))
    avg = None
    title = None
    if last is not None:
        avg = db.scalar(
            select(func.avg(MatchResult.overall_score)).where(
                MatchResult.job_id == last.job_id, MatchResult.run_at == last.run_at
            )
        )
        title = db.scalar(select(JobSpecification.job_title).where(JobSpecification.job_id == last.job_id))
    return {
        "candidates": n_cand,
        "jobs": n_jobs,
        "last_run_at": last.run_at if last else None,
        "last_run_job_title": title,
        "last_run_job_id": last.job_id if last else None,
        "average_score": round(avg, 1) if avg is not None else None,
        "embedder": embedder.backend_name,
    }
