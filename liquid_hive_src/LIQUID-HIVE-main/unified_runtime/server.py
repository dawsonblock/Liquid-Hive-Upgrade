"""
Fusion server with Autonomy, Trust, Estimator, and Model Routing
===============================================================
"""
from __future__ import annotations

import asyncio
from typing import Optional, List, Any, Dict
import sys
import os
import uuid
import json
import json as _json
import urllib.parse as _u
import urllib.request as _req
import httpx

from fastapi import FastAPI, UploadFile, File, Request
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from capsule_brain.security.input_sanitizer import sanitize_input

try:
    from capsule_brain.observability.metrics import MetricsMiddleware, router as metrics_router
    from capsule_brain.planner.plan import plan_once
    from capsule_brain.core.capsule_engine import CapsuleEngine
    from capsule_brain.core.intent_modeler import IntentModeler
except Exception:
    MetricsMiddleware = None  # type: ignore
    metrics_router = None  # type: ignore
    plan_once = None  # type: ignore
    CapsuleEngine = None  # type: ignore
    IntentModeler = None  # type: ignore

try:
    from hivemind.config import Settings
except Exception:
    Settings = None  # type: ignore

try:
    from .model_router import DSRouter, RouterConfig
    from .providers import GenRequest
except Exception:
    DSRouter = None  # type: ignore
    RouterConfig = None  # type: ignore
    GenRequest = None  # type: ignore

try:
    from hivemind.roles_text import TextRoles
    from hivemind.judge import Judge
    from hivemind.policies import decide_policy
    from hivemind.strategy_selector import StrategySelector
    from hivemind.rag.retriever import Retriever
    from hivemind.rag.citations import format_context
    from hivemind.clients.vllm_client import VLLMClient
    from hivemind.clients.vl_client import VLClient
    from hivemind.roles_vl import VisionRoles
    from hivemind.resource_estimator import ResourceEstimator
    from hivemind.adapter_deployment_manager import AdapterDeploymentManager
    from hivemind.tool_auditor import ToolAuditor
    from hivemind.confidence_modeler import ConfidenceModeler, TrustPolicy
except Exception:
    TextRoles = None      # type: ignore
    Judge = None          # type: ignore
    decide_policy = None  # type: ignore
    StrategySelector = None  # type: ignore
    Retriever = None      # type: ignore
    format_context = None  # type: ignore
    VLLMClient = None     # type: ignore
    VLClient = None      # type: ignore
    VisionRoles = None   # type: ignore
    ResourceEstimator = None  # type: ignore
    AdapterDeploymentManager = None  # type: ignore
    ToolAuditor = None  # type: ignore
    IntentModeler = None  # type: ignore
    ConfidenceModeler = None  # type: ignore
    TrustPolicy = None  # type: ignore

# Ensure trust types import isn't blocked by other hivemind imports
try:
    if ConfidenceModeler is None or TrustPolicy is None:
        from hivemind.confidence_modeler import ConfidenceModeler as _CM, TrustPolicy as _TP  # type: ignore
        ConfidenceModeler = _CM  # type: ignore
        TrustPolicy = _TP  # type: ignore
except Exception:
    pass

try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore

# Curiosity Engine (Genesis Spark)
try:
    from hivemind.autonomy.curiosity import CuriosityEngine  # type: ignore
except Exception:
    CuriosityEngine = None  # type: ignore

API_PREFIX = "/api"

app = FastAPI(title="Fusion HiveMind Capsule", version="0.1.9")

if MetricsMiddleware is not None:
    app.add_middleware(MetricsMiddleware)
if metrics_router is not None:
    app.include_router(metrics_router)

engine: Optional[CapsuleEngine] = None
text_roles: Optional[TextRoles] = None
text_roles_small: Optional[TextRoles] = None
text_roles_large: Optional[TextRoles] = None
judge: Optional[Judge] = None
retriever: Optional[Retriever] = None
settings: Optional[Settings] = None
strategy_selector: Optional[StrategySelector] = None
vl_roles: Optional[VisionRoles] = None
resource_estimator: Optional[ResourceEstimator] = None
adapter_manager: Optional[AdapterDeploymentManager] = None
tool_auditor: Optional[ToolAuditor] = None
intent_modeler: Optional[IntentModeler] = None
confidence_modeler: Optional[ConfidenceModeler] = None
ds_router: Optional[DSRouter] = None

