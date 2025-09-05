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
        # Cache clear should work when properly authorized
        response_data = r.json()
        # Should either clear successfully or report cache not available
        if "error" in response_data:
            assert response_data["error"] == "Semantic cache not available"
        else:
            assert "cleared_entries" in response_data


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
