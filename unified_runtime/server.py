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
import json as _json
import urllib.parse as _u
import urllib.request as _req

from fastapi import FastAPI, UploadFile, File, Request
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

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
    from hivemind.roles_text import TextRoles
    from hivemind.judge import Judge
    from hivemind.policies import decide_policy
    from hivemind.strategy_selector import StrategySelector
    from hivemind.rag.retriever import Retriever
    from hivemind.rag.citations import format_context
    from hivemind.config import Settings
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
    Settings = None       # type: ignore
    VLLMClient = None     # type: ignore
    VLClient = None      # type: ignore
    VisionRoles = None   # type: ignore
    ResourceEstimator = None  # type: ignore
    AdapterDeploymentManager = None  # type: ignore
    ToolAuditor = None  # type: ignore
    IntentModeler = None  # type: ignore
    ConfidenceModeler = None  # type: ignore
    TrustPolicy = None  # type: ignore

try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore

app = FastAPI(title="Fusion HiveMind Capsule", version="0.1.5")

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

try:
    from hivemind.autonomy.orchestrator import AutonomyOrchestrator
except Exception:
    AutonomyOrchestrator = None  # type: ignore

autonomy_orchestrator: Optional[AutonomyOrchestrator] = None
_autonomy_lock: Any = None
_autonomy_lock_key = "liquid_hive:autonomy_leader"
_autonomy_id = uuid.uuid4().hex

websockets: list[WebSocket] = []


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
            while True:
                try:
                    lock.extend(120)
                except Exception:
                    try:
                        if autonomy_orchestrator is not None:
                            await autonomy_orchestrator.stop()
                    except Exception:
                        pass
                    return
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


@app.on_event("startup")
async def startup() -> None:
    global engine, text_roles, judge, retriever, settings, strategy_selector
    global vl_roles, resource_estimator, adapter_manager, tool_auditor, intent_modeler, confidence_modeler
    global text_roles_small, text_roles_large
    engine = CapsuleEngine()
    await engine.start_background_tasks()

    try:
        if Settings is None:
            raise RuntimeError("HiveMind settings unavailable")
        settings_ = Settings()  # type: ignore
        resource_estimator_ = ResourceEstimator() if ResourceEstimator else None
        adapter_manager_ = AdapterDeploymentManager() if AdapterDeploymentManager else None
        tool_auditor_ = ToolAuditor(settings_.runs_dir) if ToolAuditor and settings_ else None
        intent_modeler_ = IntentModeler(engine) if IntentModeler and engine else None
        # Default client
        vclient = VLLMClient(
            settings_.vllm_endpoint,
            settings_.vllm_api_key,
            max_new_tokens=settings_.max_new_tokens,
            adapter=settings_.text_adapter_path,
            adapter_manager=adapter_manager_,
            role="implementer",
        )
        text_roles_ = TextRoles(vclient) if TextRoles else None
        # Optional small/large
        text_roles_small_ = None
        text_roles_large_ = None
        try:
            if getattr(settings_, "vllm_endpoint_small", None):
                v_small = VLLMClient(settings_.vllm_endpoint_small, settings_.vllm_api_key, max_new_tokens=settings_.max_new_tokens, adapter=settings_.text_adapter_path, adapter_manager=adapter_manager_, role="implementer")
                text_roles_small_ = TextRoles(v_small)
            if getattr(settings_, "vllm_endpoint_large", None):
                v_large = VLLMClient(settings_.vllm_endpoint_large, settings_.vllm_api_key, max_new_tokens=settings_.max_new_tokens, adapter=settings_.text_adapter_path, adapter_manager=adapter_manager_, role="implementer")
                text_roles_large_ = TextRoles(v_large)
        except Exception:
            text_roles_small_ = text_roles_small_ or None
            text_roles_large_ = text_roles_large_ or None
        judge_ = Judge(vclient) if Judge else None
        selector_ = StrategySelector(vclient) if StrategySelector else None
        retriever_ = Retriever(settings_.rag_index, settings_.embed_model) if Retriever else None
        if VLClient and VisionRoles:
            try:
                vl_client = VLClient(settings_.vl_model_id)
                vl_roles_ = VisionRoles(vl_client)
            except Exception:
                vl_roles_ = None
        else:
            vl_roles_ = None
        # Assign
        settings = settings_
        text_roles = text_roles_
        text_roles_small = text_roles_small_
        text_roles_large = text_roles_large_
        judge = judge_
        retriever = retriever_
        strategy_selector = selector_
        vl_roles = vl_roles_
        resource_estimator = resource_estimator_
        adapter_manager = adapter_manager_
        tool_auditor = tool_auditor_
        intent_modeler = intent_modeler_
    except Exception:
        text_roles = None
        text_roles_small = None
        text_roles_large = None
        judge = None
        retriever = None
        settings = None
        vl_roles = None
        resource_estimator = None
        adapter_manager = None
        tool_auditor = None
        intent_modeler = None
        confidence_modeler = None

    # tool auditor loop
    if tool_auditor is not None and engine is not None:
        async def auditor_loop() -> None:
            while True:
                try:
                    underperforming = tool_auditor.flag_underperforming()
                    for tool_name in underperforming:
                        engine.add_memory("self_extension", f"Analyze tool '{tool_name}' and propose a more resilient version.")
                except Exception:
                    pass
                await asyncio.sleep(60)
        try:
            asyncio.get_event_loop().create_task(auditor_loop())
        except Exception:
            pass

    # trust modeler loop
    if confidence_modeler is not None and engine is not None:
        async def trust_update_loop() -> None:
            while True:
                try:
                    events = []
                    try:
                        events = list(engine.memory)  # type: ignore
                    except Exception:
                        events = []
                    confidence_modeler.update_from_events(events)
                except Exception:
                    pass
                await asyncio.sleep(120)
        try:
            asyncio.get_event_loop().create_task(trust_update_loop())
        except Exception:
            pass

    await _start_autonomy_with_leader_election()


