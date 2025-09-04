from starlette.testclient import TestClient

from unified_runtime.server import app


def test_admin_guard_cache_clear_unauthorized(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    with TestClient(app) as client:
        r = client.post("/api/cache/clear", json={"pattern": "pytest-noauth"})
        assert r.status_code == 200
        assert r.json().get("error") == "Unauthorized"


def test_admin_guard_cache_clear_authorized(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    with TestClient(app) as client:
        r = client.post(
            "/api/cache/clear",
            json={"pattern": "pytest-auth"},
            headers={"x-admin-token": "secret123"},
        )
        assert r.status_code == 200
        assert "error" not in r.json()


def test_router_thresholds_guard_flow(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secretXYZ")
    with TestClient(app) as client:
        # Unauthorized
        r = client.post("/api/admin/router/set-thresholds", json={"conf_threshold": 0.8})
        assert r.status_code == 200
        assert r.json().get("error") == "Unauthorized"
        # Authorized
        r = client.post(
            "/api/admin/router/set-thresholds",
            json={"conf_threshold": 0.8},
            headers={"x-admin-token": "secretXYZ"},
        )
        assert r.status_code == 200
        data = r.json()
        assert "error" not in data
        assert isinstance(data, dict)
