"""API tests through FastAPI's TestClient (isolated temporary database)."""
import pytest

CAND = {
    "full_name": "Thandiwe Nkosi",
    "email": "thandiwe@example.com",
    "years_experience": 5,
    "level_id": 4,
    "previous_titles": "Data Engineer",
    "resume_summary": "Builds batch and streaming data pipelines in Python and SQL on AWS.",
    "skills": ["Python", "SQL", "AWS"],
}

JOB = {
    "job_title": "Data Engineer",
    "created_by": "Recruiter",
    "min_experience": 3,
    "min_level_id": 4,
    "job_description": "Design and run data pipelines in Python and SQL on AWS for analytics teams.",
    "required_skills": ["Python", "SQL"],
    "preferred_skills": ["AWS"],
    "w_skills": 40,
    "w_experience": 25,
    "w_education": 15,
    "w_semantic": 20,
}


def make_candidate(client, **over):
    r = client.post("/api/candidates", json={**CAND, **over})
    assert r.status_code == 201, r.text
    return r.json()


def make_job(client, **over):
    r = client.post("/api/jobs", json={**JOB, **over})
    assert r.status_code == 201, r.text
    return r.json()


def assert_error(r, status, field=None, contains=None):
    assert r.status_code == status, r.text
    body = r.json()
    assert set(body) == {"detail", "field"}
    if field is not None:
        assert body["field"] == field, body
    if contains:
        assert contains.lower() in body["detail"].lower(), body


# ------------------------------------------------------------ misc
def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_education_levels(client):
    levels = client.get("/api/education-levels").json()
    assert [lv["level_name"] for lv in levels][:2] == ["Matric", "Higher Certificate"]
    assert len(levels) == 7


def test_stats_empty(client):
    s = client.get("/api/stats").json()
    assert s["candidates"] == 0 and s["jobs"] == 0 and s["last_run_at"] is None


# ------------------------------------------------------ candidates
class TestCandidates:
    def test_crud(self, client):
        c = make_candidate(client, skills=["JS", "Postgres", "javascript"])
        assert c["skills"] == ["JS", "Postgres"]  # deduped after alias normalisation
        cid = c["candidate_id"]
        assert client.get(f"/api/candidates/{cid}").json()["full_name"] == "Thandiwe Nkosi"
        r = client.put(f"/api/candidates/{cid}", json={**CAND, "full_name": "Thandi Nkosi"})
        assert r.status_code == 200 and r.json()["full_name"] == "Thandi Nkosi"
        assert client.delete(f"/api/candidates/{cid}").status_code == 204
        assert_error(client.get(f"/api/candidates/{cid}"), 404)

    def test_search_and_pagination(self, client):
        for i in range(5):
            make_candidate(client, full_name=f"Person {i}", skills=["Python"] if i % 2 else ["Excel"])
        r = client.get("/api/candidates", params={"page_size": 2, "page": 2}).json()
        assert r["total"] == 5 and len(r["items"]) == 2 and r["page"] == 2
        assert client.get("/api/candidates", params={"search": "person 3"}).json()["total"] == 1
        # skill search uses the alias table: "py" finds python
        assert client.get("/api/candidates", params={"search": "py"}).json()["total"] == 2

    def test_sorting(self, client):
        make_candidate(client, full_name="Bongani", years_experience=2)
        make_candidate(client, full_name="Ayanda", years_experience=9)
        names = [c["full_name"] for c in client.get("/api/candidates", params={"sort": "years", "order": "desc"}).json()["items"]]
        assert names == ["Ayanda", "Bongani"]

    def test_search_is_parameterised(self, client):
        make_candidate(client)
        r = client.get("/api/candidates", params={"search": "' OR 1=1 --"})
        assert r.status_code == 200 and r.json()["total"] == 0

    def test_negative_years(self, client):
        assert_error(client.post("/api/candidates", json={**CAND, "years_experience": -1}), 422, "years_experience", "less than 0")

    def test_years_over_50(self, client):
        assert_error(client.post("/api/candidates", json={**CAND, "years_experience": 51}), 422, "years_experience")

    def test_empty_name(self, client):
        assert_error(client.post("/api/candidates", json={**CAND, "full_name": "   "}), 422, "full_name")

    def test_missing_name(self, client):
        body = {k: v for k, v in CAND.items() if k != "full_name"}
        assert_error(client.post("/api/candidates", json=body), 422, "full_name", "required")

    def test_short_summary(self, client):
        assert_error(client.post("/api/candidates", json={**CAND, "resume_summary": "too short"}), 422, "resume_summary", "20")

    def test_no_skills(self, client):
        assert_error(client.post("/api/candidates", json={**CAND, "skills": ["  "]}), 422, "skills", "at least one skill")

    def test_bad_email(self, client):
        assert_error(client.post("/api/candidates", json={**CAND, "email": "nope"}), 422, "email")

    def test_blank_email_ok(self, client):
        assert make_candidate(client, email="")["email"] is None

    def test_bad_level(self, client):
        assert_error(client.post("/api/candidates", json={**CAND, "level_id": 9}), 422, "level_id")

    def test_update_missing(self, client):
        assert_error(client.put("/api/candidates/999", json=CAND), 404)


