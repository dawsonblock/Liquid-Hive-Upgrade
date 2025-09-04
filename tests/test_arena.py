from starlette.testclient import TestClient

from unified_runtime.server import app


def test_arena_submit_compare_leaderboard(monkeypatch):
    # Force fallback storage by clearing envs
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_USER", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)
    monkeypatch.setenv("ENABLE_ARENA", "true")

    with TestClient(app) as client:
        # Submit task
        r = client.post("/api/arena/submit", json={"input": "Translate 'hello' to French"})
        assert r.status_code == 200
        tid = r.json()["task_id"]

        # Compare two models, A wins (longer output)
        r = client.post(
            "/api/arena/compare",
            json={
                "task_id": tid,
                "model_a": "deepseek_v3",
                "model_b": "qwen_7b",
                "output_a": "Bonjour! Ceci est une réponse plus longue.",
                "output_b": "Bonjour!",
            },
        )
        assert r.status_code == 200
        decided = r.json()["decided_winner"]
        assert decided in ("A", "B", "tie")

        # Leaderboard
        r = client.get("/api/arena/leaderboard")
        assert r.status_code == 200
        data = r.json()
        assert "leaderboard" in data
        assert any(entry["model"] == "deepseek_v3" for entry in data["leaderboard"])


def test_arena_manual_winner(monkeypatch):
    monkeypatch.setenv("ENABLE_ARENA", "true")

    with TestClient(app) as client:
        # Create task
        r = client.post("/api/arena/submit", json={"input": "Summarize this paragraph"})
        tid = r.json()["task_id"]

        # Force tie
        r = client.post(
            "/api/arena/compare",
            json={
                "task_id": tid,
                "model_a": "model_X",
                "model_b": "model_Y",
                "output_a": "same",
                "output_b": "same",
                "winner": "tie",
            },
        )
        assert r.status_code == 200
        assert r.json()["decided_winner"] == "tie"

        # A manual A-win
        r = client.post(
            "/api/arena/compare",
            json={
                "task_id": tid,
                "model_a": "model_X",
                "model_b": "model_Y",
                "output_a": "a",
                "output_b": "b",
                "winner": "A",
            },
        )
        assert r.status_code == 200
        assert r.json()["decided_winner"] == "A"

        # Leaderboard reflects counts
        r = client.get("/api/arena/leaderboard")
        entries = {e["model"]: e for e in r.json()["leaderboard"]}
        assert "model_X" in entries and "model_Y" in entries
