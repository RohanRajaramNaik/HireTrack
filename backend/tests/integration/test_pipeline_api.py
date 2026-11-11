"""Applicant pipeline API: applications, stage changes, audit trail, hiring."""
from tests.helpers import assert_error, make_application, make_candidate, make_job, move


def _setup(client):
    c = make_candidate(client)
    j = make_job(client)
    return c, j, make_application(client, c["candidate_id"], j["job_id"], note="Referred by staff member")


class TestApplications:
    def test_create_starts_at_applied_with_history(self, client):
        _, j, a = _setup(client)
        assert a["stage"] == "applied" and a["job_title"] == j["job_title"]
        assert a["allowed_moves"] == ["screened", "rejected"]
        assert len(a["events"]) == 1
        ev = a["events"][0]
        assert ev["from_stage"] is None and ev["to_stage"] == "applied"
        assert ev["changed_by_name"] == "System Administrator" and ev["note"] == "Referred by staff member"

    def test_duplicate_application(self, client):
        c, j, _ = _setup(client)
        r = client.post("/api/applications", json={"candidate_id": c["candidate_id"], "job_id": j["job_id"]})
        assert_error(r, 409, "candidate_id", "already in the pipeline")

    def test_unknown_candidate_or_job(self, client):
        j = make_job(client)
        assert_error(client.post("/api/applications", json={"candidate_id": 999, "job_id": j["job_id"]}), 404, "candidate_id")
        c = make_candidate(client)
        assert_error(client.post("/api/applications", json={"candidate_id": c["candidate_id"], "job_id": 999}), 404, "job_id")

    def test_closed_job_rejects_new_applications(self, client):
        c = make_candidate(client)
        j = make_job(client, status="closed")
        r = client.post("/api/applications", json={"candidate_id": c["candidate_id"], "job_id": j["job_id"]})
        assert_error(r, 422, "job_id", "closed")

    def test_list_filters(self, client):
        c1 = make_candidate(client)
        c2 = make_candidate(client, full_name="Bongani Mthembu", email="b@example.com")
        j = make_job(client)
        a1 = make_application(client, c1["candidate_id"], j["job_id"])
        make_application(client, c2["candidate_id"], j["job_id"])
        move(client, a1["application_id"], "screened")
        assert len(client.get("/api/applications", params={"job_id": j["job_id"]}).json()) == 2
        screened = client.get("/api/applications", params={"stage": "screened"}).json()
        assert [a["candidate_name"] for a in screened] == ["Ayanda Zulu"]
        found = client.get("/api/applications", params={"search": "bongani"}).json()
        assert [a["candidate_name"] for a in found] == ["Bongani Mthembu"]
        assert client.get("/api/applications/counts", params={"job_id": j["job_id"]}).json() == {"applied": 1, "screened": 1}

    def test_bad_stage_filter(self, client):
        assert_error(client.get("/api/applications", params={"stage": "lost"}), 422, "stage")

    def test_get_missing(self, client):
        assert_error(client.get("/api/applications/999"), 404)


