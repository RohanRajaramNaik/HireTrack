"""Pydantic request/response models.

Validation errors are turned into {"detail": "...", "field": "..."} by the
handler in main.py. Model-level errors raise FieldError so they can name the
field the message belongs to (e.g. "weights").
"""
from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .engine.scoring import Weights, WeightError, validate_skill_lists
from .engine.skills import normaliser

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9 ()\-]{7,20}$")


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
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=80)
    years_experience: float = Field(ge=0, le=50)
    level_id: int = Field(ge=1, le=7)
    previous_titles: str | None = Field(default=None, max_length=500)
    resume_summary: str = Field(min_length=20, max_length=3000)
    skills: list[str]

    _strip_text = field_validator(
        "full_name", "email", "phone", "location", "previous_titles", "resume_summary", mode="before"
    )(_strip)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v in (None, ""):
            return None
        if not PHONE_RE.match(v):
            raise ValueError("Enter a valid phone number (digits, spaces, +, - and brackets only)")
        return v

    @field_validator("location")
    @classmethod
    def _location(cls, v: str | None) -> str | None:
        return v or None

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
    phone: str | None = None
    location: str | None = None
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
    location: str = Field(min_length=2, max_length=80)
    status: str = Field(default="open", pattern="^(open|closed)$")
    min_experience: float = Field(default=0, ge=0, le=50)
    min_level_id: int = Field(ge=1, le=7)
    job_description: str = Field(min_length=20, max_length=5000)
    required_skills: list[str]
    preferred_skills: list[str] = []
    w_skills: int = Field(default=40, ge=0, le=100)
    w_experience: int = Field(default=25, ge=0, le=100)
    w_education: int = Field(default=15, ge=0, le=100)
    w_semantic: int = Field(default=20, ge=0, le=100)

    _strip_text = field_validator("job_title", "created_by", "location", "job_description", mode="before")(_strip)

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
    location: str
    status: str
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
    location: str | None = None
    pipeline_stage: str | None = None
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


# --------------------------------------------------------------------------
# Auth and users
# --------------------------------------------------------------------------
PASSWORD_RULE = "Password must be at least 8 characters and include a letter and a number"


def _check_password(v: str | None) -> str | None:
    if v is None:
        return v
    if len(v) < 8 or len(v) > 72 or not re.search(r"[A-Za-z]", v) or not re.search(r"[0-9]", v):
        raise ValueError(PASSWORD_RULE)
    return v


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=72)

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        return v.strip().lower() if isinstance(v, str) else v


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    user_id: int
    full_name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


class UserIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(max_length=254)
    role: str = Field(pattern="^(admin|recruiter|resource_manager)$")
    password: str | None = None
    is_active: bool = True

    _strip_text = field_validator("full_name", mode="before")(_strip)

    @field_validator("email", mode="before")
    @classmethod
    def _email(cls, v):
        v = v.strip().lower() if isinstance(v, str) else v
        if not isinstance(v, str) or not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v):
        return _check_password(v or None)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=72)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, v):
        return _check_password(v)


# --------------------------------------------------------------------------
# Applicant pipeline
# --------------------------------------------------------------------------
class ApplicationIn(BaseModel):
    candidate_id: int = Field(ge=1)
    job_id: int = Field(ge=1)
    match_score: float | None = Field(default=None, ge=0, le=100)
    note: str | None = Field(default=None, max_length=500)


class BulkApplicationIn(BaseModel):
    job_id: int = Field(ge=1)
    candidate_ids: list[int] = Field(min_length=1, max_length=200)


class StageChangeIn(BaseModel):
    stage: str = Field(pattern="^(applied|screened|interview|offer|hired|rejected)$")
    note: str | None = Field(default=None, max_length=500)

    _strip_text = field_validator("note", mode="before")(_strip)


class ApplicationEventOut(BaseModel):
    event_id: int
    from_stage: str | None
    to_stage: str
    changed_by_name: str | None
    changed_at: datetime
    note: str | None


class ApplicationOut(BaseModel):
    application_id: int
    candidate_id: int
    candidate_name: str
    candidate_titles: str | None
    candidate_location: str | None
    years_experience: float
    job_id: int
    job_title: str
    stage: str
    match_score: float | None
    applied_at: datetime
    updated_at: datetime
    allowed_moves: list[str]
    events: list[ApplicationEventOut] | None = None


# --------------------------------------------------------------------------
# Resource allocation
# --------------------------------------------------------------------------
class StaffIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str | None = Field(default=None, max_length=254)
    role_title: str = Field(min_length=2, max_length=100)
    location: str | None = Field(default=None, max_length=80)
    is_active: bool = True

    _strip_text = field_validator("full_name", "email", "role_title", "location", mode="before")(_strip)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        if v in (None, ""):
            return None
        if not EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address, or leave it blank")
        return v.lower()


class StaffOut(BaseModel):
    staff_id: int
    full_name: str
    email: str | None
    role_title: str
    location: str | None
    source: str
    candidate_id: int | None
    is_active: bool
    utilisation: int
    band: str
    current_projects: list[str]


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    client: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    start_date: date
    end_date: date
    status: str = Field(default="planned", pattern="^(planned|active|on_hold|completed)$")

    _strip_text = field_validator("name", "client", "description", mode="before")(_strip)

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise FieldError("end_date", "End date cannot be before the start date")
        return self


class AllocationIn(BaseModel):
    staff_id: int = Field(ge=1)
    project_id: int = Field(ge=1)
    role_on_project: str | None = Field(default=None, max_length=100)
    allocation_percent: int = Field(ge=1, le=100)
    start_date: date
    end_date: date

    _strip_text = field_validator("role_on_project", mode="before")(_strip)

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise FieldError("end_date", "End date cannot be before the start date")
        return self


class AllocationOut(BaseModel):
    allocation_id: int
    staff_id: int
    staff_name: str
    staff_role: str
    project_id: int
    project_name: str
    role_on_project: str | None
    allocation_percent: int
    start_date: date
    end_date: date
    is_current: bool


class ProjectOut(BaseModel):
    project_id: int
    name: str
    client: str
    description: str | None
    start_date: date
    end_date: date
    status: str
    team_size: int
    allocated_percent: int
    allocations: list[AllocationOut] | None = None


# --------------------------------------------------------------------------
# Bulk import
# --------------------------------------------------------------------------
class ImportRowError(BaseModel):
    row: int
    field: str | None
    message: str


class ImportOut(BaseModel):
    created: int
    skipped: int
    errors: list[ImportRowError]
