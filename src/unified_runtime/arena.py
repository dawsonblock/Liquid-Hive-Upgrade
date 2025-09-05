from __future__ import annotations

import os
import time
import uuid
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

# Prometheus metrics (optional)
try:
    from prometheus_client import Gauge  # type: ignore
except Exception:  # pragma: no cover
    Gauge = None  # type: ignore

# Local constant to avoid circular import
API_PREFIX = "/api"

router = APIRouter(prefix=f"{API_PREFIX}/arena", tags=["arena"])

# -------------------
# Data models
# -------------------


class SubmitRequest(BaseModel):
    task_id: str | None = None
    input: str = Field(..., description="Prompt/input for the task")
    reference: str | None = Field(None, description="Optional reference/ground truth")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubmitResponse(BaseModel):
    task_id: str
    stored: bool


class CompareRequest(BaseModel):
    model_config = {"protected_namespaces": ()}

    task_id: str
    model_a: str
    model_b: str
    output_a: str
    output_b: str
    winner: str | None = Field(None, description="'A' | 'B' | 'tie' (optional manual judgement)")
    judge: str | None = Field(None, description="Judge identifier (optional)")
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompareResponse(BaseModel):
    match_id: str
    decided_winner: str  # 'A' | 'B' | 'tie'


class LeaderboardEntry(BaseModel):
    model: str
    wins: int
    losses: int
    ties: int
    win_rate: float


class LeaderboardResponse(BaseModel):
    leaderboard: list[LeaderboardEntry]


# -------------------
# Metrics
# -------------------
if Gauge is not None:
    ARENA_WIN_RATE = Gauge("cb_arena_win_rate", "Arena model win rate", labelnames=("model",))
else:  # pragma: no cover
    ARENA_WIN_RATE = None  # type: ignore


# -------------------
# Storage Abstraction
# -------------------