class TestStageChanges:
    def test_full_journey_to_hired_creates_staff(self, client):
        c, j, a = _setup(client)
        aid = a["application_id"]
        for stage in ("screened", "interview", "offer"):
            r = move(client, aid, stage, note=f"Moved to {stage}")
            assert r.status_code == 200, r.text
        r = move(client, aid, "hired", note="Offer accepted")
        body = r.json()
        assert body["stage"] == "hired" and body["allowed_moves"] == []
        assert [e["to_stage"] for e in body["events"]] == ["applied", "screened", "interview", "offer", "hired"]
        assert body["events"][-1]["note"] == "Offer accepted"
        staff = client.get("/api/staff").json()
        assert len(staff) == 1
        s = staff[0]
        assert s["full_name"] == c["full_name"] and s["source"] == "hired"
        assert s["role_title"] == j["job_title"] and s["candidate_id"] == c["candidate_id"]
        assert s["utilisation"] == 0 and s["band"] == "bench"

    def test_cannot_skip_a_stage(self, client):
        _, _, a = _setup(client)
        assert_error(move(client, a["application_id"], "offer"), 422, "stage", "next stage is Screened")

    def test_unknown_stage_value(self, client):
        _, _, a = _setup(client)
        assert_error(move(client, a["application_id"], "promoted"), 422, "stage")

    def test_reject_and_reopen(self, client):
        _, _, a = _setup(client)
        aid = a["application_id"]
        move(client, aid, "screened")
        r = move(client, aid, "rejected", note="Missing required skills")
        assert r.json()["stage"] == "rejected"
        assert r.json()["allowed_moves"] == ["screened"]
        assert_error(move(client, aid, "interview"), 422, "stage")
        r = move(client, aid, "screened", note="Reopened after review")
        assert r.status_code == 200 and r.json()["stage"] == "screened"
        assert len(r.json()["events"]) == 4

    def test_hired_is_final(self, client):
        _, _, a = _setup(client)
        aid = a["application_id"]
        for s in ("screened", "interview", "offer", "hired"):
            move(client, aid, s)
        assert_error(move(client, aid, "rejected"), 422, "stage", "final")

    def test_cannot_delete_hired(self, client):
        _, _, a = _setup(client)
        aid = a["application_id"]
        for s in ("screened", "interview", "offer", "hired"):
            move(client, aid, s)
        assert_error(client.delete(f"/api/applications/{aid}"), 422)

    def test_delete_application(self, client):
        _, _, a = _setup(client)
        assert client.delete(f"/api/applications/{a['application_id']}").status_code == 204
        assert client.get("/api/applications").json() == []

    def test_hiring_needs_open_job(self, client):
        c, j, a = _setup(client)
        aid = a["application_id"]
        for s in ("screened", "interview", "offer"):
            move(client, aid, s)
        client.put(f"/api/jobs/{j['job_id']}", json={**_job_body(j), "status": "closed"})
        assert_error(move(client, aid, "hired"), 422, "stage", "closed")

    def test_change_is_attributed_to_the_user(self, client, login):
        _, _, a = _setup(client)
        r = client.post(
            f"/api/applications/{a['application_id']}/stage", json={"stage": "screened"}, headers=login("recruiter")
        )
        assert r.json()["events"][-1]["changed_by_name"] == "Nomvula Khumalo"

    def test_resource_manager_can_view_but_not_move(self, client, login):
        _, _, a = _setup(client)
        h = login("resource_manager")
        assert client.get(f"/api/applications/{a['application_id']}", headers=h).status_code == 200
        r = client.post(f"/api/applications/{a['application_id']}/stage", json={"stage": "screened"}, headers=h)
        assert_error(r, 403)

    def test_deleting_candidate_removes_applications(self, client):
        c, _, _ = _setup(client)
        client.delete(f"/api/candidates/{c['candidate_id']}")
        assert client.get("/api/applications").json() == []


def _job_body(j):
    keys = ["job_title", "location", "status", "min_experience", "min_level_id", "job_description",
            "required_skills", "preferred_skills", "w_skills", "w_experience", "w_education", "w_semantic"]
    return {k: j[k] for k in keys}


class TestFromResults:
    def test_bulk_add_shortlist_keeps_match_score(self, client):
        c1 = make_candidate(client)
        c2 = make_candidate(client, full_name="Bongani Mthembu", email="b@example.com")
        j = make_job(client)
        results = client.post(f"/api/jobs/{j['job_id']}/match").json()["results"]
        r = client.post("/api/applications/bulk", json={"job_id": j["job_id"], "candidate_ids": [c1["candidate_id"], c2["candidate_id"]]})
        assert r.json() == {"added": 2, "skipped": 0}
        apps = {a["candidate_id"]: a for a in client.get("/api/applications").json()}
        expected = {row["candidate_id"]: row["overall_score"] for row in results}
        assert apps[c1["candidate_id"]]["match_score"] == expected[c1["candidate_id"]]
        # Second time: both skipped, not duplicated.
        r = client.post("/api/applications/bulk", json={"job_id": j["job_id"], "candidate_ids": [c1["candidate_id"]]})
        assert r.json() == {"added": 0, "skipped": 1}
        # Results now show the pipeline stage for each candidate.
        rows = client.get(f"/api/jobs/{j['job_id']}/results").json()["results"]
        assert {row["pipeline_stage"] for row in rows} == {"applied"}

    def test_bulk_unknown_candidate(self, client):
        j = make_job(client)
        assert_error(client.post("/api/applications/bulk", json={"job_id": j["job_id"], "candidate_ids": [42]}), 404)

    def test_bulk_closed_job(self, client):
        c = make_candidate(client)
        j = make_job(client, status="closed")
        r = client.post("/api/applications/bulk", json={"job_id": j["job_id"], "candidate_ids": [c["candidate_id"]]})
        assert_error(r, 422, "job_id")

    def test_bulk_needs_ids(self, client):
        j = make_job(client)
        assert_error(client.post("/api/applications/bulk", json={"job_id": j["job_id"], "candidate_ids": []}), 422)

    def test_bulk_missing_job(self, client):
        assert_error(client.post("/api/applications/bulk", json={"job_id": 404, "candidate_ids": [1]}), 404, "job_id")
