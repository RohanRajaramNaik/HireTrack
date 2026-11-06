"""Job specification CRUD."""
from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..engine.skills import normaliser
from ..errors import NotFound
from ..models import JobSkill, JobSpecification, MatchRun
from ..schemas import JobIn, JobOut
from .candidate_service import get_or_create_skills

log = logging.getLogger("hiretrack.jobs")


def _query():
    return select(JobSpecification).options(selectinload(JobSpecification.skills).joinedload(JobSkill.skill))


def to_out(j: JobSpecification, last_run_at=None) -> JobOut:
    return JobOut(
        job_id=j.job_id,
        job_title=j.job_title,
        created_by=j.created_by,
        min_experience=j.min_experience,
        min_level_id=j.min_level_id,
        min_level_name=j.min_level.level_name,
        job_description=j.job_description,
        required_skills=[s.skill.name for s in j.skills if s.skill_type == "required"],
        preferred_skills=[s.skill.name for s in j.skills if s.skill_type == "preferred"],
        w_skills=j.w_skills,
        w_experience=j.w_experience,
        w_education=j.w_education,
        w_semantic=j.w_semantic,
        created_at=j.created_at,
        last_run_at=last_run_at,
    )


def _set_skills(db: Session, job: JobSpecification, required: list[str], preferred: list[str]) -> None:
    req = normaliser.normalise_many(required)
    pref = [p for p in normaliser.normalise_many(preferred) if p not in req]
    skills = get_or_create_skills(db, req + pref)
    job.skills.clear()
    db.flush()
    for n in req:
        job.skills.append(JobSkill(skill_id=skills[n].skill_id, skill_type="required"))
    for n in pref:
        job.skills.append(JobSkill(skill_id=skills[n].skill_id, skill_type="preferred"))


def list_jobs(db: Session) -> list[JobOut]:
    last_runs = dict(db.execute(select(MatchRun.job_id, func.max(MatchRun.run_at)).group_by(MatchRun.job_id)).all())
    jobs = db.scalars(_query().order_by(JobSpecification.created_at.desc(), JobSpecification.job_id.desc())).all()
    return [to_out(j, last_runs.get(j.job_id)) for j in jobs]


def get_job(db: Session, job_id: int) -> JobSpecification:
    j = db.scalar(_query().where(JobSpecification.job_id == job_id))
    if j is None:
        raise NotFound(f"Job {job_id} not found")
    return j


def job_out(db: Session, j: JobSpecification) -> JobOut:
    last = db.scalar(select(func.max(MatchRun.run_at)).where(MatchRun.job_id == j.job_id))
    return to_out(j, last)


def _apply(j: JobSpecification, data: JobIn) -> None:
    j.job_title = data.job_title
    j.created_by = data.created_by
    j.min_experience = data.min_experience
    j.min_level_id = data.min_level_id
    j.job_description = data.job_description
    j.w_skills = data.w_skills
    j.w_experience = data.w_experience
    j.w_education = data.w_education
    j.w_semantic = data.w_semantic


def create_job(db: Session, data: JobIn) -> JobSpecification:
    j = JobSpecification()
    _apply(j, data)
    db.add(j)
    db.flush()
    _set_skills(db, j, data.required_skills, data.preferred_skills)
    db.commit()
    log.info("Created job id=%s", j.job_id)
    return get_job(db, j.job_id)


def update_job(db: Session, job_id: int, data: JobIn) -> JobSpecification:
    j = get_job(db, job_id)
    _apply(j, data)
    _set_skills(db, j, data.required_skills, data.preferred_skills)
    db.commit()
    db.expire_all()
    log.info("Updated job id=%s", job_id)
    return get_job(db, job_id)


def delete_job(db: Session, job_id: int) -> None:
    j = get_job(db, job_id)
    db.delete(j)
    db.commit()
    log.info("Deleted job id=%s", job_id)
