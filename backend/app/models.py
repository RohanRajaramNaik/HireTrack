"""ORM models (3NF). CHECK constraints mirror the validation rules exactly."""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class EducationLevel(Base):
    __tablename__ = "education_level"
    level_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level_name: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    __table_args__ = (CheckConstraint("level_id BETWEEN 1 AND 7", name="ck_level_range"),)


class Skill(Base):
    __tablename__ = "skill"
    skill_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Stored lowercase + trimmed (enforced by SkillNormaliser and the CHECK below).
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    __table_args__ = (
        CheckConstraint("name = lower(trim(name)) AND length(name) > 0", name="ck_skill_normalised"),
    )


class Candidate(Base):
    __tablename__ = "candidate"
    candidate_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    years_experience: Mapped[float] = mapped_column(Float, nullable=False)
    level_id: Mapped[int] = mapped_column(ForeignKey("education_level.level_id"), nullable=False)
    previous_titles: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resume_summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    level: Mapped[EducationLevel] = relationship(lazy="joined")
    skills: Mapped[list["CandidateSkill"]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("length(trim(full_name)) BETWEEN 2 AND 100", name="ck_cand_name"),
        CheckConstraint("years_experience BETWEEN 0 AND 50", name="ck_cand_years"),
        CheckConstraint("length(resume_summary) BETWEEN 20 AND 3000", name="ck_cand_summary"),
        Index("ix_candidate_name", "full_name"),
    )


class CandidateSkill(Base):
    __tablename__ = "candidate_skill"
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.candidate_id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.skill_id", ondelete="CASCADE"), primary_key=True)
    # What the user actually typed (e.g. "JS" for javascript). Lets the results
    # screen explain alias matches. Depends on the full key, so 3NF holds.
    entered_as: Mapped[str | None] = mapped_column(String(60), nullable=True)

    candidate: Mapped[Candidate] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(lazy="joined")


class JobSpecification(Base):
    __tablename__ = "job_specification"
    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_title: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    location: Mapped[str] = mapped_column(String(80), nullable=False, default="Johannesburg")
    # open = accepting applicants; closed = filled or withdrawn
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="open")
    min_experience: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    min_level_id: Mapped[int] = mapped_column(ForeignKey("education_level.level_id"), nullable=False)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    w_skills: Mapped[int] = mapped_column(Integer, nullable=False, default=40)
    w_experience: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    w_education: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    w_semantic: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    min_level: Mapped[EducationLevel] = relationship(lazy="joined")
    skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("length(trim(job_title)) BETWEEN 2 AND 100", name="ck_job_title"),
        CheckConstraint("length(trim(location)) BETWEEN 2 AND 80", name="ck_job_location"),
        CheckConstraint("status IN ('open','closed')", name="ck_job_status"),
        CheckConstraint("min_experience BETWEEN 0 AND 50", name="ck_job_min_exp"),
        CheckConstraint("length(job_description) BETWEEN 20 AND 5000", name="ck_job_desc"),
        CheckConstraint("w_skills BETWEEN 0 AND 100", name="ck_w_skills"),
        CheckConstraint("w_experience BETWEEN 0 AND 100", name="ck_w_experience"),
        CheckConstraint("w_education BETWEEN 0 AND 100", name="ck_w_education"),
        CheckConstraint("w_semantic BETWEEN 0 AND 100", name="ck_w_semantic"),
        CheckConstraint("w_skills + w_experience + w_education + w_semantic = 100", name="ck_w_total"),
    )


class JobSkill(Base):
    __tablename__ = "job_skill"
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_specification.job_id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.skill_id", ondelete="CASCADE"), primary_key=True)
    skill_type: Mapped[str] = mapped_column(String(10), nullable=False)

    job: Mapped[JobSpecification] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(lazy="joined")

    __table_args__ = (CheckConstraint("skill_type IN ('required','preferred')", name="ck_skill_type"),)