try:
    from hivemind.autonomy.orchestrator import AutonomyOrchestrator
except Exception:
    AutonomyOrchestrator = None  # type: ignore

autonomy_orchestrator: Optional[AutonomyOrchestrator] = None
_autonomy_lock: Any = None
_autonomy_lock_key = "liquid_hive:autonomy_leader"
_autonomy_id = uuid.uuid4().hex

websockets: list[WebSocket] = []


@app.on_event("startup")
async def startup() -> None:
    """Initialize global components on startup."""
    global settings, retriever, engine, text_roles, judge, strategy_selector, vl_roles
    global resource_estimator, adapter_manager, tool_auditor, intent_modeler, confidence_modeler, ds_router
    
    # Initialize settings
    if Settings is not None:
        settings = Settings()
    
    # Initialize DS-Router
    if DSRouter is not None and RouterConfig is not None:
        router_config = RouterConfig.from_env()
        ds_router = DSRouter(router_config)
        # Warm-up provider health checks in background to avoid first-call latency
        try:
            asyncio.get_event_loop().create_task(ds_router.get_provider_status())
        except Exception:
            pass
        
    # Initialize retriever
    if Retriever is not None and settings is not None:
        retriever = Retriever(settings.rag_index, settings.embed_model)
    
    # Initialize engine
    if CapsuleEngine is not None:
        engine = CapsuleEngine()
    
    # Initialize text roles
    if TextRoles is not None and settings is not None:
        text_roles = TextRoles(settings)
    
    # Initialize trust modeler with default policy if available
    if ConfidenceModeler is not None and TrustPolicy is not None:
        try:
            enabled = bool(getattr(settings, "TRUSTED_AUTONOMY_ENABLED", False)) if settings else False
            threshold = float(getattr(settings, "TRUST_THRESHOLD", 0.999)) if settings else 0.999
            min_samples = int(getattr(settings, "TRUST_MIN_SAMPLES", 200)) if settings else 200
            allow = getattr(settings, "TRUST_ALLOWLIST", "") if settings else ""
            allow_t = tuple([s.strip() for s in allow.split(",") if s.strip()])
            confidence_policy = TrustPolicy(
                enabled=enabled,
                threshold=threshold,
                min_samples=min_samples,
                allowlist=allow_t,
            )
            confidence_modeler = ConfidenceModeler(confidence_policy)
        except Exception:
            confidence_modeler = None


def _env_write(key: str, value: str) -> None:
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        lines: List[str] = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        found = False
        new_lines: List[str] = []
        for line in lines:
            if line.strip().startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"{key}={value}")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")
    except Exception:
        pass


def _prom_q(base_url: Optional[str], promql: str) -> Optional[dict]:
    if not base_url:
        return None
    try:
        params = _u.urlencode({"query": promql})
        with _req.urlopen(f"{base_url}/api/v1/query?{params}") as r:
            data = _json.loads(r.read().decode())
            if data.get("status") == "success":
                return data.get("data")
    except Exception:
        return None
    return None


def _scalar(data: Optional[dict]) -> Optional[float]:
    try:
        if not data:
            return None
        res = data.get("result", [])
        if not res:
            return None
        v = res[0].get("value", [None, None])[1]
        return float(v) if v is not None else None
    except Exception:
        return None


async def _broadcast_autonomy_event(event: dict) -> None:
    dead = []
    for ws in list(websockets):
        try:
            await ws.send_json({"type": "autonomy_events", "payload": [event]})
        except Exception:
            dead.append(ws)
    for ws in dead:
        try:
            websockets.remove(ws)
        except Exception:
            pass