# ------------------------------------------------------------ jobs
class TestJobs:
    def test_crud(self, client):
        j = make_job(client, required_skills=["py", "SQL"], preferred_skills=["k8s"])
        assert j["required_skills"] == ["python", "sql"] and j["preferred_skills"] == ["kubernetes"]
        jid = j["job_id"]
        assert len(client.get("/api/jobs").json()) == 1
        r = client.put(f"/api/jobs/{jid}", json={**JOB, "job_title": "Senior Data Engineer"})
        assert r.json()["job_title"] == "Senior Data Engineer"
        assert client.delete(f"/api/jobs/{jid}").status_code == 204
        assert_error(client.get(f"/api/jobs/{jid}"), 404)

    def test_weights_95(self, client):
        r = client.post("/api/jobs", json={**JOB, "w_semantic": 15})
        assert_error(r, 422, "weights")
        assert r.json()["detail"] == "Weights must add up to 100% (now 95%)"

    def test_weights_over_100(self, client):
        assert_error(client.post("/api/jobs", json={**JOB, "w_skills": 50}), 422, "weights", "now 110%")

    def test_weight_negative(self, client):
        assert_error(client.post("/api/jobs", json={**JOB, "w_skills": -5, "w_experience": 70}), 422, "w_skills")

    def test_preferred_repeats_required(self, client):
        r = client.post("/api/jobs", json={**JOB, "preferred_skills": ["Python", "AWS"]})
        assert_error(r, 422, "preferred_skills", "repeat required")

    def test_preferred_repeats_required_via_alias(self, client):
        r = client.post("/api/jobs", json={**JOB, "required_skills": ["JavaScript"], "preferred_skills": ["JS"]})
        assert_error(r, 422, "preferred_skills", "javascript")

    def test_no_required_skill(self, client):
        assert_error(client.post("/api/jobs", json={**JOB, "required_skills": []}), 422, "required_skills")

    def test_empty_title(self, client):
        assert_error(client.post("/api/jobs", json={**JOB, "job_title": ""}), 422, "job_title")

    def test_short_description(self, client):
        assert_error(client.post("/api/jobs", json={**JOB, "job_description": "short"}), 422, "job_description")

    def test_negative_min_experience(self, client):
        assert_error(client.post("/api/jobs", json={**JOB, "min_experience": -2}), 422, "min_experience")


