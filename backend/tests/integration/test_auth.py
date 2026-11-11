"""Authentication, user administration and role-based access control."""
import pytest

from tests.helpers import CAND, JOB, PROJECT, STAFF, assert_error, make_candidate, make_job


class TestLogin:
    def test_login_returns_token_and_user(self, anon):
        r = anon.post("/api/auth/login", json={"email": "Recruiter@HireTrack.local ", "password": "Recruiter@123"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["token_type"] == "bearer" and body["expires_in"] == 8 * 3600
        assert body["user"]["role"] == "recruiter"
        assert "password_hash" not in body["user"]

    def test_wrong_password(self, anon):
        r = anon.post("/api/auth/login", json={"email": "admin@hiretrack.local", "password": "wrong-pass1"})
        assert_error(r, 401, "password", "incorrect email or password")

    def test_unknown_email_same_message(self, anon):
        r = anon.post("/api/auth/login", json={"email": "nobody@hiretrack.local", "password": "Admin@123"})
        assert_error(r, 401, "password", "incorrect email or password")

    def test_lockout_after_five_failures(self, anon):
        for _ in range(5):
            anon.post("/api/auth/login", json={"email": "admin@hiretrack.local", "password": "bad-guess1"})
        r = anon.post("/api/auth/login", json={"email": "admin@hiretrack.local", "password": "Admin@123"})
        assert_error(r, 429, "password", "too many failed")

    def test_me(self, client):
        me = client.get("/api/auth/me").json()
        assert me["email"] == "admin@hiretrack.local" and me["role"] == "admin"
        assert me["last_login_at"] is not None

    def test_missing_token(self, anon):
        assert_error(anon.get("/api/candidates"), 401, contains="sign in")

    def test_garbage_token(self, anon):
        assert_error(anon.get("/api/candidates", headers={"Authorization": "Bearer not.a.token"}), 401)

    def test_expired_token(self, anon):
        from app.security import create_token

        token = create_token(1, "admin", hours=-1)
        assert_error(anon.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}), 401, contains="expired")

    def test_health_is_public(self, anon):
        assert anon.get("/api/health").status_code == 200

    def test_deactivated_user_token_rejected(self, client, login):
        rec = login("recruiter")
        users = client.get("/api/users").json()
        r_user = next(u for u in users if u["role"] == "recruiter")
        client.put(f"/api/users/{r_user['user_id']}", json={**_user_body(r_user), "is_active": False})
        assert_error(client.get("/api/candidates", headers=rec), 401, contains="no longer active")
        r = client.post("/api/auth/login", json={"email": "recruiter@hiretrack.local", "password": "Recruiter@123"})
        assert_error(r, 401, contains="deactivated")


def _user_body(u, **over):
    return {"full_name": u["full_name"], "email": u["email"], "role": u["role"], "is_active": u["is_active"], **over}


class TestPasswords:
    def test_change_password(self, anon, login):
        h = login("recruiter")
        r = anon.post(
            "/api/auth/change-password", headers=h, json={"current_password": "Recruiter@123", "new_password": "Newpass99"}
        )
        assert r.status_code == 204
        ok = anon.post("/api/auth/login", json={"email": "recruiter@hiretrack.local", "password": "Newpass99"})
        assert ok.status_code == 200

    def test_change_password_wrong_current(self, anon, login):
        r = anon.post(
            "/api/auth/change-password",
            headers=login("recruiter"),
            json={"current_password": "nope", "new_password": "Newpass99"},
        )
        assert_error(r, 401, "current_password")

    @pytest.mark.parametrize("weak", ["short1", "allletters", "12345678"])
    def test_password_rule(self, anon, login, weak):
        r = anon.post(
            "/api/auth/change-password",
            headers=login("recruiter"),
            json={"current_password": "Recruiter@123", "new_password": weak},
        )
        assert_error(r, 422, "new_password", "at least 8 characters")

    def test_hash_never_plain_text(self, client):
        from sqlalchemy import select

        from app.database import SessionLocal
        from app.models import User

        with SessionLocal() as db:
            for h in db.scalars(select(User.password_hash)):
                assert h.startswith("$2b$") and "Admin@123" not in h


