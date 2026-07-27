from fastapi.testclient import TestClient
import pytest

from app.core.config import Settings, get_settings
from app.main import app
import app.main as main_module


class ReadyRepository:
    def storage_status(self):
        return {
            "status": "ok",
            "provider": "gcs",
            "root": "gs://private-production-bucket/",
            "rawdataExists": True,
        }


class BrokenRepository:
    def storage_status(self):
        raise PermissionError("private bucket denied")


class EmptyRepository:
    def storage_status(self):
        return {
            "provider": "file",
            "root": "/data",
            "rawdataExists": False,
        }


def _headers(client):
    settings = get_settings()
    response = client.post(
        "/api/auth/login",
        json={
            "username": settings.auth_username,
            "password": settings.auth_password,
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_public_probes_are_minimal_and_detailed_health_requires_auth(monkeypatch):
    monkeypatch.setattr(main_module, "get_repository", lambda: ReadyRepository())
    client = TestClient(app)

    assert client.get("/api/livez").json() == {"status": "ok"}
    readiness = client.get("/api/readyz")
    assert readiness.status_code == 200
    assert readiness.json() == {"status": "ok", "checks": {"storage": True}}
    assert readiness.headers["cache-control"] == "no-store"
    assert "gs://" not in readiness.text

    assert client.get("/api/health").status_code == 401
    detailed = client.get("/api/health", headers=_headers(client))
    assert detailed.status_code == 200
    assert detailed.json()["root"] == "gs://private-production-bucket/"
    assert detailed.headers["cache-control"] == "no-store"


def test_degraded_readiness_does_not_disclose_exception(monkeypatch):
    monkeypatch.setattr(main_module, "get_repository", lambda: BrokenRepository())
    response = TestClient(app).get("/api/readyz")
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"storage": False},
    }
    assert "PermissionError" not in response.text


def test_readiness_is_degraded_when_required_data_is_missing(monkeypatch):
    monkeypatch.setattr(main_module, "get_repository", lambda: EmptyRepository())
    response = TestClient(app).get("/api/readyz")
    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "checks": {"storage": False},
    }


def test_production_rejects_default_or_weak_credentials():
    base = {
        "environment": "production",
        "auth_username": "plc.operator",
        "auth_password": "strong-password-123",
        "auth_secret": "s" * 40,
    }
    Settings(_env_file=None, **base)

    with pytest.raises(ValueError, match="USERNAME"):
        Settings(_env_file=None, **{**base, "auth_username": "admin"})
    with pytest.raises(ValueError, match="PASSWORD"):
        Settings(_env_file=None, **{**base, "auth_password": "short"})
    with pytest.raises(ValueError, match="SECRET"):
        Settings(_env_file=None, **{**base, "auth_secret": "short"})
    with pytest.raises(ValueError, match="CORS"):
        Settings(_env_file=None, **{**base, "cors_origins": ["*"]})


@pytest.mark.parametrize(
    ("username_attr", "role", "permission"),
    [
        ("auth_username", "Operator", "plc:operate"),
        ("auth_engineer_username", "Engineer", "plc:reset"),
        ("auth_lead_username", "Lead", "access:manage"),
    ],
)
def test_login_issues_role_bound_identity(username_attr, role, permission):
    client = TestClient(app)
    settings = get_settings()
    response = client.post(
        "/api/auth/login",
        json={
            "username": getattr(settings, username_attr),
            "password": settings.auth_password,
        },
    )

    assert response.status_code == 200
    session = response.json()
    assert session["role"] == role
    assert permission in session["permissions"]

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {session['token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == getattr(settings, username_attr)
    assert me.json()["role"] == role


def test_operator_cannot_reset_plc_runtime():
    client = TestClient(app)
    headers = _headers(client)

    response = client.post("/api/plc/commands/reset", headers=headers)

    assert response.status_code == 403
    assert "Operator" in response.json()["detail"]