async def _start_autonomy_with_leader_election() -> None:
    global autonomy_orchestrator, _autonomy_lock
    if AutonomyOrchestrator is None or engine is None or settings is None:
        return
    if redis is None or not getattr(settings, "redis_url", None):
        return
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore
        lock = r.lock(_autonomy_lock_key, timeout=120)
        got = lock.acquire(blocking=False)
        if not got:
            return
        _autonomy_lock = lock
        autonomy_orchestrator = AutonomyOrchestrator(engine, adapter_manager, settings)  # type: ignore
        await autonomy_orchestrator.start()

        async def renew_lock() -> None:
            backoff = 1
            while True:
                try:
                    lock.extend(120)
                    backoff = 1  # reset on success
                except Exception:
                    # Attempt graceful stop and try to re-acquire with backoff
                    try:
                        if autonomy_orchestrator is not None:
                            await autonomy_orchestrator.stop()
                    except Exception:
                        pass
                    try:
                        reacquired = lock.acquire(blocking=False)
                        if not reacquired:
                            return  # give up leadership
                        backoff = 1
                    except Exception:
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * 2, 60)
                        continue
                await asyncio.sleep(60)
        asyncio.get_event_loop().create_task(renew_lock())
    except Exception:
        try:
            if _autonomy_lock is not None:
                _autonomy_lock.release()
        except Exception:
            pass
        _autonomy_lock = None
        autonomy_orchestrator = None
        return


@app.get(f"{API_PREFIX}/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": engine is not None}


@app.get(f"{API_PREFIX}/vllm/models")
async def vllm_models() -> Dict[str, Any]:
    """Helper endpoint to query vLLM service for loaded models."""
    try:
        if settings is None or settings.vllm_endpoint is None:
            return {"error": "vLLM endpoint not configured"}
        url = settings.vllm_endpoint.rstrip("/") + "/v1/models"
        with _req.urlopen(url, timeout=5) as r:
            data = _json.loads(r.read().decode())
            return data
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/secrets/health")
async def secrets_health() -> dict[str, Any]:
    """Get secrets manager health status."""
    if settings is None:
        return {"error": "Settings not initialized"}
    try:
        return settings.get_secrets_health()
    except Exception as exc:
        return {"error": str(exc)}


async def _get_approvals() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    if engine is None:
        return items
    try:
        for idx, item in enumerate(engine.memory):  # type: ignore
            if item.get("role") == "approval":
                items.append({"id": idx, "content": item.get("content", "")})
    except Exception:
        pass
    return items


@app.get(f"{API_PREFIX}/approvals")
async def list_approvals() -> List[Dict[str, Any]]:
    return await _get_approvals()


@app.post(f"{API_PREFIX}/approvals/{{idx}}/approve")
async def approve_proposal(idx: int) -> Dict[str, str]:
    if engine is None:
        return {"error": "Engine not ready"}
    try:
        item = engine.memory[idx]  # type: ignore
        if item.get("role") != "approval":
            raise IndexError
        engine.add_memory("approval_feedback", f"APPROVED: {item.get('content', '')}")  # type: ignore
        del engine.memory[idx]  # type: ignore
        return {"status": "approved"}
    except Exception:
        return {"error": "Invalid approval index"}


@app.post(f"{API_PREFIX}/approvals/{{idx}}/deny")
async def deny_proposal(idx: int) -> Dict[str, str]:
    if engine is None:
        return {"error": "Engine not ready"}
    try:
        item = engine.memory[idx]  # type: ignore
        if item.get("role") != "approval":
            raise IndexError
        engine.add_memory("approval_feedback", f"DENIED: {item.get('content', '')}")  # type: ignore
        del engine.memory[idx]  # type: ignore
        return {"status": "denied"}
    except Exception:
        return {"error": "Invalid approval index"}


@app.get(f"{API_PREFIX}/adapters")
async def list_adapters() -> List[Dict[str, Any]]:
    table: List[Dict[str, Any]] = []
    if adapter_manager is None:
        return table
    try:
        for role, entry in adapter_manager.state.items():  # type: ignore
            table.append({
                "role": role,
                "champion": entry.get("active") or "",
                "challenger": entry.get("challenger") or "",
            })
    except Exception:
        pass
    return table


