from starlette.testclient import TestClient

from unified_runtime.server import app


def test_health_and_core_endpoints():
    with TestClient(app) as client:
        r = client.get("/api/healthz")
        assert r.status_code == 200

        r = client.get("/api/cache/health")
        assert r.status_code == 200

        r = client.get("/api/cache/analytics")
        assert r.status_code == 200

        r = client.get("/api/cache/status")
        assert r.status_code == 200

        r = client.get("/api/swarm/status")
        assert r.status_code == 200


def test_cache_clear_without_admin_token_when_not_required(monkeypatch):
    # Ensure ADMIN_TOKEN not set for this test
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    with TestClient(app) as client:
        r = client.post("/api/cache/clear", json={"pattern": "pytest"})
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)
        # Should either clear successfully or report cache not available
        if "error" in data:
            assert data["error"] == "Semantic cache not available"
        else:
            assert "cleared_entries" in data


def test_autopromote_preview():
    with TestClient(app) as client:
        r = client.get("/api/autonomy/autopromote/preview")
        assert r.status_code == 200
        assert isinstance(r.json(), dict)