# ---------------------------------------------------------- matching
class TestMatching:
    def test_match_and_results(self, client):
        strong = make_candidate(client, full_name="Strong Fit")
        make_candidate(client, full_name="Weak Fit", skills=["Excel"], years_experience=1, level_id=1,
                       resume_summary="Retail store supervisor managing rosters and stock counts.")
        job = make_job(client)
        r = client.post(f"/api/jobs/{job['job_id']}/match")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["run"]["candidate_count"] == 2
        assert body["run"]["w_skills"] == 40
        top = body["results"][0]
        assert top["candidate_id"] == strong["candidate_id"] and top["rank"] == 1
        assert top["skills_score"] == 100.0 and top["experience_score"] == 100.0
        assert top["calculation"].startswith("Overall = (100×40")
        assert top["explanation"].startswith("Strong on skills (2 of 2 required, 1 of 1 preferred)")
        weak = body["results"][1]
        assert weak["missing"]["required"] == ["python", "sql"]
        # GET returns the same latest run
        again = client.get(f"/api/jobs/{job['job_id']}/results").json()
        assert [x["candidate_id"] for x in again["results"]] == [x["candidate_id"] for x in body["results"]]

    def test_alias_recorded(self, client):
        make_candidate(client, skills=["JS"])
        job = make_job(client, required_skills=["JavaScript"], preferred_skills=[])
        res = client.post(f"/api/jobs/{job['job_id']}/match").json()["results"][0]
        assert res["aliases"] == {"javascript": "JS"}
        assert any('"JS"' in n for n in res["insights"])

    def test_results_before_run(self, client):
        job = make_job(client)
        body = client.get(f"/api/jobs/{job['job_id']}/results").json()
        assert body["run"] is None and body["results"] == []

    def test_match_without_candidates(self, client):
        job = make_job(client)
        assert_error(client.post(f"/api/jobs/{job['job_id']}/match"), 400, contains="no candidates")

    def test_match_missing_job(self, client):
        assert_error(client.post("/api/jobs/999/match"), 404)

    def test_csv(self, client):
        make_candidate(client, full_name="=HYPERLINK(evil)")
        job = make_job(client)
        assert_error(client.get(f"/api/jobs/{job['job_id']}/results.csv"), 404)
        client.post(f"/api/jobs/{job['job_id']}/match")
        r = client.get(f"/api/jobs/{job['job_id']}/results.csv")
        assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
        assert "attachment" in r.headers["content-disposition"]
        lines = r.text.lstrip("﻿").splitlines()
        assert lines[0].startswith("Rank,Candidate,Overall")
        assert "'=HYPERLINK(evil)" in lines[1]  # formula injection neutralised

    def test_stats_after_run(self, client):
        make_candidate(client)
        job = make_job(client)
        client.post(f"/api/jobs/{job['job_id']}/match")
        s = client.get("/api/stats").json()
        assert s["candidates"] == 1 and s["jobs"] == 1
        assert s["last_run_job_title"] == "Data Engineer" and s["average_score"] is not None

    def test_deleting_candidate_cascades_results(self, client):
        c = make_candidate(client)
        job = make_job(client)
        client.post(f"/api/jobs/{job['job_id']}/match")
        client.delete(f"/api/candidates/{c['candidate_id']}")
        assert client.get(f"/api/jobs/{job['job_id']}/results").json()["results"] == []


