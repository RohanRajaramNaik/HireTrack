"""Applicant pipeline: applications, stage changes and the audit trail.

Every stage change writes an ApplicationEvent row in the same transaction as
the change itself, so the history can never disagree with the current stage.
Moving an application to "hired" also adds the person to the staff pool, so a
Resource Manager can allocate them to projects straight away.
"""
from __future__ import annotations

import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..engine import pipeline as rules
from ..errors import AppError, Conflict, NotFound
from ..models import Application, ApplicationEvent, Candidate, JobSpecification, StaffMember, User, utcnow
from ..schemas import ApplicationEventOut, ApplicationIn, ApplicationOut, BulkApplicationIn, StageChangeIn

log = logging.getLogger("hiretrack.pipeline")


def _rejected_from(app: Application) -> str | None:
    """The stage this application was at when it was rejected (for reopening)."""
    for ev in reversed(app.events):
        if ev.to_stage == rules.REJECTED:
            return ev.from_stage
    return None


def to_out(app: Application, with_events: bool = False) -> ApplicationOut:
    c = app.candidate
    events = None
    if with_events:
        events = [
            ApplicationEventOut(
                event_id=e.event_id,
                from_stage=e.from_stage,
                to_stage=e.to_stage,
                changed_by_name=e.user.full_name if e.user else None,
                changed_at=e.changed_at,
                note=e.note,
            )
            for e in app.events
        ]
    return ApplicationOut(
        application_id=app.application_id,
        candidate_id=app.candidate_id,
        candidate_name=c.full_name,
        candidate_titles=c.previous_titles,
        candidate_location=c.location,
        years_experience=c.years_experience,
        job_id=app.job_id,
        job_title=app.job.job_title,
        stage=app.stage,
        match_score=app.match_score,
        applied_at=app.applied_at,
        updated_at=app.updated_at,
        allowed_moves=rules.allowed_moves(app.stage, _rejected_from(app)),
        events=events,
    )


def _query():
    return select(Application).options(selectinload(Application.events).joinedload(ApplicationEvent.user))


def list_applications(
    db: Session, job_id: int | None = None, stage: str | None = None, search: str | None = None
) -> list[ApplicationOut]:
    q = _query().join(Application.candidate)
    if job_id is not None:
        q = q.where(Application.job_id == job_id)
    if stage:
        q = q.where(Application.stage == stage)
    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        q = q.where(
            or_(
                func.lower(Candidate.full_name).like(term),
                func.lower(func.coalesce(Candidate.previous_titles, "")).like(term),
            )
        )
    q = q.order_by(Application.updated_at.desc(), Application.application_id.desc())
    return [to_out(a) for a in db.scalars(q).unique().all()]


def get_application(db: Session, application_id: int) -> Application:
    app = db.scalar(_query().where(Application.application_id == application_id))
    if app is None:
        raise NotFound(f"Application {application_id} not found")
    return app


def _check_refs(db: Session, candidate_id: int, job_id: int) -> JobSpecification:
    if db.get(Candidate, candidate_id) is None:
        raise NotFound(f"Candidate {candidate_id} not found", field="candidate_id")
    job = db.get(JobSpecification, job_id)
    if job is None:
        raise NotFound(f"Job {job_id} not found", field="job_id")
    if job.status != "open":
        raise AppError("This job is closed and is not accepting applicants", field="job_id", status_code=422)
    return job


def create_application(db: Session, data: ApplicationIn, user: User) -> Application:
    _check_refs(db, data.candidate_id, data.job_id)
    exists = db.scalar(
        select(Application.application_id).where(
            Application.candidate_id == data.candidate_id, Application.job_id == data.job_id
        )
    )
    if exists:
        raise Conflict("This candidate is already in the pipeline for this job", field="candidate_id")
    now = utcnow()
    app = Application(
        candidate_id=data.candidate_id,
        job_id=data.job_id,
        stage="applied",
        match_score=data.match_score,
        applied_at=now,
        updated_at=now,
    )
    app.events.append(
        ApplicationEvent(from_stage=None, to_stage="applied", changed_by=user.user_id, changed_at=now, note=data.note)
    )
    db.add(app)
    db.commit()
    log.info("Application id=%s created (candidate=%s job=%s)", app.application_id, data.candidate_id, data.job_id)
    return get_application(db, app.application_id)


