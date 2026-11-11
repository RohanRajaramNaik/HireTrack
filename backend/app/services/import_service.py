"""Bulk candidate import (CSV / Excel) and CV text extraction.

Import rules
- The first row holds column names. Names are matched case-insensitively and
  a few common alternatives are accepted (see HEADER_ALIASES).
- Every row is validated with exactly the same rules as the Add Candidate form
  (schemas.CandidateIn). Invalid rows are reported with their row number and
  are not saved; valid rows are saved together in one transaction.
- A row whose email already belongs to a candidate is skipped, so importing the
  same file twice does not create duplicates.
"""
from __future__ import annotations

import csv
import io
import logging
import re
import zipfile

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..engine.skills import ALIASES, normaliser
from ..errors import AppError
from ..models import Candidate, CandidateSkill, Skill
from ..schemas import CandidateIn, ImportOut, ImportRowError
from .candidate_service import get_or_create_skills
from .seed_service import LEVEL_IDS

log = logging.getLogger("hiretrack.import")

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000
TEMPLATE_COLUMNS = [
    "full_name", "email", "phone", "location", "years_experience", "education",
    "previous_titles", "skills", "resume_summary",
]
HEADER_ALIASES = {
    "name": "full_name", "full name": "full_name", "candidate": "full_name",
    "email address": "email", "e-mail": "email",
    "phone number": "phone", "mobile": "phone", "cell": "phone",
    "city": "location",
    "years": "years_experience", "experience": "years_experience", "years of experience": "years_experience",
    "education level": "education", "qualification": "education", "level": "education", "level_id": "education",
    "titles": "previous_titles", "previous titles": "previous_titles", "job titles": "previous_titles",
    "summary": "resume_summary", "cv": "resume_summary", "cv summary": "resume_summary", "resume": "resume_summary",
    "resume summary": "resume_summary",
}
REQUIRED_COLUMNS = {"full_name", "years_experience", "education", "skills", "resume_summary"}


def template_csv() -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(TEMPLATE_COLUMNS)
    w.writerow(
        [
            "Ayanda Zulu", "ayanda.zulu@example.co.za", "+27 82 555 0101", "Durban", "4", "Bachelor's Degree",
            "Software Developer; Junior Developer", "Python; Django; SQL; Docker",
            "Backend developer who builds and maintains REST APIs in Python and Django for an online retailer, "
            "with automated tests and containerised deployments.",
        ]
    )
    return buf.getvalue()


# ------------------------------------------------------------------ parsing
def _canon_header(h) -> str:
    key = str(h or "").strip().lower().replace("_", " ")
    key = re.sub(r"\s+", " ", key)
    if key.replace(" ", "_") in TEMPLATE_COLUMNS:
        return key.replace(" ", "_")
    return HEADER_ALIASES.get(key, key.replace(" ", "_"))


def _read_rows(filename: str, content: bytes) -> list[dict]:
    if len(content) > MAX_BYTES:
        raise AppError("The file is larger than 5 MB. Split it into smaller files.", field="file", status_code=413)
    name = (filename or "").lower()
    if name.endswith(".csv"):
        text = _decode(content)
        rows = list(csv.reader(io.StringIO(text)))
    elif name.endswith(".xlsx"):
        from openpyxl import load_workbook

        try:
            wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:
            raise AppError("This Excel file could not be read. Save it as .xlsx and try again.", field="file") from exc
        ws = wb.worksheets[0]
        rows = [["" if v is None else v for v in r] for r in ws.iter_rows(values_only=True)]
        wb.close()
    else:
        raise AppError("Upload a .csv or .xlsx file", field="file", status_code=415)
    rows = [r for r in rows if any(str(v).strip() for v in r)]
    if not rows:
        raise AppError("The file is empty", field="file", status_code=422)
    header = [_canon_header(h) for h in rows[0]]
    missing = REQUIRED_COLUMNS - set(header)
    if missing:
        raise AppError(
            "Missing column(s): " + ", ".join(sorted(missing)) + ". Download the template to see the expected columns.",
            field="file",
            status_code=422,
        )
    body = rows[1:]
    if len(body) > MAX_ROWS:
        raise AppError(f"A file can hold at most {MAX_ROWS} candidates", field="file", status_code=422)
    return [{header[i]: row[i] if i < len(row) else "" for i in range(len(header))} for row in body]


