"""Resource allocation API: staff, projects, allocations and utilisation."""
from tests.helpers import PROJECT, STAFF, assert_error, created, iso


def staff(client, **over):
    return created(client.post("/api/staff", json={**STAFF, **over}))


def project(client, **over):
    return created(client.post("/api/projects", json={**PROJECT, **over}))


def allocate(client, staff_id, project_id, pct, start=-10, end=30, role="Developer"):
    return client.post(
        "/api/allocations",
        json={
            "staff_id": staff_id,
            "project_id": project_id,
            "allocation_percent": pct,
            "start_date": iso(start),
            "end_date": iso(end),
            "role_on_project": role,
        },
    )


class TestStaff:
    def test_crud(self, client):
        s = staff(client)
        assert s["source"] == "existing" and s["band"] == "bench" and s["utilisation"] == 0
        r = client.put(f"/api/staff/{s['staff_id']}", json={**STAFF, "role_title": "Senior Software Developer"})
        assert r.json()["role_title"] == "Senior Software Developer"
        assert client.get(f"/api/staff/{s['staff_id']}").status_code == 200
        assert client.delete(f"/api/staff/{s['staff_id']}").status_code == 204
        assert_error(client.get(f"/api/staff/{s['staff_id']}"), 404)

    def test_validation(self, client):
        assert_error(client.post("/api/staff", json={**STAFF, "full_name": "J"}), 422, "full_name")
        assert_error(client.post("/api/staff", json={**STAFF, "email": "bad"}), 422, "email")
        assert_error(client.post("/api/staff", json={**STAFF, "role_title": ""}), 422, "role_title")

    def test_search_and_band_filter(self, client):
        a = staff(client)
        staff(client, full_name="Liezl Steyn", role_title="QA Engineer")
        p = project(client)
        allocate(client, a["staff_id"], p["project_id"], 100)
        assert [s["full_name"] for s in client.get("/api/staff", params={"search": "qa eng"}).json()] == ["Liezl Steyn"]
        assert [s["full_name"] for s in client.get("/api/staff", params={"band": "full"}).json()] == ["Johan Venter"]
        assert [s["full_name"] for s in client.get("/api/staff", params={"band": "bench"}).json()] == ["Liezl Steyn"]


class TestProjects:
    def test_crud_and_detail(self, client):
        p = project(client)
        assert p["team_size"] == 0 and p["allocations"] == []
        r = client.put(f"/api/projects/{p['project_id']}", json={**PROJECT, "status": "on_hold"})
        assert r.json()["status"] == "on_hold"
        assert [x["name"] for x in client.get("/api/projects", params={"status": "on_hold"}).json()] == ["Claims Portal"]
        assert client.delete(f"/api/projects/{p['project_id']}").status_code == 204

    def test_end_before_start(self, client):
        r = client.post("/api/projects", json={**PROJECT, "start_date": iso(10), "end_date": iso(1)})
        assert_error(r, 422, "end_date", "before the start date")

    def test_duplicate_name(self, client):
        project(client)
        assert_error(client.post("/api/projects", json={**PROJECT, "name": "claims portal"}), 409, "name")

    def test_bad_status(self, client):
        assert_error(client.post("/api/projects", json={**PROJECT, "status": "done"}), 422, "status")

    def test_cannot_shrink_dates_past_allocations(self, client):
        s, p = staff(client), project(client)
        allocate(client, s["staff_id"], p["project_id"], 50, start=-10, end=60)
        r = client.put(f"/api/projects/{p['project_id']}", json={**PROJECT, "end_date": iso(30)})
        assert_error(r, 422, "start_date", "fall outside")

    def test_missing(self, client):
        assert_error(client.get("/api/projects/77"), 404)


