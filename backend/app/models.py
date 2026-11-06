"""ORM models (3NF). CHECK constraints mirror the validation rules exactly."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
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

    candidate: Mapped[Candidate] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(lazy="joined")


class JobSpecification(Base):
    __tablename__ = "job_specification"
    job_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_title: Mapped[str] = mapped_column(String(100), nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
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