def _decode(content: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(enc)
        except UnicodeDecodeError:
            continue
    raise AppError("The file's text encoding is not supported", field="file")  # pragma: no cover


def _level(value) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d+(\.0+)?", text):
        return int(float(text))
    return LEVEL_IDS.get(text.lower().replace("’", "'"))


def _skills(value) -> list[str]:
    text = str(value or "")
    sep = ";" if ";" in text else ","
    return [s.strip() for s in text.split(sep) if s.strip()]


def _to_input(row: dict) -> dict:
    years = str(row.get("years_experience", "")).strip()
    return {
        "full_name": str(row.get("full_name", "")).strip(),
        "email": str(row.get("email", "")).strip() or None,
        "phone": str(row.get("phone", "")).strip() or None,
        "location": str(row.get("location", "")).strip() or None,
        "years_experience": years if years else None,
        "level_id": _level(row.get("education")),
        "previous_titles": str(row.get("previous_titles", "")).strip() or None,
        "resume_summary": str(row.get("resume_summary", "")).strip(),
        "skills": _skills(row.get("skills")),
    }


def _friendly(err: dict) -> tuple[str | None, str]:
    loc = [str(p) for p in err.get("loc", [])]
    field = loc[0] if loc else None
    if field == "level_id":
        return "education", "Education must be one of the 7 levels (e.g. Diploma, Bachelor's Degree) or 1-7"
    msg = err.get("msg", "Invalid value").removeprefix("Value error, ")
    if err.get("type") == "missing" or (err.get("type") in ("int_type", "float_type") and err.get("input") is None):
        msg = "This value is required"
    elif err.get("type") == "string_too_short":
        msg = f"Must be at least {err.get('ctx', {}).get('min_length')} characters"
    elif err.get("type") == "string_too_long":
        msg = f"Must be {err.get('ctx', {}).get('max_length')} characters or fewer"
    elif err.get("type") == "less_than_equal":
        msg = f"Cannot be more than {err.get('ctx', {}).get('le')}"
    elif err.get("type") == "greater_than_equal":
        msg = f"Cannot be less than {err.get('ctx', {}).get('ge')}"
    return field, msg


# ------------------------------------------------------------------- import
def import_candidates(db: Session, filename: str, content: bytes) -> ImportOut:
    rows = _read_rows(filename, content)
    existing_emails = {e for e in db.scalars(select(func.lower(Candidate.email)).where(Candidate.email.is_not(None)))}
    errors: list[ImportRowError] = []
    valid: list[CandidateIn] = []
    skipped = 0
    seen_in_file: set[str] = set()
    for i, row in enumerate(rows, start=2):  # row 1 is the header
        try:
            data = CandidateIn(**_to_input(row))
        except ValidationError as exc:
            field, msg = _friendly(exc.errors()[0])
            errors.append(ImportRowError(row=i, field=field, message=msg))
            continue
        if data.email and (data.email in existing_emails or data.email in seen_in_file):
            skipped += 1
            continue
        if data.email:
            seen_in_file.add(data.email)
        valid.append(data)

    if valid:
        try:
            pairs_per_row = [normaliser.normalise_with_source(d.skills) for d in valid]
            skills = get_or_create_skills(db, sorted({p[0] for pairs in pairs_per_row for p in pairs}))
            for d, pairs in zip(valid, pairs_per_row):
                c = Candidate(
                    full_name=d.full_name,
                    email=d.email,
                    phone=d.phone,
                    location=d.location,
                    years_experience=d.years_experience,
                    level_id=d.level_id,
                    previous_titles=d.previous_titles or None,
                    resume_summary=d.resume_summary,
                )
                c.skills = [CandidateSkill(skill_id=skills[canon].skill_id, entered_as=ent[:60]) for canon, ent in pairs]
                db.add(c)
            db.commit()
        except Exception:
            db.rollback()
            log.exception("Bulk import failed; rolled back")
            raise
    log.info("Imported %d candidates (%d skipped, %d errors)", len(valid), skipped, len(errors))
    if valid:
        from .seed_service import warm_embeddings_async

        warm_embeddings_async()
    return ImportOut(created=len(valid), skipped=skipped, errors=errors[:200])


# ------------------------------------------------------------ CV extraction
# Common IT skills recognised in a CV even before any candidate has them.
# Short words that are also ordinary English ("go") are left out on purpose.
COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "c#", "c++", ".net", "sql", "nosql", "html", "css", "react",
    "angular", "vue", "node.js", "django", "flask", "fastapi", "spring", "kotlin", "swift", "android", "ios",
    "php", "laravel", "ruby", "rails", "rest apis", "graphql", "microservices", "git", "docker", "kubernetes",
    "terraform", "ansible", "linux", "bash", "powershell", "aws", "azure", "gcp", "ci/cd", "jenkins",
    "github actions", "postgresql", "mysql", "sql server", "oracle", "mongodb", "redis", "kafka", "spark",
    "airflow", "dbt", "snowflake", "databricks", "etl", "data modelling", "data warehousing", "power bi",
    "tableau", "excel", "statistics", "machine learning", "scikit-learn", "pandas", "numpy", "tensorflow",
    "pytorch", "selenium", "playwright", "cypress", "jira", "agile", "scrum", "networking", "cisco", "firewalls",
    "active directory", "siem", "splunk", "penetration testing", "owasp", "iso 27001", "itil",
    "troubleshooting", "project management", "stakeholder management", "requirements analysis", "uml",
]
AMBIGUOUS = {"go", "r", "c", "vb", "ts"}