class TestUserAdmin:
    def test_list_users(self, client):
        roles = sorted(u["role"] for u in client.get("/api/users").json())
        assert roles == ["admin", "recruiter", "resource_manager"]

    def test_create_and_login(self, client, anon):
        body = {"full_name": "Lerato Moloi", "email": "Lerato@HireTrack.local", "role": "recruiter", "password": "Welcome12"}
        r = client.post("/api/users", json=body)
        assert r.status_code == 201 and r.json()["email"] == "lerato@hiretrack.local"
        assert anon.post("/api/auth/login", json={"email": "lerato@hiretrack.local", "password": "Welcome12"}).status_code == 200

    def test_duplicate_email(self, client):
        r = client.post(
            "/api/users", json={"full_name": "X Y", "email": "admin@hiretrack.local", "role": "admin", "password": "Welcome12"}
        )
        assert_error(r, 409, "email")

    def test_create_needs_password(self, client):
        r = client.post("/api/users", json={"full_name": "X Y", "email": "x@y.co", "role": "admin"})
        assert_error(r, 422, "password")

    def test_bad_role(self, client):
        r = client.post("/api/users", json={"full_name": "X Y", "email": "x@y.co", "role": "boss", "password": "Welcome12"})
        assert_error(r, 422, "role")

    def test_bad_email(self, client):
        r = client.post("/api/users", json={"full_name": "X Y", "email": "nope", "role": "admin", "password": "Welcome12"})
        assert_error(r, 422, "email")

    def test_cannot_remove_last_admin(self, client):
        admin = next(u for u in client.get("/api/users").json() if u["role"] == "admin")
        r = client.put(f"/api/users/{admin['user_id']}", json=_user_body(admin, role="recruiter"))
        assert_error(r, 422, "role", "at least one active administrator")

    def test_cannot_deactivate_self(self, client):
        client.post(
            "/api/users", json={"full_name": "Second Admin", "email": "a2@h.local", "role": "admin", "password": "Welcome12"}
        )
        me = client.get("/api/auth/me").json()
        r = client.put(f"/api/users/{me['user_id']}", json=_user_body(me, is_active=False))
        assert_error(r, 422, "is_active", "your own account")

    def test_update_user_and_reset_password(self, client, anon):
        u = next(x for x in client.get("/api/users").json() if x["role"] == "resource_manager")
        r = client.put(f"/api/users/{u['user_id']}", json=_user_body(u, full_name="Pieter B", password="Reset1234"))
        assert r.status_code == 200 and r.json()["full_name"] == "Pieter B"
        assert anon.post("/api/auth/login", json={"email": u["email"], "password": "Reset1234"}).status_code == 200

    def test_update_missing_user(self, client):
        body = {"full_name": "X Y", "email": "x@y.co", "role": "admin"}
        assert_error(client.put("/api/users/9999", json=body), 404)


# Role access matrix: (method, path, body, {role: allowed?})
H, R, M = "admin", "recruiter", "resource_manager"


def _matrix():
    return [
        ("GET", "/api/candidates", None, {H: 1, R: 1, M: 1}),
        ("POST", "/api/candidates", CAND, {H: 1, R: 1, M: 0}),
        ("GET", "/api/jobs", None, {H: 1, R: 1, M: 1}),
        ("POST", "/api/jobs", JOB, {H: 1, R: 1, M: 0}),
        ("GET", "/api/applications", None, {H: 1, R: 1, M: 1}),
        ("GET", "/api/staff", None, {H: 1, R: 1, M: 1}),
        ("POST", "/api/staff", STAFF, {H: 1, R: 0, M: 1}),
        ("POST", "/api/projects", PROJECT, {H: 1, R: 0, M: 1}),
        ("GET", "/api/dashboard", None, {H: 1, R: 1, M: 1}),
        ("GET", "/api/users", None, {H: 1, R: 0, M: 0}),
        ("GET", "/api/admin/backups", None, {H: 1, R: 0, M: 0}),
        ("POST", "/api/demo/start", None, {H: 1, R: 1, M: 0}),
    ]


@pytest.mark.parametrize("method,path,body,allowed", _matrix(), ids=lambda v: v if isinstance(v, str) else None)
@pytest.mark.parametrize("role", [H, R, M])
def test_role_access_matrix(anon, login, method, path, body, allowed, role):
    r = anon.request(method, path, json=body, headers=login(role))
    if allowed[role]:
        assert r.status_code in (200, 201), f"{role} should be allowed: {r.status_code} {r.text}"
    else:
        assert_error(r, 403, contains="role does not have access")


def test_resource_manager_cannot_run_match(client, login):
    make_candidate(client)
    job = make_job(client)
    r = client.post(f"/api/jobs/{job['job_id']}/match", headers=login("resource_manager"))
    assert_error(r, 403)


def test_recruiter_cannot_restore_backups(client, login):
    r = client.post("/api/admin/backups/x.db/restore", headers={**login("recruiter"), "X-Confirm-Password": "Recruiter@123"})
    assert_error(r, 403)
