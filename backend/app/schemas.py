"""Pydantic request/response models.

Validation errors are turned into {"detail": "...", "field": "..."} by the
handler in main.py. Model-level errors raise FieldError so they can name the
field the message belongs to (e.g. "weights").
"""
from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .engine.scoring import Weights, WeightError, validate_skill_lists
from .engine.skills import normaliser

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class FieldError(ValueError):
    """A validation error tied to a specific field name."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field


class ErrorOut(BaseModel):
    detail: str
    field: str | None = None


def _strip(v):
    return v.strip() if isinstance(v, str) else v


def _clean_skill_list(v):
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError("Skills must be a list")
    return [str(s) for s in v if str(s).strip()]


# --------------------------------------------------------------------------
# Lookups
# --------------------------------------------------------------------------
class EducationLevelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    level_id: int
    level_name: str


# --------------------------------------------------------------------------
# Candidates
# --------------------------------------------------------------------------
class CandidateIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str | None = Field(default=None, max_length=254)
    years_experience: float = Field(ge=0, le=50)
    level_id: int = Field(ge=1, le=7)
    previous_titles: str | None = Field(default=None, max_length=500)
    resume_summary: str = Field(min_length=20, max_length=3000)
    skills: list[str]

    _strip_text = field_validator("full_name", "email", "previous_titles", "resume_summary", mode="before")(_strip)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address, or leave it blank")
        return v.lower()

    @field_validator("skills", mode="before")
    @classmethod
    def _skills_list(cls, v):
        return _clean_skill_list(v)

    @field_validator("skills")
    @classmethod
    def _skills_required(cls, v: list[str]) -> list[str]:
        if not normaliser.normalise_many(v):
            raise ValueError("Add at least one skill")
        for s in v:
            if len(s.strip()) > 60:
                raise ValueError(f"Skill names must be 60 characters or fewer ({s[:20]}...)")
        return v


class CandidateOut(BaseModel):
    candidate_id: int
    full_name: str
    email: str | None
    years_experience: float
    level_id: int
    level_name: str
    previous_titles: str | None
    resume_summary: str
    skills: list[str]
    created_at: datetime


class CandidateListOut(BaseModel):
    items: list[CandidateOut]
    total: int
    page: int
    page_size: int


# --------------------------------------------------------------------------
# Jobs
# --------------------------------------------------------------------------
class JobIn(BaseModel):
    job_title: str = Field(min_length=2, max_length=100)
    created_by: str | None = Field(default=None, max_length=100)
    min_experience: float = Field(default=0, ge=0, le=50)
    min_level_id: int = Field(ge=1, le=7)
    job_description: str = Field(min_length=20, max_length=5000)
    required_skills: list[str]
    preferred_skills: list[str] = []
    w_skills: int = Field(default=40, ge=0, le=100)
    w_experience: int = Field(default=25, ge=0, le=100)
    w_education: int = Field(default=15, ge=0, le=100)
    w_semantic: int = Field(default=20, ge=0, le=100)

    _strip_text = field_validator("job_title", "created_by", "job_description", mode="before")(_strip)

    @field_validator("required_skills", "preferred_skills", mode="before")
    @classmethod
    def _skills_list(cls, v):
        return _clean_skill_list(v)

    @model_validator(mode="after")
    def _rules(self) -> "JobIn":
        try:
            Weights(self.w_skills, self.w_experience, self.w_education, self.w_semantic).validate()
        except WeightError as exc:
            raise FieldError("weights", str(exc)) from exc
        req = normaliser.normalise_many(self.required_skills)
        pref = normaliser.normalise_many(self.preferred_skills)
        if not req:
            raise FieldError("required_skills", "Add at least one required skill")
        try:
            validate_skill_lists(req, pref)
        except ValueError as exc:
            raise FieldError("preferred_skills", str(exc)) from exc
        if self.created_by == "":
            self.created_by = None
        return self


class JobOut(BaseModel):
    job_id: int
    job_title: str
    created_by: str | None
    min_experience: float
    min_level_id: int
    min_level_name: str
    job_description: str
    required_skills: list[str]
    preferred_skills: list[str]
    w_skills: int
    w_experience: int
    w_education: int
    w_semantic: int
    created_at: datetime
    last_run_at: datetime | None = None


# --------------------------------------------------------------------------
# Results
# --------------------------------------------------------------------------
class SkillLists(BaseModel):
    required: list[str]
    preferred: list[str]


class ResultRow(BaseModel):
    result_id: int
    rank: int
    candidate_id: int
    full_name: str
    previous_titles: str | None
    years_experience: float
    level_name: str
    skills_score: float
    experience_score: float
    education_score: float
    semantic_score: float
    overall_score: float
    matched: SkillLists
    missing: SkillLists
    aliases: dict[str, str]
    explanation: str
    insights: list[str]
    calculation: str


class RunInfo(BaseModel):
    run_at: datetime
    duration_ms: int
    candidate_count: int
    w_skills: int
    w_experience: int
    w_education: int
    w_semantic: int


class ResultsOut(BaseModel):
    job: JobOut
    run: RunInfo | None
    results: list[ResultRow]


class StatsOut(BaseModel):
    candidates: int
    jobs: int
    last_run_at: datetime | None
    last_run_job_title: str | None
    last_run_job_id: int | None
    average_score: float | None
    embedder: str


class BackupOut(BaseModel):
    file: str
    size_bytes: int
    created_at: datetime
    reason: str