@app.on_event("shutdown")
async def shutdown() -> None:
    global _autonomy_lock
    if autonomy_orchestrator is not None:
        try:
            await autonomy_orchestrator.stop()
        except Exception:
            pass
    if _autonomy_lock is not None:
        try:
            _autonomy_lock.release()
        except Exception:
            pass
        _autonomy_lock = None
    if engine is not None:
        await engine.shutdown()


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": engine is not None}


@app.get("/secrets/health")
async def secrets_health() -> dict[str, any]:
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


@app.get("/approvals")
async def list_approvals() -> List[Dict[str, Any]]:
    return await _get_approvals()


@app.post("/approvals/{idx}/approve")
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


@app.post("/approvals/{idx}/deny")
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


@app.get("/adapters")
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


@app.get("/adapters/state")
async def adapters_state() -> Dict[str, Any]:
    if adapter_manager is None:
        return {"state": {}}
    try:
        return {"state": adapter_manager.state}  # type: ignore
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/adapters/promote/{role}")
async def promote_adapter(role: str) -> Dict[str, Any]:
    if adapter_manager is None:
        return {"error": "Adapter manager unavailable"}
    try:
        new_active = adapter_manager.promote_challenger(role)  # type: ignore
        return {"role": role, "new_active": new_active}
    except Exception as exc:
        return {"error": str(exc)}


@app.get("/config/governor")
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


@app.post("/config/governor")
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


@app.get("/trust/policy")
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


@app.post("/trust/policy")
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


@app.post("/trust/score")
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


@app.get("/autonomy/autopromote/preview")
async def autopromote_preview() -> dict[str, any]:
    if settings is None or adapter_manager is None:
        return {"candidates": []}
    base = getattr(settings, "PROMETHEUS_BASE_URL", None)
    window = "5m"
    min_samples = int(getattr(settings, "AUTOPROMOTE_MIN_SAMPLES", 300))
    out = []
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
            cost_a = resource_estimator.estimate_cost("implementer", "large", active) if resource_estimator else 1.0
            cost_c = resource_estimator.estimate_cost("implementer", "large", challenger) if resource_estimator else 1.0
        except Exception:
            cost_a = cost_c = 1.0
        better_latency = p95_c <= (p95_a * 0.9)
        better_cost = cost_c <= (cost_a * 0.9)
        if better_latency or better_cost:
            out.append({"role": role, "active": active, "challenger": challenger, "p95_a": p95_a, "p95_c": p95_c, "cost_a": cost_a, "cost_c": cost_c, "reason": "latency" if better_latency else "cost"})
    return {"candidates": out}


@app.get("/state")
async def state() -> dict[str, Any]:
    if engine is None:
        return {"error": "Engine not ready"}
    return engine.get_state_summary()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    websockets.append(websocket)  # type: ignore
    try:
        while True:
            await asyncio.sleep(10)
            try:
                if engine is not None:
                    summary = engine.get_state_summary()
                    await websocket.send_json({"type": "state_update", "payload": summary})
                    approvals = await _get_approvals()
                    await websocket.send_json({"type": "approvals_update", "payload": approvals})
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        try:
            websockets.remove(websocket)  # type: ignore
        except Exception:
            pass


@app.post("/train")
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


