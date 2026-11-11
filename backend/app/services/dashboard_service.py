"""Dashboard figures: key counts and the data behind each chart, in one call."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..engine.pipeline import FINAL, LABELS
from ..models import Application, ApplicationEvent, Candidate, JobSpecification, User, utcnow
from . import match_service, pipeline_service, resource_service


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.month - 1 + n, 12)
    return date(d.year + y, m + 1, 1)


def dashboard(db: Session) -> dict:
    now = utcnow()
    counts = pipeline_service.stage_counts(db)
    active_apps = sum(n for s, n in counts.items() if s not in FINAL)
    hires_30 = db.scalar(
        select(func.count(ApplicationEvent.event_id)).where(
            ApplicationEvent.to_stage == "hired", ApplicationEvent.changed_at >= now - timedelta(days=30)
        )
    ) or 0

    # Applications in progress per open job (top 8).
    per_job = db.execute(
        select(JobSpecification.job_id, JobSpecification.job_title, func.count(Application.application_id))
        .join(Application, Application.job_id == JobSpecification.job_id)
        .where(JobSpecification.status == "open", Application.stage.not_in(tuple(FINAL)))
        .group_by(JobSpecification.job_id)
        .order_by(func.count(Application.application_id).desc(), JobSpecification.job_title)
        .limit(8)
    ).all()

    # Hires per month for the last 6 months (including this one).
    first = _add_months(_month_start(now.date()), -5)
    hire_dates = db.scalars(
        select(ApplicationEvent.changed_at).where(
            ApplicationEvent.to_stage == "hired",
            ApplicationEvent.changed_at >= datetime.combine(first, datetime.min.time()),
        )
    ).all()
    months = [_add_months(first, i) for i in range(6)]
    hires = {m: 0 for m in months}
    for d in hire_dates:
        key = _month_start(d.date())
        if key in hires:
            hires[key] += 1

    # Latest stage changes for the activity list.
    recent = db.execute(
        select(ApplicationEvent, Candidate.full_name, JobSpecification.job_title, User.full_name)
        .join(Application, Application.application_id == ApplicationEvent.application_id)
        .join(Candidate, Candidate.candidate_id == Application.candidate_id)
        .join(JobSpecification, JobSpecification.job_id == Application.job_id)
        .outerjoin(User, User.user_id == ApplicationEvent.changed_by)
        .order_by(ApplicationEvent.changed_at.desc(), ApplicationEvent.event_id.desc())
        .limit(8)
    ).all()

    util = resource_service.utilisation_summary(db)
    stats = match_service.stats(db)
    return {
        "counts": {
            "candidates": stats["candidates"],
            "jobs_open": db.scalar(select(func.count()).where(JobSpecification.status == "open")) or 0,
            "jobs_total": stats["jobs"],
            "applications_active": active_apps,
            "hires_30_days": hires_30,
            "staff_active": util["active_staff"],
            "staff_bench": util["bands"]["bench"],
            "average_utilisation": util["average_utilisation"],
        },
        "funnel": pipeline_service.funnel(db),
        "applications_per_job": [{"job_id": j, "job_title": t, "count": n} for j, t, n in per_job],
        "hires_per_month": [{"month": m.strftime("%Y-%m"), "label": m.strftime("%b"), "count": hires[m]} for m in months],
        "utilisation_bands": util["bands"],
        "recent_activity": [
            {
                "event_id": ev.event_id,
                "application_id": ev.application_id,
                "candidate_name": cname,
                "job_title": jtitle,
                "from_stage": ev.from_stage,
                "to_stage": ev.to_stage,
                "to_label": LABELS.get(ev.to_stage, ev.to_stage),
                "changed_by": uname,
                "changed_at": ev.changed_at,
            }
            for ev, cname, jtitle, uname in recent
        ],
        "matching": {
            "last_run_at": stats["last_run_at"],
            "last_run_job_title": stats["last_run_job_title"],
            "last_run_job_id": stats["last_run_job_id"],
            "average_score": stats["average_score"],
            "embedder": stats["embedder"],
        },
    }
