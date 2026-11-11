"""Generate the report diagrams as SVG (rendered to PNG by render.mjs).

    python docs/diagrams/make_diagrams.py
    node frontend/e2e/render-diagrams.mjs

Diagrams: architecture.svg, erd.svg, pipeline-states.svg, allocation-flow.svg
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent
INK = "#0f172a"
MUTED = "#475569"
LINE = "#94a3b8"
ACCENT = "#1d3fbf"
SOFT = "#eef2ff"
GO = "#157a3b"
FONT = "Segoe UI, Inter, Arial, sans-serif"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(w: int, h: int, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{FONT}">\n<rect width="{w}" height="{h}" fill="#ffffff"/>\n'
        '<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{MUTED}"/></marker></defs>\n'
        f"{body}</svg>\n"
    )


def text(x, y, s, size=14, weight=400, fill=INK, anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>\n'


def box(x, y, w, h, fill="#ffffff", stroke=LINE, rx=8, dash=None, sw=1.5):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>\n'


def arrow(points, label=None, lx=None, ly=None, both=False, color=MUTED):
    pts = " ".join(f"{x},{y}" for x, y in points)
    start = ' marker-start="url(#arr)"' if both else ""
    out = f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.6" marker-end="url(#arr)"{start}/>\n'
    if label:
        out += text(lx, ly, label, 12, 400, MUTED, "middle")
    return out


# ------------------------------------------------------------- architecture
def architecture() -> str:
    b = ""
    b += text(40, 44, "HireTrack: three-tier architecture (one computer, 127.0.0.1)", 22, 700)
    # Tier labels
    tiers = [(80, "Presentation tier"), (330, "Application tier"), (820, "Data tier")]
    for y, t in tiers:
        b += text(40, y, t.upper(), 12, 700, MUTED)
    # Presentation
    b += box(40, 92, 1120, 196, "#f8fafc")
    b += text(60, 120, "Web browser (Edge, Chrome) - React 18 single-page app built with Vite, styled with Tailwind CSS", 15, 600)
    pages = ["Sign in", "Dashboard", "Candidates", "Jobs", "Matching", "Pipeline", "Resources", "Admin"]
    for i, p in enumerate(pages):
        x = 60 + i * 136
        b += box(x, 138, 124, 44, "#ffffff", ACCENT, 6)
        b += text(x + 62, 166, p, 14, 600, ACCENT, "middle")
    b += box(60, 198, 520, 74, "#ffffff")
    b += text(76, 222, "lib/auth.jsx  - signed-in user, role checks (can())", 13, 400, INK)
    b += text(76, 244, "lib/validation.js - same rules as the server, inline errors", 13, 400, INK)
    b += text(76, 264, "lib/scoring.js - client re-rank for 'What if' weights", 13, 400, INK)
    b += box(600, 198, 540, 74, "#ffffff")
    b += text(616, 222, "apiClient.js - one place for every HTTP call", 13, 400, INK)
    b += text(616, 244, "sends Authorization: Bearer <JWT>; 401 signs the user out", 13, 400, INK)
    b += text(616, 264, "uploads (CV, CSV/XLSX) and authenticated CSV download", 13, 400, INK)
    # arrow to API
    b += arrow([(600, 290), (600, 340)], both=True)
    b += text(612, 322, "HTTP + JSON (REST)   /api/...   JWT bearer token", 13, 600, MUTED)
    # Application tier
    b += box(40, 344, 1120, 440, "#f8fafc")
    b += text(60, 372, "FastAPI application served by Uvicorn (Python 3.11) - also serves the built frontend on the same port", 15, 600)
    # security strip
    b += box(60, 388, 1080, 52, SOFT, ACCENT, 6)
    b += text(76, 410, "security.py - bcrypt passwords, JWT (HS256, 8 h), require_roles(...) on every route, login lock-out,", 13, 400, INK)
    b += text(76, 430, "password re-confirmation for destructive admin actions.  main.py - one error shape {detail, field}, CORS 127.0.0.1 only", 13, 400, INK)
    # routers
    routers = ["auth / users", "candidates (+ import, CV)", "jobs", "match / dashboard", "pipeline", "resources", "admin"]
    x = 60
    b += text(60, 466, "Routers (HTTP layer, Pydantic validation)", 13, 700, MUTED)
    for r in routers:
        w = 136 if len(r) < 14 else 168
        b += box(x, 476, w, 38, "#ffffff")
        b += text(x + w / 2, 500, r, 13, 600, INK, "middle")
        x += w + 10
    b += arrow([(600, 516), (600, 538)])
    b += text(60, 560, "Services (business rules, transactions)", 13, 700, MUTED)
    services = ["user", "candidate", "import", "job", "match", "pipeline", "resource", "dashboard", "seed", "backup"]
    x = 60
    for s in services:
        b += box(x, 570, 99, 36, "#ffffff")
        b += text(x + 49.5, 593, s, 13, 600, INK, "middle")
        x += 108
    b += arrow([(600, 608), (600, 630)])
    b += text(60, 652, "Engine (pure Python, no database code, unit tested on its own)", 13, 700, MUTED)
    engine = [
        ("scoring.py", "skills, experience, education,", "meaning, overall, ranking"),
        ("embeddings.py", "all-MiniLM-L6-v2 vectors,", "cached by text hash"),
        ("skills.py", "SkillNormaliser,", "~90 aliases (JS, K8s...)"),
        ("pipeline.py", "stage order, allowed moves,", "funnel"),
        ("allocation.py", "peak load per day,", "no booking above 100%"),
    ]
    for i, (n, l1, l2) in enumerate(engine):
        x = 60 + i * 218
        b += box(x, 662, 206, 100, "#ffffff", ACCENT, 6)
        b += text(x + 14, 688, n, 14, 700, ACCENT)
        b += text(x + 14, 712, l1, 12, 400, INK)
        b += text(x + 14, 732, l2, 12, 400, INK)
    b += arrow([(600, 786), (600, 836)], both=True)
    b += text(612, 816, "SQLAlchemy 2 ORM (bound parameters only; PRAGMA foreign_keys=ON)", 13, 600, MUTED)
    # data tier
    data = [
        ("data/hiretrack.db", "SQLite database: 14 tables,", "CHECK, UNIQUE and FK rules"),
        ("models/all-MiniLM-L6-v2", "local language model (~90 MB),", "downloaded once, then offline"),
        ("data/embedding_cache.npz", "CV vectors keyed by SHA-1", "(no CV text stored)"),
        ("backups/", "daily, pre-seed, pre-restore and", "manual copies (10 kept)"),
        ("logs/app.log", "rotating 1 MB x 5;", "ids and counts only"),
    ]
    for i, (n, l1, l2) in enumerate(data):
        x = 40 + i * 226
        b += box(x, 840, 214, 96, "#ffffff")
        b += text(x + 14, 866, n, 13, 700, INK)
        b += text(x + 14, 890, l1, 12, 400, MUTED)
        b += text(x + 14, 910, l2, 12, 400, MUTED)
    b += text(40, 970, "Internet is used only during installation (pip, npm, model download). At run time HF_HUB_OFFLINE=1 and the server binds to 127.0.0.1.", 13, 400, MUTED)
    return svg(1200, 990, b)


# ---------------------------------------------------------------------- ERD
ENTITIES = {
    "education_level": (40, 40, ["PK level_id", "level_name (UQ)"]),
    "candidate": (40, 190, ["PK candidate_id", "full_name", "email, phone, location", "years_experience", "FK level_id", "previous_titles", "resume_summary", "created_at"]),
    "candidate_skill": (40, 510, ["PK,FK candidate_id", "PK,FK skill_id", "entered_as"]),
    "skill": (40, 680, ["PK skill_id", "name (UQ, lower case)"]),
    "job_specification": (440, 40, ["PK job_id", "job_title, location, status", "min_experience", "FK min_level_id", "job_description", "w_skills, w_experience,", "w_education, w_semantic", "created_by, created_at"]),
    "job_skill": (440, 400, ["PK,FK job_id", "PK,FK skill_id", "skill_type (required|preferred)"]),
    "match_run": (440, 560, ["PK run_id", "FK job_id", "run_at, duration_ms", "candidate_count, weights used"]),
    "match_result": (840, 40, ["PK result_id", "FK candidate_id", "FK job_id", "skills/experience/education/", "semantic/overall score", "rank", "matched/missing skills (JSON)", "explanation, run_at"]),
    "application": (840, 400, ["PK application_id", "FK candidate_id", "FK job_id", "stage", "match_score", "applied_at, updated_at", "UQ (candidate_id, job_id)"]),
    "application_event": (840, 650, ["PK event_id", "FK application_id", "from_stage, to_stage", "FK changed_by", "changed_at, note"]),
    "app_user": (1240, 40, ["PK user_id", "full_name", "email (UQ)", "password_hash (bcrypt)", "role", "is_active, last_login_at"]),
    "staff_member": (1240, 300, ["PK staff_id", "full_name, email", "role_title, location", "FK candidate_id (UQ, nullable)", "source (existing|hired)", "is_active"]),
    "allocation": (1240, 560, ["PK allocation_id", "FK staff_id", "FK project_id", "role_on_project", "allocation_percent (1-100)", "start_date, end_date"]),
    "project": (1240, 820, ["PK project_id", "name (UQ), client", "description", "start_date, end_date", "status"]),
}
W_ENT = 340
ROW = 22


def ent_h(name):
    return 34 + len(ENTITIES[name][2]) * ROW + 8


def ent(name):
    x, y, cols = ENTITIES[name]
    h = ent_h(name)
    b = box(x, y, W_ENT, h, "#ffffff", INK, 4, sw=1.4)
    b += f'<rect x="{x}" y="{y}" width="{W_ENT}" height="30" rx="4" fill="{ACCENT}"/>\n'
    b += f'<rect x="{x}" y="{y + 20}" width="{W_ENT}" height="10" fill="{ACCENT}"/>\n'
    b += text(x + 12, y + 21, name.upper(), 14, 700, "#ffffff")
    for i, c in enumerate(cols):
        weight = 700 if c.startswith("PK") else 400
        color = ACCENT if c.startswith("FK") or c.startswith("PK,FK") else INK
        b += text(x + 12, y + 50 + i * ROW, c, 13, weight, color)
    return b


def side(name, s, frac=0.5):
    x, y, _ = ENTITIES[name]
    h = ent_h(name)
    return {
        "l": (x, y + h * frac),
        "r": (x + W_ENT, y + h * frac),
        "t": (x + W_ENT * frac, y),
        "b": (x + W_ENT * frac, y + h),
    }[s]


def rel(points, one_end, many_end):
    """Line with '1' near the first point and 'N' near the last."""
    pts = " ".join(f"{x},{y}" for x, y in points)
    b = f'<polyline points="{pts}" fill="none" stroke="{MUTED}" stroke-width="1.5"/>\n'
    (x0, y0), (x1, y1) = points[0], points[-1]
    b += text(one_end[0], one_end[1], "1", 13, 700, MUTED, "middle")
    b += text(many_end[0], many_end[1], "N", 13, 700, MUTED, "middle")
    b += f'<circle cx="{x1}" cy="{y1}" r="3.5" fill="{MUTED}"/>\n'
    return b


def erd() -> str:
    b = text(40, 26, "HireTrack database (3NF) - 14 tables. N = many; the dot marks the 'many' side.", 16, 700)
    b = b.replace('y="26"', 'y="24"')
    body = ""
    for n in ENTITIES:
        body += ent(n)
    lines = ""
    # education_level 1-N candidate
    lines += rel([side("education_level", "b", 0.3), side("candidate", "t", 0.3)], (130, 140), (130, 184))
    # education_level 1-N job (min level)
    p0 = side("education_level", "r", 0.5)
    lines += rel([p0, (410, p0[1]), (410, 150), (440, 150)], (p0[0] + 12, p0[1] - 6), (430, 145))
    # candidate 1-N candidate_skill
    lines += rel([side("candidate", "b", 0.3), side("candidate_skill", "t", 0.3)], (130, 486), (130, 504))
    # skill 1-N candidate_skill
    lines += rel([side("skill", "t", 0.3), side("candidate_skill", "b", 0.3)], (130, 674), (130, 624))
    # skill 1-N job_skill
    ps = side("skill", "r", 0.5)
    lines += rel([ps, (420, ps[1]), (420, 450), (440, 450)], (ps[0] + 12, ps[1] - 6), (430, 444))
    # job 1-N job_skill
    lines += rel([side("job_specification", "b", 0.3), side("job_skill", "t", 0.3)], (530, 352), (530, 394))
    # job_skill... job 1-N match_run
    pj = side("job_specification", "l", 0.85)
    lines += rel([pj, (400, pj[1]), (400, 610), (440, 610)], (428, pj[1] - 6), (430, 604))
    # job 1-N match_result
    lines += rel([side("job_specification", "r", 0.2), (840, side("job_specification", "r", 0.2)[1])], (796, 84), (832, 84))
    # job 1-N application
    pa = side("job_specification", "r", 0.75)
    lines += rel([pa, (810, pa[1]), (810, 470), (840, 470)], (796, pa[1] - 6), (830, 464))
    # candidate 1-N match_result / application (via a bus line at x=420? route right side)
    pc = side("candidate", "r", 0.4)
    lines += rel([pc, (395, pc[1]), (395, 20), (820, 20), (820, 110), (840, 110)], (pc[0] + 12, pc[1] - 6), (830, 104))
    pc2 = side("candidate", "r", 0.7)
    lines += rel([pc2, (405, pc2[1]), (405, 380), (800, 380), (800, 494), (840, 494)], (pc2[0] + 12, pc2[1] - 6), (830, 488))
    # application 1-N application_event
    lines += rel([side("application", "b", 0.3), side("application_event", "t", 0.3)], (930, 612), (930, 644))
    # app_user 1-N application_event (changed_by)
    pu = side("app_user", "l", 0.85)
    lines += rel([pu, (1215, pu[1]), (1215, 760), (1180, 760)], (1228, pu[1] - 6), (1192, 754))
    # candidate 1-0..1 staff_member (hired)
    pc3 = side("candidate", "b", 0.8)
    lines += rel([pc3, (312, 496), (395, 496), (395, 990), (1220, 990), (1220, 420), (1240, 420)], (312, 488), (1230, 414))
    lines += text(800, 984, "a hired candidate becomes one staff member (0..1)", 12, 400, MUTED, "middle")
    # staff 1-N allocation
    lines += rel([side("staff_member", "b", 0.3), side("allocation", "t", 0.3)], (1330, 534), (1330, 554))
    # project 1-N allocation
    lines += rel([side("project", "t", 0.3), side("allocation", "b", 0.3)], (1330, 814), (1330, 772))
    return svg(1620, 1050, b + '<g transform="translate(0,40)">' + lines + body + "</g>")


# -------------------------------------------------------------- pipeline
def pipeline_states() -> str:
    b = text(40, 40, "Applicant pipeline: allowed stage changes (engine/pipeline.py)", 20, 700)
    stages = ["Applied", "Screened", "Interview", "Offer", "Hired"]
    xs = [60 + i * 230 for i in range(5)]
    for i, (x, s) in enumerate(zip(xs, stages)):
        final = s == "Hired"
        b += box(x, 110, 170, 60, SOFT if not final else "#ecfaf1", ACCENT if not final else GO, 30, sw=2)
        b += text(x + 85, 146, s, 16, 700, ACCENT if not final else GO, "middle")
        if i < 4:
            b += arrow([(x + 172, 140), (xs[i + 1] - 4, 140)])
    b += box(520, 300, 170, 60, "#f1f5f9", MUTED, 30, sw=2)
    b += text(605, 336, "Rejected", 16, 700, MUTED, "middle")
    for x in xs[:4]:
        b += f'<path d="M{x + 85},172 C{x + 85},250 {600},230 {605},298" fill="none" stroke="{MUTED}" stroke-width="1.4" stroke-dasharray="5 4" marker-end="url(#arr)"/>\n'
    b += f'<path d="M520,330 C330,330 160,250 145,174" fill="none" stroke="{ACCENT}" stroke-width="1.4" marker-end="url(#arr)"/>\n'
    b += text(120, 360, "reopen: back to the stage", 12, 400, ACCENT, "middle")
    b += text(120, 376, "it was rejected from", 12, 400, ACCENT, "middle")
    notes = [
        "Rules",
        "- One stage forward at a time; stages cannot be skipped or reversed.",
        "- Any open stage can be rejected (dashed). Hired is final.",
        "- Every change writes an application_event row: from, to, user, time, note.",
        "- Moving to Hired adds the person to the staff pool for allocation.",
        "- A closed job accepts no new applicants and no further hires.",
    ]
    for i, n in enumerate(notes):
        b += text(760, 270 + i * 22, n, 13, 700 if i == 0 else 400, INK)
    return svg(1260, 420, b)


# -------------------------------------------------------- allocation flow
def allocation_flow() -> str:
    b = text(40, 40, "Allocation check: can this person take on more work for these dates?", 20, 700)
    steps = [
        ("Request", "staff, project, %,", "start and end date"),
        ("Basic rules", "1-100%, end >= start,", "dates inside project"),
        ("Collect bookings", "this person's allocations on", "planned / active projects"),
        ("Peak load", "check each day the load can", "change (sweep), add new %"),
        ("Decision", "peak <= 100%: save", "peak > 100%: refuse + reason"),
    ]
    for i, (t, l1, l2) in enumerate(steps):
        x = 40 + i * 236
        b += box(x, 80, 212, 100, "#ffffff", ACCENT if i == 4 else LINE, 8, sw=1.6)
        b += text(x + 14, 108, f"{i + 1}. {t}", 15, 700, ACCENT if i == 4 else INK)
        b += text(x + 14, 136, l1, 13, 400, MUTED)
        b += text(x + 14, 156, l2, 13, 400, MUTED)
        if i < 4:
            b += arrow([(x + 214, 130), (x + 234, 130)])
    b += text(40, 224, "Example: already 70% on Claims Portal for March to May; a new 50% booking in April would peak at 120%.", 13, 400, INK)
    b += text(40, 246, "Message shown: 'This would book the person at 120% on 01 Apr 2026 (already 70% allocated). The most you can add for these dates is 30%.'", 13, 400, MUTED)
    return svg(1240, 270, b)


if __name__ == "__main__":
    for name, fn in [("architecture", architecture), ("erd", erd), ("pipeline-states", pipeline_states), ("allocation-flow", allocation_flow)]:
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print("wrote", name)