class ArenaStore:
    def __init__(self):
        self.redis = None
        self.neo4j = None

        # In-memory fallback structures
        self._tasks: dict[str, dict[str, Any]] = {}
        self._matches: dict[str, dict[str, Any]] = {}
        self._score: dict[str, dict[str, int]] = {}

        # Try Redis
        try:
            import redis as _redis  # type: ignore

            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis = _redis.Redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
        except Exception:
            self.redis = None

        # Try Neo4j
        try:
            from neo4j import GraphDatabase  # type: ignore

            uri = os.getenv("NEO4J_URI")
            user = os.getenv("NEO4J_USER")
            pwd = os.getenv("NEO4J_PASSWORD")
            if uri and user and pwd:
                self.neo4j = GraphDatabase.driver(uri, auth=(user, pwd))
                # quick check session
                with self.neo4j.session() as s:
                    s.run("RETURN 1 AS ok").single()
        except Exception:
            self.neo4j = None

    # -------- tasks --------
    def create_task(self, task: dict[str, Any]) -> bool:
        tid = task["task_id"]
        now = time.time()
        task["created_at"] = now

        if self.redis:
            try:
                key = f"arena:task:{tid}"
                self.redis.hset(key, mapping={"task": TaskJSON.dumps(task)})
                self.redis.sadd("arena:tasks", tid)
            except Exception:
                pass
        if self.neo4j:
            try:
                q = "MERGE (t:Task {id: $id}) SET t.input=$input, t.reference=$reference, t.created_at=$ts"
                with self.neo4j.session() as s:
                    s.run(
                        q, id=tid, input=task.get("input"), reference=task.get("reference"), ts=now
                    )
            except Exception:
                pass
        # Always keep in-memory fallback
        self._tasks[tid] = task
        return True

    # -------- matches --------
    def record_match(self, match: dict[str, Any]) -> bool:
        mid = match["match_id"]
        now = time.time()
        match["created_at"] = now
        a = match["model_a"]
        b = match["model_b"]
        winner = match.get("winner", "tie")

        # Update scoreboard in-memory first
        self._score.setdefault(a, {"wins": 0, "losses": 0, "ties": 0})
        self._score.setdefault(b, {"wins": 0, "losses": 0, "ties": 0})
        if winner == "A":
            self._score[a]["wins"] += 1
            self._score[b]["losses"] += 1
        elif winner == "B":
            self._score[b]["wins"] += 1
            self._score[a]["losses"] += 1
        else:
            self._score[a]["ties"] += 1
            self._score[b]["ties"] += 1

        # Update win-rate gauge
        try:
            if ARENA_WIN_RATE is not None:
                for m in (a, b):
                    wins = self._score[m]["wins"]
                    losses = self._score[m]["losses"]
                    denom = max(1, wins + losses)
                    rate = wins / float(denom)
                    ARENA_WIN_RATE.labels(model=m).set(rate)
        except Exception:
            pass

        # Persist to Redis if available
        if self.redis:
            try:
                key = f"arena:match:{mid}"
                self.redis.hset(key, mapping={"match": TaskJSON.dumps(match)})
                self.redis.lpush("arena:matches", mid)
                # scoreboard per model
                for m in (a, b):
                    skey = f"arena:score:{m}"
                    sc = self._score[m]
                    self.redis.hset(skey, mapping=sc)
            except Exception:
                pass

        # Persist to Neo4j if available
        if self.neo4j:
            try:
                q = (
                    "MERGE (a:Model {name: $a}) MERGE (b:Model {name: $b}) "
                    "MERGE (t:Task {id: $tid}) "
                    "CREATE (m:Match {id: $mid, created_at: $ts, winner: $winner}) "
                    "MERGE (m)-[:ON_TASK]->(t) "
                    "MERGE (m)-[:WITH_A]->(a) "
                    "MERGE (m)-[:WITH_B]->(b) "
                    "FOREACH (w IN CASE WHEN $winner='A' THEN [1] ELSE [] END | MERGE (a)-[:WON_AGAINST]->(b)) "
                    "FOREACH (w IN CASE WHEN $winner='B' THEN [1] ELSE [] END | MERGE (b)-[:WON_AGAINST]->(a)) "
                )
                with self.neo4j.session() as s:
                    s.run(q, a=a, b=b, tid=match["task_id"], mid=mid, ts=now, winner=winner)
            except Exception:
                pass

        self._matches[mid] = match
        return True

    def get_leaderboard(self) -> list[LeaderboardEntry]:
        entries: list[LeaderboardEntry] = []
        # Prefer Redis scoreboard if available
        models: list[str] = list(self._score.keys())
        if self.redis:
            try:
                # Discover models from keys
                keys = self.redis.keys("arena:score:*")
                models = [k.split(":", 2)[-1] for k in keys] or models
            except Exception:
                pass

        for model in models:
            wins = self._score.get(model, {}).get("wins", 0)
            losses = self._score.get(model, {}).get("losses", 0)
            ties = self._score.get(model, {}).get("ties", 0)
            total = max(1, wins + losses)  # ignore ties in denominator
            win_rate = wins / float(total)
            entries.append(
                LeaderboardEntry(
                    model=model, wins=wins, losses=losses, ties=ties, win_rate=win_rate
                )
            )

        entries.sort(key=lambda e: e.win_rate, reverse=True)
        return entries


# Helper for compact JSON storage in Redis
class TaskJSON:
    import json as _json

    @staticmethod
    def dumps(obj: Any) -> str:
        try:
            return TaskJSON._json.dumps(obj, separators=(",", ":"))
        except Exception:
            return "{}"


store = ArenaStore()

# -------------------
# Endpoints
# -------------------


@router.post("/submit", response_model=SubmitResponse)
async def submit_task(req: SubmitRequest) -> SubmitResponse:
    tid = req.task_id or uuid.uuid4().hex
    payload = {
        "task_id": tid,
        "input": req.input,
        "reference": req.reference,
        "metadata": req.metadata,
    }
    store.create_task(payload)
    return SubmitResponse(task_id=tid, stored=True)


@router.post("/compare", response_model=CompareResponse)
async def compare_models(req: CompareRequest) -> CompareResponse:
    mid = uuid.uuid4().hex
    decided = req.winner
    if decided not in ("A", "B", "tie"):
        # trivial heuristic fallback: longer output wins; equal length is tie
        la = len(req.output_a or "")
        lb = len(req.output_b or "")
        if la > lb:
            decided = "A"
        elif lb > la:
            decided = "B"
        else:
            decided = "tie"

    match = {
        "match_id": mid,
        "task_id": req.task_id,
        "model_a": req.model_a,
        "model_b": req.model_b,
        "output_a": req.output_a,
        "output_b": req.output_b,
        "winner": decided,
        "judge": req.judge,
        "rationale": req.rationale,
        "metadata": req.metadata,
    }
    store.record_match(match)
    return CompareResponse(match_id=mid, decided_winner=decided)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def leaderboard() -> LeaderboardResponse:
    return LeaderboardResponse(leaderboard=store.get_leaderboard())