class TestAllocations:
    def test_allocate_and_utilisation(self, client):
        s, p = staff(client), project(client)
        r = allocate(client, s["staff_id"], p["project_id"], 60)
        assert r.status_code == 201, r.text
        a = r.json()
        assert a["is_current"] and a["staff_name"] == "Johan Venter" and a["project_name"] == "Claims Portal"
        got = client.get(f"/api/staff/{s['staff_id']}").json()
        assert got["utilisation"] == 60 and got["band"] == "healthy" and got["current_projects"] == ["Claims Portal"]
        detail = client.get(f"/api/projects/{p['project_id']}").json()
        assert detail["team_size"] == 1 and detail["allocated_percent"] == 60
        assert client.get("/api/utilisation").json() == {
            "active_staff": 1, "average_utilisation": 60.0, "bands": {"bench": 0, "light": 0, "healthy": 1, "full": 0}
        }

    def test_over_allocation_rejected(self, client):
        s = staff(client)
        p1, p2 = project(client), project(client, name="Fleet Tracking")
        assert allocate(client, s["staff_id"], p1["project_id"], 70).status_code == 201
        r = allocate(client, s["staff_id"], p2["project_id"], 40)
        assert_error(r, 422, "allocation_percent", "most you can add for these dates is 30%")
        assert allocate(client, s["staff_id"], p2["project_id"], 30).status_code == 201

    def test_non_overlapping_dates_allowed(self, client):
        s, p = staff(client), project(client)
        assert allocate(client, s["staff_id"], p["project_id"], 100, start=-20, end=0).status_code == 201
        assert allocate(client, s["staff_id"], p["project_id"], 100, start=1, end=40).status_code == 201

    def test_dates_must_be_inside_project(self, client):
        s, p = staff(client), project(client)
        assert_error(allocate(client, s["staff_id"], p["project_id"], 50, start=-60, end=10), 422, "start_date", "within the project")

    def test_completed_project(self, client):
        s = staff(client)
        p = project(client, status="completed")
        assert_error(allocate(client, s["staff_id"], p["project_id"], 50), 422, "project_id", "completed")

    def test_inactive_staff(self, client):
        s = staff(client, is_active=False)
        p = project(client)
        assert_error(allocate(client, s["staff_id"], p["project_id"], 50), 422, "staff_id", "inactive")

    def test_percent_range(self, client):
        s, p = staff(client), project(client)
        assert_error(allocate(client, s["staff_id"], p["project_id"], 0), 422, "allocation_percent")
        assert_error(allocate(client, s["staff_id"], p["project_id"], 120), 422, "allocation_percent")

    def test_on_hold_project_does_not_count(self, client):
        s = staff(client)
        held = project(client, name="Paused", status="on_hold")
        active = project(client, name="Live")
        assert allocate(client, s["staff_id"], held["project_id"], 80).status_code == 201
        assert allocate(client, s["staff_id"], active["project_id"], 100).status_code == 201
        assert client.get(f"/api/staff/{s['staff_id']}").json()["utilisation"] == 100

    def test_update_and_delete(self, client):
        s, p = staff(client), project(client)
        a = allocate(client, s["staff_id"], p["project_id"], 50).json()
        body = {
            "staff_id": s["staff_id"], "project_id": p["project_id"], "allocation_percent": 100,
            "start_date": iso(-10), "end_date": iso(30), "role_on_project": "Lead",
        }
        r = client.put(f"/api/allocations/{a['allocation_id']}", json=body)
        assert r.status_code == 200 and r.json()["allocation_percent"] == 100  # its own old 50% is ignored
        assert len(client.get("/api/allocations", params={"staff_id": s["staff_id"]}).json()) == 1
        assert client.delete(f"/api/allocations/{a['allocation_id']}").status_code == 204
        assert client.get("/api/allocations", params={"project_id": p["project_id"]}).json() == []
        assert_error(client.delete(f"/api/allocations/{a['allocation_id']}"), 404)

    def test_deleting_project_frees_staff(self, client):
        s, p = staff(client), project(client)
        allocate(client, s["staff_id"], p["project_id"], 100)
        client.delete(f"/api/projects/{p['project_id']}")
        assert client.get(f"/api/staff/{s['staff_id']}").json()["utilisation"] == 0

    def test_recruiter_cannot_allocate(self, client, login):
        s, p = staff(client), project(client)
        r = client.post(
            "/api/allocations",
            headers=login("recruiter"),
            json={"staff_id": s["staff_id"], "project_id": p["project_id"], "allocation_percent": 10,
                  "start_date": iso(0), "end_date": iso(5)},
        )
        assert_error(r, 403)