class MatchResult(Base):
    __tablename__ = "match_result"
    result_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.candidate_id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_specification.job_id", ondelete="CASCADE"), nullable=False
    )
    skills_score: Mapped[float] = mapped_column(Float, nullable=False)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False)
    education_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    # {"required": [...], "preferred": [...], "aliases": {"js": "javascript"}}
    matched_skills: Mapped[dict] = mapped_column(JSON, nullable=False)
    # {"required": [...], "preferred": [...]}
    missing_skills: Mapped[dict] = mapped_column(JSON, nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # Snapshot of the plain-English explanation and keyword-search notes at run
    # time, so they always agree with the stored scores.
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights: Mapped[list | None] = mapped_column(JSON, nullable=True)

    candidate: Mapped[Candidate] = relationship(lazy="joined")

    __table_args__ = (
        CheckConstraint("skills_score BETWEEN 0 AND 100", name="ck_mr_skills"),
        CheckConstraint("experience_score BETWEEN 0 AND 100", name="ck_mr_exp"),
        CheckConstraint("education_score BETWEEN 0 AND 100", name="ck_mr_edu"),
        CheckConstraint("semantic_score BETWEEN 0 AND 100", name="ck_mr_sem"),
        CheckConstraint("overall_score BETWEEN 0 AND 100", name="ck_mr_overall"),
        CheckConstraint("rank >= 1", name="ck_mr_rank"),
        UniqueConstraint("candidate_id", "job_id", "run_at", name="uq_mr_cand_job_run"),
        Index("ix_match_result_job_run", "job_id", "run_at"),
    )


class MatchRun(Base):
    """Metadata for one matching run (an addition to the brief's schema).

    Stores the weights actually used and how long the run took, so the Results
    screen stays truthful even if the job specification is edited afterwards.
    """

    __tablename__ = "match_run"
    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_specification.job_id", ondelete="CASCADE"), nullable=False
    )
    run_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False)
    w_skills: Mapped[int] = mapped_column(Integer, nullable=False)
    w_experience: Mapped[int] = mapped_column(Integer, nullable=False)
    w_education: Mapped[int] = mapped_column(Integer, nullable=False)
    w_semantic: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint("job_id", "run_at", name="uq_run_job_time"),
        CheckConstraint("w_skills + w_experience + w_education + w_semantic = 100", name="ck_run_w_total"),
    )


# --------------------------------------------------------------------------
# Phase 5 additions: user accounts, applicant pipeline, resource allocation
# --------------------------------------------------------------------------
ROLES = ("admin", "recruiter", "resource_manager")
STAGES = ("applied", "screened", "interview", "offer", "hired", "rejected")
PROJECT_STATUSES = ("planned", "active", "on_hold", "completed")


class User(Base):
    """A person who logs in. The role decides which screens and actions they get."""

    __tablename__ = "app_user"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('admin','recruiter','resource_manager')", name="ck_user_role"),
        CheckConstraint("email = lower(trim(email))", name="ck_user_email_lower"),
    )


class Application(Base):
    """One candidate applying for one job, and where that application stands."""

    __tablename__ = "application"
    application_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(
        ForeignKey("candidate.candidate_id", ondelete="CASCADE"), nullable=False
    )
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_specification.job_id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(12), nullable=False, default="applied")
    # Overall match score when the candidate was added from a match run.
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    candidate: Mapped[Candidate] = relationship(lazy="joined")
    job: Mapped[JobSpecification] = relationship(lazy="joined")
    events: Mapped[list["ApplicationEvent"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ApplicationEvent.event_id",
    )

    __table_args__ = (
        CheckConstraint(
            "stage IN ('applied','screened','interview','offer','hired','rejected')", name="ck_app_stage"
        ),
        CheckConstraint("match_score IS NULL OR match_score BETWEEN 0 AND 100", name="ck_app_score"),
        UniqueConstraint("candidate_id", "job_id", name="uq_app_cand_job"),
        Index("ix_application_job_stage", "job_id", "stage"),
    )


class ApplicationEvent(Base):
    """Audit trail: every stage change, who made it and when. Rows are never edited."""

    __tablename__ = "application_event"
    event_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        ForeignKey("application.application_id", ondelete="CASCADE"), nullable=False
    )
    from_stage: Mapped[str | None] = mapped_column(String(12), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(12), nullable=False)
    changed_by: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.user_id", ondelete="SET NULL"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    application: Mapped[Application] = relationship(back_populates="events")
    user: Mapped[User | None] = relationship(lazy="joined")


class StaffMember(Base):
    """Someone who can be allocated to projects: existing staff or a hired candidate."""

    __tablename__ = "staff_member"
    staff_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    role_title: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # Set when the person was hired through the pipeline.
    candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("candidate.candidate_id", ondelete="SET NULL"), nullable=True, unique=True
    )
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="existing")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    allocations: Mapped[list["Allocation"]] = relationship(
        back_populates="staff", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("length(trim(full_name)) BETWEEN 2 AND 100", name="ck_staff_name"),
        CheckConstraint("source IN ('existing','hired')", name="ck_staff_source"),
    )


class Project(Base):
    __tablename__ = "project"
    project_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    client: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="planned")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    allocations: Mapped[list["Allocation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("length(trim(name)) BETWEEN 2 AND 100", name="ck_project_name"),
        CheckConstraint("end_date >= start_date", name="ck_project_dates"),
        CheckConstraint("status IN ('planned','active','on_hold','completed')", name="ck_project_status"),
    )


class Allocation(Base):
    """A share of one staff member's time on one project for a date range."""

    __tablename__ = "allocation"
    allocation_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("staff_member.staff_id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False)
    role_on_project: Mapped[str | None] = mapped_column(String(100), nullable=True)
    allocation_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    staff: Mapped[StaffMember] = relationship(back_populates="allocations", lazy="joined")
    project: Mapped[Project] = relationship(back_populates="allocations", lazy="joined")

    __table_args__ = (
        CheckConstraint("allocation_percent BETWEEN 1 AND 100", name="ck_alloc_percent"),
        CheckConstraint("end_date >= start_date", name="ck_alloc_dates"),
        Index("ix_allocation_staff", "staff_id"),
    )