@app.post("/chat")
async def chat(q: str, request: Request) -> dict[str, str | dict[str, str]]:
    if engine is None:
        return {"answer": "Engine not ready"}
    engine.add_memory("user", q)

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

    context_txt = ""
    prompt = q
    if retriever is not None and format_context is not None:
        try:
            docs = retriever.search(q, k=5)  # type: ignore[operator]
            context_txt = format_context(docs)  # type: ignore[operator]
            prompt = (
                f"[CONTEXT]\n{context_txt}\n\n"
                f"[QUESTION]\n{q}\n\n"
                "Cite using [#]. If not in context, say 'Not in context'."
            )
        except Exception:
            prompt = q

    answer = "Placeholder: HiveMind unavailable"
    policy_used = None

    # Model routing: choose roles object
    roles_obj = text_roles
    try:
        routing = bool(getattr(settings, "MODEL_ROUTING_ENABLED", False)) if settings else False
        chosen_model = None
        ctx: dict[str, Any] = {}
        if resource_estimator is not None:
            try:
                ctx["estimated_cost"] = resource_estimator.estimate_cost("implementer", "large")
            except Exception:
                pass
        if intent_modeler is not None:
            try:
                ctx["operator_intent"] = intent_modeler.current_intent
            except Exception:
                pass
        if engine is not None:
            try:
                ctx["phi"] = engine.get_state_summary().get("self_awareness_metrics", {}).get("phi")
            except Exception:
                pass
        ctx["planner_hints"] = planner_hints or []
        ctx["reasoning_steps"] = reasoning_steps or ""
        decision = None
        if strategy_selector is not None:
            try:
                decision = await strategy_selector.decide(prompt, ctx)
                policy_used = decision.get("strategy") if decision else None
                if decision and decision.get("reason"):
                    request.scope["selector_reason"] = decision["reason"]
                chosen_model = decision.get("model") if decision else None
            except Exception:
                decision = None
        if routing:
            if not chosen_model:
                short = len(q) < 160 and not context_txt
                chosen_model = "small" if short else "large"
            if chosen_model == "small" and text_roles_small is not None:
                roles_obj = text_roles_small
            elif chosen_model == "large" and text_roles_large is not None:
                roles_obj = text_roles_large
    except Exception:
        roles_obj = text_roles

    if roles_obj is not None and judge is not None and settings is not None:
        try:
            policy = policy_used
            if not policy and decide_policy is not None:
                policy = decide_policy(task_type="text", prompt=prompt)  # type: ignore[operator]
            if policy == "committee":
                tasks: List[str] = await asyncio.gather(*[
                    roles_obj.implementer(prompt)  # type: ignore[attr-defined]
                    for _ in range(settings.committee_k)
                ])
                rankings = await judge.rank(tasks, prompt=prompt)  # type: ignore[attr-defined]
                answer = judge.merge(tasks, rankings)  # type: ignore[attr-defined]
            elif policy == "debate":
                a1 = await roles_obj.architect(prompt)  # type: ignore[attr-defined]
                a2 = await roles_obj.implementer(prompt)  # type: ignore[attr-defined]
                rankings = await judge.rank([a1, a2], prompt=prompt)  # type: ignore[attr-defined]
                answer = judge.select([a1, a2], rankings)  # type: ignore[attr-defined]
            elif policy == "clone_dispatch":
                answer = await roles_obj.implementer(prompt)  # type: ignore[attr-defined]
            elif policy == "self_extension_prompt":
                answer = "Self‑extension requests are not supported by this endpoint"
            elif policy == "cross_modal_synthesis":
                img_desc = context_txt if context_txt else None
                try:
                    answer = await roles_obj.fusion_agent(prompt, image_description=img_desc)  # type: ignore[attr-defined]
                except Exception as exc:
                    answer = f"Error generating cross‑modal answer: {exc}"
            else:
                answer = await roles_obj.implementer(prompt)  # type: ignore[attr-defined]
        except Exception as exc:
            answer = f"Error generating answer: {exc}"

    engine.add_memory("assistant", answer)

    try:
        if hasattr(text_roles, "c"):
            client = text_roles.c  # type: ignore[attr-defined]
            adapter_version = getattr(client, "current_adapter_version", None)
            if adapter_version:
                request.scope["adapter_version"] = adapter_version
    except Exception:
        pass

    result: dict[str, str | dict[str, str]] = {"answer": answer}
    if policy_used:
        result["reasoning_strategy"] = str(policy_used)
    try:
        sr = request.scope.get("selector_reason")
        if sr:
            result["selector_reason"] = sr
    except Exception:
        pass
    if context_txt:
        result["context"] = context_txt
    if planner_hints:
        result["planner_hints"] = planner_hints  # type: ignore
    if reasoning_steps:
        result["reasoning_steps"] = reasoning_steps  # type: ignore
    return result


@app.post("/vision")
async def vision(question: str, file: UploadFile = File(...), grounding_required: bool = False, request: Request = None):
    if engine is None:
        return {"answer": "Engine not ready"}
    if vl_roles is None or judge is None:
        return {"answer": "Vision pipeline unavailable"}
    image_data = await file.read()
    engine.add_memory("user", question)
    answer: str = "Vision processing unavailable"
    critique: Optional[str] = None
    grounding: Optional[dict[str, any]] = None
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
    resp: dict[str, any] = {"answer": answer}
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