"""Candidate CRUD. All queries use SQLAlchemy bound parameters."""
from __future__ import annotations

import logging

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..engine.skills import normaliser
from ..errors import NotFound
from ..models import Candidate, CandidateSkill, Skill
from ..schemas import CandidateIn, CandidateOut

log = logging.getLogger("hiretrack.candidates")

SORTS = {
    "name": func.lower(Candidate.full_name),
    "years": Candidate.years_experience,
    "level": Candidate.level_id,
    "created": Candidate.created_at,
}


def get_or_create_skills(db: Session, names: list[str]) -> dict[str, Skill]:
    """Return {canonical_name: Skill}, inserting any skills not yet known."""
    if not names:
        return {}
    found = {s.name: s for s in db.scalars(select(Skill).where(Skill.name.in_(names)))}
    for n in names:
        if n not in found:
            sk = Skill(name=n)
            db.add(sk)
            found[n] = sk
    db.flush()
    return found


def to_out(c: Candidate) -> CandidateOut:
    return CandidateOut(
        candidate_id=c.candidate_id,
        full_name=c.full_name,
        email=c.email,
        phone=c.phone,
        location=c.location,
        years_experience=c.years_experience,
        level_id=c.level_id,
        level_name=c.level.level_name,
        previous_titles=c.previous_titles,
        resume_summary=c.resume_summary,
        skills=[cs.entered_as or cs.skill.name for cs in c.skills],
        created_at=c.created_at,
    )


def _set_skills(db: Session, cand: Candidate, raw_skills: list[str]) -> None:
    pairs = normaliser.normalise_with_source(raw_skills)
    skills = get_or_create_skills(db, [p[0] for p in pairs])
    cand.skills.clear()
    db.flush()
    for canonical, entered in pairs:
        cand.skills.append(CandidateSkill(skill_id=skills[canonical].skill_id, entered_as=entered[:60]))


def _query():
    return select(Candidate).options(selectinload(Candidate.skills).joinedload(CandidateSkill.skill))


def list_candidates(
    db: Session, search: str | None, page: int, page_size: int, sort: str, order: str
) -> tuple[list[CandidateOut], int]:
    q = _query()
    count_q = select(func.count(Candidate.candidate_id))
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        canonical = f"%{normaliser.normalise(search)}%"
        skill_match = exists().where(
            CandidateSkill.candidate_id == Candidate.candidate_id,
            CandidateSkill.skill_id == Skill.skill_id,
            Skill.name.like(canonical),
        )
        cond = or_(
            func.lower(Candidate.full_name).like(term),
            func.lower(func.coalesce(Candidate.previous_titles, "")).like(term),
            func.lower(func.coalesce(Candidate.email, "")).like(term),
            func.lower(func.coalesce(Candidate.location, "")).like(term),
            skill_match,
        )
        q, count_q = q.where(cond), count_q.where(cond)
    col = SORTS.get(sort, SORTS["name"])
    q = q.order_by(col.desc() if order == "desc" else col.asc(), Candidate.candidate_id)
    total = db.scalar(count_q) or 0
    rows = db.scalars(q.offset((page - 1) * page_size).limit(page_size)).unique().all()
    return [to_out(c) for c in rows], total


def get_candidate(db: Session, candidate_id: int) -> Candidate:
    c = db.scalar(_query().where(Candidate.candidate_id == candidate_id))
    if c is None:
        raise NotFound(f"Candidate {candidate_id} not found")
    return c


def create_candidate(db: Session, data: CandidateIn) -> Candidate:
    c = Candidate(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        location=data.location,
        years_experience=data.years_experience,
        level_id=data.level_id,
        previous_titles=data.previous_titles or None,
        resume_summary=data.resume_summary,
    )
    db.add(c)
    db.flush()
    _set_skills(db, c, data.skills)
    db.commit()
    log.info("Created candidate id=%s", c.candidate_id)
    return get_candidate(db, c.candidate_id)


def update_candidate(db: Session, candidate_id: int, data: CandidateIn) -> Candidate:
    c = get_candidate(db, candidate_id)
    c.full_name = data.full_name
    c.email = data.email
    c.phone = data.phone
    c.location = data.location
    c.years_experience = data.years_experience
    c.level_id = data.level_id
    c.previous_titles = data.previous_titles or None
    c.resume_summary = data.resume_summary
    _set_skills(db, c, data.skills)
    db.commit()
    log.info("Updated candidate id=%s", candidate_id)
    db.expire_all()
    return get_candidate(db, candidate_id)


def delete_candidate(db: Session, candidate_id: int) -> None:
    c = get_candidate(db, candidate_id)
    db.delete(c)
    db.commit()
    log.info("Deleted candidate id=%s", candidate_id)