# ------------------------------------------------------------- admin
class TestAdmin:
    def test_wrong_passcode(self, client):
        assert_error(client.post("/api/admin/backups", headers={"X-Admin-Passcode": "wrong"}), 401, "passcode", "incorrect")

    def test_missing_passcode(self, client):
        assert_error(client.get("/api/admin/backups"), 401, "passcode")

    @pytest.mark.parametrize("path", ["/api/admin/seed", "/api/admin/seed-large", "/api/admin/verify"])
    def test_wrong_passcode_everywhere(self, client, path):
        assert_error(client.post(path, headers={"X-Admin-Passcode": "nope"}), 401, "passcode")

    def test_restore_needs_passcode(self, client):
        assert_error(client.post("/api/admin/backups/x.db/restore"), 401)

    def test_verify(self, client, admin_headers):
        assert client.post("/api/admin/verify", headers=admin_headers).json() == {"ok": True}

    def test_backup_list_restore(self, client, admin_headers):
        make_candidate(client, full_name="Before Backup")
        b = client.post("/api/admin/backups", headers=admin_headers)
        assert b.status_code == 201
        fname = b.json()["file"]
        assert fname in [x["file"] for x in client.get("/api/admin/backups", headers=admin_headers).json()]
        make_candidate(client, full_name="After Backup")
        assert client.get("/api/candidates").json()["total"] == 2
        r = client.post(f"/api/admin/backups/{fname}/restore", headers=admin_headers)
        assert r.status_code == 200, r.text
        assert r.json()["safety_backup"].endswith("prerestore.db")
        names = [c["full_name"] for c in client.get("/api/candidates").json()["items"]]
        assert names == ["Before Backup"]

    def test_restore_rejects_traversal(self, client, admin_headers):
        r = client.post("/api/admin/backups/..%2F..%2Fdata%2Fhiretrack.db/restore", headers=admin_headers)
        assert r.status_code in (400, 404)

    def test_restore_unknown(self, client, admin_headers):
        assert_error(client.post("/api/admin/backups/hiretrack-20200101-000000-manual.db/restore", headers=admin_headers), 404)

    def test_restore_rejects_corrupt(self, client, admin_headers):
        from app.config import settings

        bad = settings.backup_dir / "hiretrack-20990101-000000-manual.db"
        bad.write_bytes(b"this is not a sqlite database at all" * 100)
        try:
            assert_error(client.post(f"/api/admin/backups/{bad.name}/restore", headers=admin_headers), 400, contains="integrity")
        finally:
            bad.unlink()

    def test_keeps_ten_backups(self, client, admin_headers):
        for _ in range(12):
            client.post("/api/admin/backups", headers=admin_headers)
        assert len(client.get("/api/admin/backups", headers=admin_headers).json()) == 10


# -------------------------------------------------------------- seeding
class TestSeed:
    def test_seed_demo(self, client, admin_headers):
        make_candidate(client, full_name="Will Be Wiped")
        r = client.post("/api/admin/seed", headers=admin_headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["candidates"] == 18 and body["jobs"] == 3
        assert body["safety_backup"].endswith("preseed.db")
        names = [c["full_name"] for c in client.get("/api/candidates", params={"page_size": 100}).json()["items"]]
        assert "Will Be Wiped" not in names and "Thandiwe Nkosi" in names
        titles = {j["job_title"] for j in client.get("/api/jobs").json()}
        assert titles == {"Cloud Data Engineer", "Full-Stack Developer", "Business Analyst"}

    def test_seeded_demo_story(self, client, admin_headers):
        client.post("/api/admin/seed", headers=admin_headers)
        job = next(j for j in client.get("/api/jobs").json() if j["job_title"] == "Cloud Data Engineer")
        res = client.post(f"/api/jobs/{job['job_id']}/match").json()["results"]
        assert len(res) == 18
        by_name = {r["full_name"]: r for r in res}
        assert res[0]["full_name"] == "Thandiwe Nkosi"
        assert by_name["Sipho Dlamini"]["aliases"] == {"python": "Py"}
        assert by_name["Lwazi Ngcobo"]["rank"] == 18 or by_name["Lwazi Ngcobo"]["overall_score"] < 40

    def test_seed_large(self, client, admin_headers):
        r = client.post("/api/admin/seed-large", headers=admin_headers)
        assert r.status_code == 200, r.text
        assert r.json()["candidates"] == 2018
        assert client.get("/api/candidates", params={"page_size": 1}).json()["total"] == 2018

    def test_demo_start_empty_db_seeds(self, client):
        r = client.post("/api/demo/start").json()
        assert r["seeded"] is True
        assert client.get(f"/api/jobs/{r['job_id']}").json()["job_title"] == "Cloud Data Engineer"

    def test_demo_start_keeps_existing_data(self, client):
        make_candidate(client, full_name="Keep Me")
        r = client.post("/api/demo/start").json()
        assert r["seeded"] is False
        names = [c["full_name"] for c in client.get("/api/candidates").json()["items"]]
        assert names == ["Keep Me"]
        assert client.get(f"/api/jobs/{r['job_id']}").json()["job_title"] == "Cloud Data Engineer"