@app.get(f"{API_PREFIX}/adapters/state")
async def adapters_state() -> Dict[str, Any]:
    if adapter_manager is None:
        return {"state": {}}
    try:
        return {"state": adapter_manager.state}  # type: ignore
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/adapters/promote/{{role}}")
async def promote_adapter(role: str) -> Dict[str, Any]:
    if adapter_manager is None:
        return {"error": "Adapter manager unavailable"}
    try:
        new_active = adapter_manager.promote_challenger(role)  # type: ignore
        return {"role": role, "new_active": new_active}
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/config/governor")
async def get_governor() -> Dict[str, Any]:
    if settings is None:
        return {"ENABLE_ORACLE_REFINEMENT": None, "FORCE_GPT4O_ARBITER": None}
    try:
        return {
            "ENABLE_ORACLE_REFINEMENT": bool(getattr(settings, "ENABLE_ORACLE_REFINEMENT", False)),
            "FORCE_GPT4O_ARBITER": bool(getattr(settings, "FORCE_GPT4O_ARBITER", False)),
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/config/governor")
async def update_governor(cfg: Dict[str, Any]) -> Dict[str, str]:
    global settings
    if settings is None:
        return {"error": "Settings unavailable"}
    try:
        enable_val = cfg.get("ENABLE_ORACLE_REFINEMENT")
        force_val = cfg.get("FORCE_GPT4O_ARBITER")
        if enable_val is None and "enabled" in cfg:
            enable_val = cfg["enabled"]
        if force_val is None and "force_gpt4o" in cfg:
            force_val = cfg["force_gpt4o"]
        if enable_val is not None:
            settings.ENABLE_ORACLE_REFINEMENT = bool(enable_val)  # type: ignore
            _env_write("ENABLE_ORACLE_REFINEMENT", "true" if bool(enable_val) else "false")
        if force_val is not None:
            settings.FORCE_GPT4O_ARBITER = bool(force_val)  # type: ignore
            _env_write("FORCE_GPT4O_ARBITER", "true" if bool(force_val) else "false")
        return {"status": "updated"}
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/trust/policy")
async def get_trust_policy() -> Dict[str, Any]:
    if settings is None:
        return {"enabled": False}
    allow = getattr(settings, "TRUST_ALLOWLIST", None) or ""
    return {
        "enabled": bool(getattr(settings, "TRUSTED_AUTONOMY_ENABLED", False)),
        "threshold": float(getattr(settings, "TRUST_THRESHOLD", 0.999)),
        "min_samples": int(getattr(settings, "TRUST_MIN_SAMPLES", 200)),
        "allowlist": [s.strip() for s in allow.split(",") if s.strip()],
    }


@app.post(f"{API_PREFIX}/trust/policy")
async def set_trust_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    global settings, confidence_modeler
    if settings is None or ConfidenceModeler is None or TrustPolicy is None:
        return {"error": "Trust module unavailable"}
    try:
        if "enabled" in cfg:
            settings.TRUSTED_AUTONOMY_ENABLED = bool(cfg["enabled"])  # type: ignore
            _env_write("TRUSTED_AUTONOMY_ENABLED", "true" if settings.TRUSTED_AUTONOMY_ENABLED else "false")
        if "threshold" in cfg:
            settings.TRUST_THRESHOLD = float(cfg["threshold"])  # type: ignore
            _env_write("TRUST_THRESHOLD", str(settings.TRUST_THRESHOLD))
        if "min_samples" in cfg:
            settings.TRUST_MIN_SAMPLES = int(cfg["min_samples"])  # type: ignore
            _env_write("TRUST_MIN_SAMPLES", str(settings.TRUST_MIN_SAMPLES))
        if "allowlist" in cfg:
            allow = ",".join(cfg.get("allowlist") or [])
            settings.TRUST_ALLOWLIST = allow  # type: ignore
            _env_write("TRUST_ALLOWLIST", allow)
        allow_t = tuple([s.strip() for s in (settings.TRUST_ALLOWLIST or "").split(",") if s.strip()])  # type: ignore
        policy = TrustPolicy(
            enabled=bool(settings.TRUSTED_AUTONOMY_ENABLED),  # type: ignore
            threshold=float(settings.TRUST_THRESHOLD),  # type: ignore
            min_samples=int(settings.TRUST_MIN_SAMPLES),  # type: ignore
            allowlist=allow_t,
        )
        if confidence_modeler is None:
            confidence_modeler = ConfidenceModeler(policy)
        else:
            confidence_modeler.update_policy(policy)
        return {"status": "updated", "policy": await get_trust_policy()}
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/trust/score")
async def trust_score(proposal: Dict[str, Any]) -> Dict[str, Any]:
    if confidence_modeler is None:
        return {"enabled": False, "score": None, "bypass": False, "reason": "modeler_unavailable"}
    try:
        events = []
        try:
            events = list(engine.memory) if engine is not None else []  # type: ignore
        except Exception:
            events = []
        confidence_modeler.update_from_events(events)
        decision = confidence_modeler.decide(proposal)
        return {"enabled": True, **decision}
    except Exception as exc:
        return {"enabled": True, "error": str(exc)}


@app.post(f"{API_PREFIX}/internal/delegate_task")
async def delegate_task(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Task Delegation API: Allows one LIQUID-HIVE instance to offload sub-tasks to others.
    Internal-only endpoint for swarm coordination.
    """
    try:
        from hivemind.swarm_protocol import get_swarm_coordinator
        
        swarm = await get_swarm_coordinator()
        if not swarm:
            return {"error": "Swarm protocol not available"}
        
        task_type = task_data.get("task_type")
        payload = task_data.get("payload", {})
        priority = task_data.get("priority", 1)
        timeout = task_data.get("timeout", 300)
        
        if not task_type:
            return {"error": "task_type required"}
        
        # Delegate task to swarm
        result = await swarm.delegate_task(task_type, payload, priority, timeout)
        
        if result:
            return {"status": "completed", "result": result}
        else:
            return {"status": "failed", "error": "Task delegation failed"}
            
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/swarm/status")
async def swarm_status() -> Dict[str, Any]:
    """Get swarm coordination status and node information."""
    try:
        from hivemind.swarm_protocol import get_swarm_coordinator
        
        swarm = await get_swarm_coordinator()
        if not swarm:
            return {"swarm_enabled": False, "reason": "coordinator_unavailable"}
        
        # Get swarm state
        if swarm.redis_client:
            nodes_data = await swarm.redis_client.hgetall("swarm:nodes")
            nodes = []
            for node_id, node_json in nodes_data.items():
                try:
                    node_info = json.loads(node_json)
                    nodes.append(node_info)
                except Exception:
                    continue
            
            return {
                "swarm_enabled": True,
                "node_id": swarm.node_id,
                "active_nodes": len(nodes),
                "nodes": nodes,
                "active_tasks": len(swarm.active_tasks),
                "capabilities": swarm.capabilities
            }
        else:
            return {"swarm_enabled": False, "reason": "redis_unavailable"}
            
    except Exception as exc:
        return {"swarm_enabled": False, "error": str(exc)}


@app.get(f"{API_PREFIX}/providers")
async def get_providers_status() -> Dict[str, Any]:
    """Get status of all DS-Router providers."""
    if ds_router is None:
        return {"error": "DS-Router not available"}
    
    try:
        return {
            "providers": await ds_router.get_provider_status(),
            "router_active": True,
            "timestamp": asyncio.get_event_loop().time()
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/admin/budget/reset")
async def reset_budget() -> Dict[str, str]:
    """Reset daily budget counters (Admin only)."""
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        return {"error": "Admin token not configured"}
    
    # In production, verify admin token from request headers
    # For now, just reset the budget tracker
    if ds_router is not None and hasattr(ds_router, '_budget_tracker'):
        ds_router._budget_tracker.tokens_used = 0
        ds_router._budget_tracker.usd_spent = 0.0
        return {"status": "budget_reset"}
    else:
        return {"error": "Router or budget tracker not available"}


@app.post(f"{API_PREFIX}/admin/router/set-thresholds")
async def set_router_thresholds(thresholds: Dict[str, float]) -> Dict[str, Any]:
    """Set router confidence and support thresholds (Admin only)."""
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        return {"error": "Admin token not configured"}
    
    if ds_router is None:
        return {"error": "DS-Router not available"}
    
    try:
        # Update thresholds
        if "conf_threshold" in thresholds:
            ds_router.config.conf_threshold = float(thresholds["conf_threshold"])
        if "support_threshold" in thresholds:
            ds_router.config.support_threshold = float(thresholds["support_threshold"])
        if "max_cot_tokens" in thresholds:
            ds_router.config.max_cot_tokens = int(thresholds["max_cot_tokens"])
            
        return {
            "status": "updated",
            "current_thresholds": {
                "conf_threshold": ds_router.config.conf_threshold,
                "support_threshold": ds_router.config.support_threshold,
                "max_cot_tokens": ds_router.config.max_cot_tokens
            }
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/autonomy/autopromote/preview")
async def autopromote_preview() -> dict[str, Any]:
    if settings is None or adapter_manager is None:
        return {"candidates": []}
    base = getattr(settings, "PROMETHEUS_BASE_URL", None)
    window = "5m"
    min_samples = int(getattr(settings, "AUTOPROMOTE_MIN_SAMPLES", 300))
    out = []
    # Build a representative prompt from recent user inputs to estimate costs
    representative_prompt = ""
    try:
        if engine is not None:
            user_msgs = [m.get("content", "") for m in list(engine.memory)[-200:] if m.get("role") == "user"]  # type: ignore
            snippet = "\n".join(user_msgs[-5:])
            representative_prompt = snippet[:2000]
    except Exception:
        representative_prompt = "Evaluate adapter performance under typical conversational load."

    for role, entry in getattr(adapter_manager, "state", {}).items():  # type: ignore
        active = (entry or {}).get("active")
        challenger = (entry or {}).get("challenger")
        if not (active and challenger and active != challenger):
            continue
        r_active = _scalar(_prom_q(base, f'sum(rate(cb_requests_total{{adapter_version="{active}"}}[{window}]))')) or 0.0
        r_chall = _scalar(_prom_q(base, f'sum(rate(cb_requests_total{{adapter_version="{challenger}"}}[{window}]))')) or 0.0
        if (r_active * 300) < min_samples or (r_chall * 300) < min_samples:
            continue
        p95_a = _scalar(_prom_q(base, f'histogram_quantile(0.95, sum(rate(cb_request_latency_seconds_bucket{{adapter_version="{active}"}}[{window}])) by (le))')) or 9e9
        p95_c = _scalar(_prom_q(base, f'histogram_quantile(0.95, sum(rate(cb_request_latency_seconds_bucket{{adapter_version="{challenger}"}}[{window}])) by (le))')) or 9e9
        try:
            cost_small = resource_estimator.estimate_cost("implementer", "small", representative_prompt) if resource_estimator else {"predicted_cost_small": 1.0}
            cost_large = resource_estimator.estimate_cost("implementer", "large", representative_prompt) if resource_estimator else {"predicted_cost_large": 1.0}
        except Exception:
            cost_small = {"predicted_cost_small": 1.0}
            cost_large = {"predicted_cost_large": 1.0}
        better_latency = p95_c <= (p95_a * 0.9)
        better_cost = (cost_large.get("predicted_cost_large", 1.0)) <= (cost_small.get("predicted_cost_small", 1.0))
        if better_latency or better_cost:
            out.append({
                "role": role,
                "active": active,
                "challenger": challenger,
                "p95_a": p95_a,
                "p95_c": p95_c,
                "predicted_cost_small": cost_small.get("predicted_cost_small"),
                "predicted_cost_large": cost_large.get("predicted_cost_large"),
                "reason": "latency" if better_latency else "cost",
            })
    return {"candidates": out}


@app.get(f"{API_PREFIX}/state")
async def state() -> dict[str, Any]:
    if engine is None:
        return {"error": "Engine not ready"}
    return engine.get_state_summary()


@app.websocket(f"{API_PREFIX}/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    websockets.append(websocket)  # type: ignore
    try:
        while True:
            await asyncio.sleep(10) # Or listen to engine.bus for immediate events
            try:
                if engine is not None:
                    summary = engine.get_state_summary()
                    await websocket.send_json({"type": "state_update", "payload": summary})
                    
                    approvals = await _get_approvals()
                    await websocket.send_json({"type": "approvals_update", "payload": approvals})

                    # --- Add custom events here ---
                    # Example: Get recent self_extension memories
                    recent_autonomy_events = [m for m in list(engine.memory)[-50:] if m.get("role") in ["self_extension", "approval_feedback"]]
                    if recent_autonomy_events:
                        await websocket.send_json({"type": "autonomy_events_recent", "payload": recent_autonomy_events})
                    
                    # RAG system status
                    if retriever is not None:
                        rag_status = {
                            "is_ready": retriever.is_ready,
                            "doc_count": len(retriever.doc_store) if retriever.doc_store else 0,
                            "embedding_model": retriever.embed_model_id
                        }
                        await websocket.send_json({"type": "rag_status", "payload": rag_status})
                    
                    # Oracle/Arbiter system status
                    oracle_status = {
                        "deepseek_available": bool(os.getenv("DEEPSEEK_API_KEY")),
                        "openai_available": bool(os.getenv("OPENAI_API_KEY")),
                        "refinement_enabled": getattr(settings, "ENABLE_ORACLE_REFINEMENT", False) if settings else False
                    }
                    await websocket.send_json({"type": "oracle_status", "payload": oracle_status})
                    
                    # You could also listen to engine.bus.get_nowait() or a dedicated queue for events
                    # and immediately broadcast them.
                    # -----------------------------

            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        try:
            websockets.remove(websocket)  # type: ignore
        except Exception:
            pass


@app.post(f"{API_PREFIX}/train")
async def train() -> dict[str, str]:
    try:
        from hivemind.training.dataset_build import build_text_sft_and_prefs, build_vl_sft
        build_text_sft_and_prefs()
        try:
            build_vl_sft()
        except Exception:
            pass
        import subprocess, pathlib, uuid as _uuid
        base = pathlib.Path(settings.adapters_dir if settings else "/app/adapters")  # type: ignore
        out_dir = base / "text" / f"adapter_{_uuid.uuid4().hex}"
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            sys.executable,
            "-m",
            "hivemind.training.sft_text",
            "--out",
            str(out_dir),
        ], check=True)
        if settings is not None:
            settings.text_adapter_path = str(out_dir)
        return {"status": "success", "adapter_path": str(out_dir)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post(f"{API_PREFIX}/chat")
async def chat(q: str, request: Request) -> dict[str, Any]:
    """Unified chat endpoint relying exclusively on DS-Router.
    The router encapsulates safety (Pre/Post guards), routing, confidence, and fallbacks.
    """
    q = sanitize_input(q)
    # Proceed even if engine is not yet initialized; router-only mode
    if engine is not None:
        engine.add_memory("user", q)

    # Optional planning hints (non-blocking)
    planner_hints = None
    reasoning_steps = None
    if plan_once is not None:
        try:
            plan_result = await plan_once(q)
            planner_hints = plan_result.get("tool_hints")
            reasoning_steps = plan_result.get("reasoning_steps")
        except Exception:
            planner_hints = None
            reasoning_steps = None

    # RAG enrichment
    context_txt = ""
    prompt = q
    if retriever is not None:
        try:
            docs = await retriever.search(q, k=5)
            context_txt = retriever.format_context(docs)
            prompt = (
                f"[CONTEXT]\n{context_txt}\n\n"
                f"[QUESTION]\n{q}\n\n"
                "Cite using [#]. If not in context, say 'Not in context'."
            )
        except Exception:
            prompt = q

    # DS-Router only
    if ds_router is None or GenRequest is None:
        answer = "Router unavailable"
        if engine is not None:
            engine.add_memory("assistant", answer)
        return {"answer": answer}

    provider_used = None
    confidence = None
    escalated = False

    try:
        gen_request = GenRequest(
            prompt=prompt,
            system_prompt="You are a helpful AI assistant. Provide accurate and helpful responses.",
            max_tokens=getattr(settings, 'max_new_tokens', 512) if settings else 512,
            temperature=0.7
        )
        # Hard cap to avoid p95 &gt; 10s due to cold-starts
        chat_timeout = float(os.getenv("CHAT_TIMEOUT_SECS", "9.5"))
        gen_response = await asyncio.wait_for(ds_router.generate(gen_request), timeout=chat_timeout)
        answer = gen_response.content
        provider_used = gen_response.provider
        confidence = gen_response.confidence
        escalated = gen_response.metadata.get("escalated", False)

        # Annotate request scope for metrics
        request.scope["provider_used"] = provider_used
        request.scope["router_confidence"] = confidence
        request.scope["escalated"] = escalated

    except asyncio.TimeoutError:
        answer = (
            "I apologize, but I'm currently experiencing high load and couldn't respond in time. "
            "Please try again in a moment."
        )
        provider_used = "timeout_fallback"
        confidence = 0.0
        escalated = False
    except Exception:
        # Trust DS-Router's internal fallback chain; if it still fails, return a resilient static message
        answer = (
            "I apologize, but I'm currently unable to process your request due to temporary "
            "system limitations. Please try again shortly."
        )
        provider_used = "system_fallback"
        confidence = 0.0
        escalated = False

    engine.add_memory("assistant", answer)

    try:
        if hasattr(text_roles, "c"):
            client = text_roles.c  # type: ignore[attr-defined]
            adapter_version = getattr(client, "current_adapter_version", None)
            if adapter_version:
                request.scope["adapter_version"] = adapter_version
    except Exception:
        pass

    result: dict[str, Any] = {"answer": answer}
    if provider_used:
        result["provider"] = provider_used
    if confidence is not None:
        result["confidence"] = confidence
    if escalated:
        result["escalated"] = escalated
    if context_txt:
        result["context"] = context_txt
    if planner_hints:
        result["planner_hints"] = planner_hints  # type: ignore
    if reasoning_steps:
        result["reasoning_steps"] = reasoning_steps  # type: ignore
    return result


@app.post(f"{API_PREFIX}/vision")
async def vision(question: str, file: UploadFile = File(...), grounding_required: bool = False, request: Request = None):
    if engine is None:
        return {"answer": "Engine not ready"}
    if vl_roles is None or judge is None:
        return {"answer": "Vision pipeline unavailable"}
    image_data = await file.read()
    engine.add_memory("user", question)
    answer: str = "Vision processing unavailable"
    critique: Optional[str] = None
    grounding: Optional[dict[str, Any]] = None
    try:
        candidates = await vl_roles.vl_committee(question, image_data, k=2)  # type: ignore[attr-defined]
        rankings = await judge.rank_vision(question, image_data, candidates)  # type: ignore[attr-defined]
        wid = int(rankings.get("winner_id", 0))
        answer = candidates[wid] if 0 <= wid < len(candidates) else candidates[0]
        critique = rankings.get("critique")
        if grounding_required:
            grounding = vl_roles.grounding_validator(question, image_data, answer)  # type: ignore[attr-defined]
    except Exception as exc:
        answer = f"Error processing vision request: {exc}"
    engine.add_memory("assistant", answer)
    if request is not None:
        try:
            request.scope["adapter_version"] = "vl"
        except Exception:
            pass
    resp: dict[str, Any] = {"answer": answer}
    if critique:
        resp["critique"] = critique
    if grounding:
        resp["grounding"] = grounding
    return resp

# Mount GUI SPA
try:
    import pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[1]
    gui_dist_path = repo_root / "gui" / "dist"
    gui_build_path = repo_root / "gui" / "build"
    static_root: Optional[pathlib.Path] = None
    if gui_dist_path.exists():
        static_root = gui_dist_path
    elif gui_build_path.exists():
        static_root = gui_build_path
    if static_root is not None:
        app.mount("/", StaticFiles(directory=str(static_root), html=True), name="gui")
except Exception:
    pass