EMAIL_IN_TEXT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_IN_TEXT = re.compile(r"(?:\+27|0)[\s-]?\d{2}[\s-]?\d{3}[\s-]?\d{4}")


def _pdf_text(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content))
    return "\n".join((page.extract_text() or "") for page in reader.pages[:10])


def _docx_text(content: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", " ", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'")):
        text = text.replace(ent, ch)
    return text


def extract_cv(db: Session, filename: str, content: bytes) -> dict:
    """Read a CV file and return text plus details found in it, to pre-fill the form.

    Nothing is saved: the recruiter reviews and corrects the form first.
    """
    if len(content) > MAX_BYTES:
        raise AppError("The file is larger than 5 MB", field="file", status_code=413)
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            text = _pdf_text(content)
        elif name.endswith(".docx"):
            text = _docx_text(content)
        elif name.endswith(".txt"):
            text = _decode(content)
        else:
            raise AppError("Upload a .pdf, .docx or .txt CV", field="file", status_code=415)
    except AppError:
        raise
    except Exception as exc:
        raise AppError("This CV could not be read. Try saving it as PDF or plain text.", field="file") from exc
    clean = re.sub(r"[ \t]+", " ", text)
    clean = re.sub(r"\n\s*\n+", "\n", clean).strip()
    if len(clean) < 20:
        raise AppError(
            "No readable text was found in this file (it may be a scanned image)", field="file", status_code=422
        )
    summary = re.sub(r"\s+", " ", clean)
    truncated = len(summary) > 3000
    summary = summary[:3000].rsplit(" ", 1)[0] if truncated else summary

    known = (set(db.scalars(select(Skill.name))) | set(ALIASES) | set(ALIASES.values()) | set(COMMON_SKILLS)) - AMBIGUOUS
    lowered = " " + re.sub(r"\s+", " ", clean.lower()) + " "
    found: list[str] = []
    for term in sorted(known, key=len, reverse=True):
        if len(term) < 2:
            continue
        if re.search(r"(?<![\w+#.])" + re.escape(term) + r"(?![\w+#])", lowered):
            canon = normaliser.normalise(term)
            if canon not in found:
                found.append(canon)
    email = EMAIL_IN_TEXT.search(clean)
    phone = PHONE_IN_TEXT.search(clean)
    first_line = clean.splitlines()[0].strip() if clean else ""
    name_guess = first_line if 2 <= len(first_line) <= 60 and not any(ch.isdigit() for ch in first_line) else None
    return {
        "resume_summary": summary,
        "truncated": truncated,
        "skills": found[:25],
        "email": email.group(0).lower() if email else None,
        "phone": phone.group(0) if phone else None,
        "full_name": name_guess,
        "characters": len(clean),
    }