def bulk_add(db: Session, data: BulkApplicationIn, user: User) -> dict:
    """Add several candidates (e.g. a shortlist from Results) to one job's pipeline.

    Candidates already in the pipeline for this job are skipped, not errors.
    The match score from the latest run is stored with each new application.
    """
    from .match_service import latest_scores

    job = db.get(JobSpecification, data.job_id)
    if job is None:
        raise NotFound(f"Job {data.job_id} not found", field="job_id")
    if job.status != "open":
        raise AppError("This job is closed and is not accepting applicants", field="job_id", status_code=422)
    ids = list(dict.fromkeys(data.candidate_ids))
    known = set(db.scalars(select(Candidate.candidate_id).where(Candidate.candidate_id.in_(ids))))
    missing = [i for i in ids if i not in known]
    if missing:
        raise NotFound(f"Candidate {missing[0]} not found", field="candidate_ids")
    already = set(
        db.scalars(
            select(Application.candidate_id).where(Application.job_id == job.job_id, Application.candidate_id.in_(ids))
        )
    )
    scores = latest_scores(db, job.job_id)
    now = utcnow()
    added = 0
    for cid in ids:
        if cid in already:
            continue
        app = Application(
            candidate_id=cid, job_id=job.job_id, stage="applied", match_score=scores.get(cid), applied_at=now, updated_at=now
        )
        app.events.append(
            ApplicationEvent(
                from_stage=None, to_stage="applied", changed_by=user.user_id, changed_at=now, note="Added from match results"
            )
        )
        db.add(app)
        added += 1
    db.commit()
    log.info("Bulk-added %d applications to job id=%s", added, job.job_id)
    return {"added": added, "skipped": len(ids) - added}


def _ensure_staff(db: Session, app: Application) -> StaffMember:
    """Create a staff record for a hired candidate (once)."""
    staff = db.scalar(select(StaffMember).where(StaffMember.candidate_id == app.candidate_id))
    if staff is None:
        c = app.candidate
        staff = StaffMember(
            full_name=c.full_name,
            email=c.email,
            role_title=app.job.job_title,
            location=c.location or app.job.location,
            candidate_id=c.candidate_id,
            source="hired",
        )
        db.add(staff)
    else:
        staff.is_active = True
        staff.role_title = app.job.job_title
    return staff


def change_stage(db: Session, application_id: int, data: StageChangeIn, user: User) -> Application:
    app = get_application(db, application_id)
    try:
        rules.check_move(app.stage, data.stage, _rejected_from(app))
    except rules.StageError as exc:
        raise AppError(str(exc), field="stage", status_code=422) from exc
    if data.stage == "hired" and app.job.status != "open":
        raise AppError("This job is closed, so nobody else can be hired for it", field="stage", status_code=422)
    now = utcnow()
    app.events.append(
        ApplicationEvent(
            from_stage=app.stage, to_stage=data.stage, changed_by=user.user_id, changed_at=now, note=data.note or None
        )
    )
    app.stage = data.stage
    app.updated_at = now
    if data.stage == "hired":
        _ensure_staff(db, app)
    db.commit()
    log.info("Application id=%s moved to %s by user id=%s", application_id, data.stage, user.user_id)
    db.expire_all()
    return get_application(db, application_id)


def delete_application(db: Session, application_id: int) -> None:
    app = get_application(db, application_id)
    if app.stage == "hired":
        raise AppError("A hired application cannot be deleted; it is part of the staff record", status_code=422)
    db.delete(app)
    db.commit()
    log.info("Deleted application id=%s", application_id)


def stage_counts(db: Session, job_id: int | None = None) -> dict[str, int]:
    q = select(Application.stage, func.count(Application.application_id)).group_by(Application.stage)
    if job_id is not None:
        q = q.where(Application.job_id == job_id)
    return {stage: n for stage, n in db.execute(q).all()}


def funnel(db: Session) -> list[dict]:
    current = stage_counts(db)
    # For rejected applications, find the stage they were rejected from.
    rows = db.execute(
        select(ApplicationEvent.application_id, ApplicationEvent.from_stage)
        .join(Application, Application.application_id == ApplicationEvent.application_id)
        .where(Application.stage == rules.REJECTED, ApplicationEvent.to_stage == rules.REJECTED)
        .order_by(ApplicationEvent.event_id)
    ).all()
    rejected_from = {app_id: frm for app_id, frm in rows}  # last rejection wins
    furthest: dict[str, int] = {}
    for stage, n in current.items():
        if stage != rules.REJECTED:
            furthest[stage] = furthest.get(stage, 0) + n
    for frm in rejected_from.values():
        s = rules.furthest_stage(rules.REJECTED, frm)
        furthest[s] = furthest.get(s, 0) + 1
    return rules.funnel(furthest, current)
