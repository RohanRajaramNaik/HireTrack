"""Shared test data and helpers for the integration tests."""
from __future__ import annotations

from datetime import date, timedelta

CAND = {
    "full_name": "Ayanda Zulu",
    "email": "ayanda@example.com",
    "phone": "+27 82 555 0101",
    "location": "Durban",
    "years_experience": 4,
    "level_id": 4,
    "previous_titles": "Software Developer",
    "resume_summary": "Backend developer building REST APIs in Python and Django with automated tests.",
    "skills": ["Python", "Django", "SQL"],
}

JOB = {
    "job_title": "Backend Developer",
    "location": "Cape Town",
    "status": "open",
    "min_experience": 3,
    "min_level_id": 4,
    "job_description": "Build and maintain REST APIs in Python and Django, with tests and code reviews.",
    "required_skills": ["Python", "Django"],
    "preferred_skills": ["Docker"],
    "w_skills": 40,
    "w_experience": 25,
    "w_education": 15,
    "w_semantic": 20,
}

TODAY = date.today()


def iso(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


PROJECT = {
    "name": "Claims Portal",
    "client": "Fynbos Insurance",
    "description": "Online claims portal",
    "start_date": iso(-30),
    "end_date": iso(90),
    "status": "active",
}

STAFF = {"full_name": "Johan Venter", "email": "johan@staff.example", "role_title": "Software Developer", "location": "Pretoria"}


def created(r, status=201):
    assert r.status_code == status, r.text
    return r.json()


def make_candidate(client, **over):
    return created(client.post("/api/candidates", json={**CAND, **over}))


def make_job(client, **over):
    return created(client.post("/api/jobs", json={**JOB, **over}))


def make_application(client, candidate_id, job_id, **over):
    return created(client.post("/api/applications", json={"candidate_id": candidate_id, "job_id": job_id, **over}))


def move(client, app_id, stage, note=None):
    return client.post(f"/api/applications/{app_id}/stage", json={"stage": stage, "note": note})


def assert_error(r, status, field=None, contains=None):
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"detail", "field"}, body
    if field is not None:
        assert body["field"] == field, body
    if contains:
        assert contains.lower() in body["detail"].lower(), body
