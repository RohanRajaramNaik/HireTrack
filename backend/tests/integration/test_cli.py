"""Command-line tools used in the installation guide (password reset)."""
from app import reset_password


def test_reset_password_and_reactivate(client, anon):
    users = client.get("/api/users").json()
    rec = next(u for u in users if u["role"] == "recruiter")
    client.put(f"/api/users/{rec['user_id']}", json={**{k: rec[k] for k in ("full_name", "email", "role")}, "is_active": False})
    assert reset_password.main(["Recruiter@HireTrack.local", "Changed123"]) == 0
    r = anon.post("/api/auth/login", json={"email": "recruiter@hiretrack.local", "password": "Changed123"})
    assert r.status_code == 200


def test_reset_password_rejects_weak_password(anon, capsys):
    assert reset_password.main(["admin@hiretrack.local", "weak"]) == 1
    assert "at least 8 characters" in capsys.readouterr().out


def test_reset_password_unknown_user(anon, capsys):
    assert reset_password.main(["nobody@hiretrack.local", "Changed123"]) == 1
    assert "No user" in capsys.readouterr().out


def test_reset_password_usage(capsys):
    assert reset_password.main([]) == 2
    assert "reset_password" in capsys.readouterr().out
