"""
Fusion server
==============

This module defines a FastAPI application that unifies the Capsule‑Brain operator
shell with the HiveMind intelligence core.  At startup we initialise both
subsystems and lazily allocate the underlying clients used by HiveMind.  At
shutdown we close any resources held by the Capsule engine.

Endpoints
---------

* ``GET /healthz`` – simple health check; reports whether the Capsule engine has been
  initialised.
* ``POST /chat`` – accepts a string payload named ``q`` and orchestrates the
  request through the Capsule memory, HiveMind retrieval and policy layers.
  The result includes the chosen answer and the context used if RAG is enabled.

The actual intelligence for answering prompts lives in the HiveMind project.
This server merely provides the glue code to call into those roles while
recording interactions into the Capsule memory.  In environments where the
HiveMind clients cannot be instantiated (for example, if the vLLM endpoint is
unreachable) the service will fall back to returning a placeholder answer.
"""

from __future__ import annotations

import asyncio
from typing import Optional, List, Any, Dict
import sys
import os
import uuid

from fastapi import FastAPI, UploadFile, File, Request
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

# Observability: import Prometheus metrics middleware and router from capsule_brain
try:
    from capsule_brain.observability.metrics import MetricsMiddleware, router as metrics_router
    from capsule_brain.planner.plan import plan_once
except Exception:
    MetricsMiddleware = None  # type: ignore
    metrics_router = None  # type: ignore
    plan_once = None  # type: ignore

# Capsule‑Brain imports
from capsule_brain.core.capsule_engine import CapsuleEngine

# HiveMind imports – these may raise ImportError if optional dependencies are
# missing.  The imports are wrapped in a try/except block in the startup
# callback below.
try:
    from hivemind.roles_text import TextRoles
    from hivemind.judge import Judge
    from hivemind.policies import decide_policy
    from hivemind.strategy_selector import StrategySelector
    from hivemind.rag.retriever import Retriever
    from hivemind.rag.citations import format_context
    from hivemind.config import Settings
    from hivemind.clients.vllm_client import VLLMClient
    # Optionally import vision client and roles
    from hivemind.clients.vl_client import VLClient
    from hivemind.roles_vl import VisionRoles
    from hivemind.resource_estimator import ResourceEstimator
    from hivemind.adapter_deployment_manager import AdapterDeploymentManager
    from hivemind.tool_auditor import ToolAuditor
    from capsule_brain.core.intent_modeler import IntentModeler
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

# Optional: Redis for leader election
try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore

app = FastAPI(title="Fusion HiveMind Capsule", version="0.1.2")

# If available, attach the Prometheus metrics middleware and route
if MetricsMiddleware is not None:
    app.add_middleware(MetricsMiddleware)
if metrics_router is not None:
    app.include_router(metrics_router)

# Static mounting is appended at the end of this module after all API routes
# are registered to ensure API endpoints take precedence over the SPA fallthrough.

# Global objects.  These are initialised in the startup event.
engine: Optional[CapsuleEngine] = None
text_roles: Optional[TextRoles] = None
judge: Optional[Judge] = None
retriever: Optional[Retriever] = None
settings: Optional[Settings] = None
strategy_selector: Optional[StrategySelector] = None
vl_roles: Optional[VisionRoles] = None
resource_estimator: Optional[ResourceEstimator] = None
adapter_manager: Optional[AdapterDeploymentManager] = None
tool_auditor: Optional[ToolAuditor] = None
intent_modeler: Optional[IntentModeler] = None

# Autonomy orchestrator
try:
    from hivemind.autonomy.orchestrator import AutonomyOrchestrator
except Exception:
    AutonomyOrchestrator = None  # type: ignore

autonomy_orchestrator: Optional[AutonomyOrchestrator] = None
_autonomy_lock: Any = None
_autonomy_lock_key = "liquid_hive:autonomy_leader"
_autonomy_id = uuid.uuid4().hex

# Track connected websocket clients
websockets: list[WebSocket] = []


def _env_write(key: str, value: str) -> None:
    """Persist a key=value into the project .env file safely.

    This updates or inserts the key while preserving other lines and comments.
    """
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
        # Non-fatal; ignore persistence errors
        pass


async def _start_autonomy_with_leader_election() -> None:
    """Start the AutonomyOrchestrator with a cluster-wide leader lock via Redis.

    Only the instance holding the Redis lock runs autonomy loops. Others stay
    dormant and periodically attempt to acquire leadership.
    """
    global autonomy_orchestrator, _autonomy_lock
    if AutonomyOrchestrator is None or engine is None or settings is None:
        return
    # If redis is unavailable or no URL provided, do not start autonomy to avoid split-brain
    if redis is None or not getattr(settings, "redis_url", None):
        return
    try:
        r = redis.Redis.from_url(settings.redis_url, decode_responses=True)  # type: ignore
        lock = r.lock(_autonomy_lock_key, timeout=120)  # 2 minutes lease
        got = lock.acquire(blocking=False)
        if not got:
            return
        _autonomy_lock = lock
        autonomy_orchestrator = AutonomyOrchestrator(engine, adapter_manager, settings)  # type: ignore
        await autonomy_orchestrator.start()

        async def renew_lock() -> None:
            while True:
                try:
                    # Extend the lease if still held
                    lock.extend(120)
                except Exception:
                    # Failed to extend, likely lost leadership; stop orchestrator
                    try:
                        if autonomy_orchestrator is not None:
                            await autonomy_orchestrator.stop()
                    except Exception:
                        pass
                    return
                await asyncio.sleep(60)

        asyncio.get_event_loop().create_task(renew_lock())
    except Exception:
        # On any error, do not start to avoid multiple leaders
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
    """Initialise the Capsule engine, HiveMind clients and strategy selector."""
    global engine, text_roles, judge, retriever, settings, strategy_selector
    global vl_roles, resource_estimator, adapter_manager, tool_auditor, intent_modeler
    # start the Capsule engine; this sets up memory, graph and background tasks
    engine = CapsuleEngine()
    await engine.start_background_tasks()

    # Attempt to construct HiveMind clients.  These may fail if optional
    # dependencies such as vLLM are not available in the runtime environment.  In
    # that case the service will continue to operate, but answers will be
    # placeholders.
    try:
        if Settings is None:
            raise RuntimeError("HiveMind settings unavailable")
        settings_ = Settings()  # type: ignore
        # Initialise optional services first so dependencies can reference them
        resource_estimator_ = ResourceEstimator() if ResourceEstimator else None
        adapter_manager_ = AdapterDeploymentManager() if AdapterDeploymentManager else None
        tool_auditor_ = ToolAuditor(settings_.runs_dir) if ToolAuditor and settings_ else None
        intent_modeler_ = IntentModeler(engine) if IntentModeler and engine else None
        # Instantiate the vLLM client used by text roles, judge and strategy selector
        vclient = VLLMClient(
            settings_.vllm_endpoint,
            settings_.vllm_api_key,
            max_new_tokens=settings_.max_new_tokens,
            adapter=settings_.text_adapter_path,
            adapter_manager=adapter_manager_,
            role="implementer",
        )
        text_roles_ = TextRoles(vclient) if TextRoles else None
        judge_ = Judge(vclient) if Judge else None
        selector_ = StrategySelector(vclient) if StrategySelector else None
        retriever_ = Retriever(settings_.rag_index, settings_.embed_model) if Retriever else None
        # Instantiate vision client and roles if possible
        if VLClient and VisionRoles:
            try:
                vl_client = VLClient(settings_.vl_model_id)
                vl_roles_ = VisionRoles(vl_client)
            except Exception:
                vl_roles_ = None
        else:
            vl_roles_ = None
        # Assign to globals
        settings = settings_
        text_roles = text_roles_
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
        judge = None
        retriever = None
        settings = None
        vl_roles = None
        resource_estimator = None
        adapter_manager = None
        tool_auditor = None
        intent_modeler = None

    # Launch the tool auditor loop if available
    if tool_auditor is not None and engine is not None:
        async def auditor_loop() -> None:
            while True:
                try:
                    underperforming = tool_auditor.flag_underperforming()
                    for tool_name in underperforming:
                        prompt = (
                            f"The tool '{tool_name}' has a high failure rate. "
                            f"Please analyze its implementation and propose a more resilient version."
                        )
                        engine.add_memory("self_extension", prompt)
                except Exception:
                    pass
                await asyncio.sleep(60)
        try:
            asyncio.get_event_loop().create_task(auditor_loop())
        except Exception:
            pass

    # Launch a resource estimator update loop if available
    if resource_estimator is not None:
        async def estimator_loop() -> None:
            while True:
                try:
                    resource_estimator.update_from_logs(settings.runs_dir if settings else "./runs")  # type: ignore
                except Exception:
                    pass
                await asyncio.sleep(120)
        try:
            asyncio.get_event_loop().create_task(estimator_loop())
        except Exception:
            pass

    # Launch the autonomy orchestrator with leader election
    await _start_autonomy_with_leader_election()


@app.on_event("shutdown")
async def shutdown() -> None:
    """Shutdown the Capsule engine when the service exits."""
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

# Helper to get approvals list from memory
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

# --- Approval Queue Endpoints ---
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

# --- Adapter deployment endpoints ---
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

# --- Governor configuration endpoints ---
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

# State and WebSocket endpoints unchanged ... (below)

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
        # Also build VL dataset if logs include VL interactions
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
    if text_roles is not None and judge is not None and settings is not None:
        try:
            ctx: dict[str, Any] = {}
            ctx["gpu_utilization_percent"] = "N/A"
            ctx["tools"] = []
            if resource_estimator is not None:
                ctx["estimated_cost"] = resource_estimator.estimate_cost("implementer")
            try:
                if intent_modeler is not None:
                    ctx["operator_intent"] = intent_modeler.current_intent
            except Exception:
                pass
            try:
                if engine is not None:
                    phi = engine.get_state_summary().get("self_awareness_metrics", {}).get("phi")
                    ctx["phi"] = phi
            except Exception:
                pass
            ctx["planner_hints"] = planner_hints or []
            ctx["reasoning_steps"] = reasoning_steps or ""
            policy = None
            if strategy_selector is not None:
                decision = await strategy_selector.decide(prompt, ctx)
                policy = decision.get("strategy")
                policy_used = policy
            if not policy and decide_policy is not None:
                policy = decide_policy(task_type="text", prompt=prompt)  # type: ignore[operator]
            if policy == "committee":
                tasks: List[str] = await asyncio.gather(*[
                    text_roles.implementer(prompt)  # type: ignore[attr-defined]
                    for _ in range(settings.committee_k)
                ])
                rankings = await judge.rank(tasks, prompt=prompt)  # type: ignore[attr-defined]
                answer = judge.merge(tasks, rankings)  # type: ignore[attr-defined]
            elif policy == "debate":
                a1 = await text_roles.architect(prompt)  # type: ignore[attr-defined]
                a2 = await text_roles.implementer(prompt)  # type: ignore[attr-defined]
                rankings = await judge.rank([a1, a2], prompt=prompt)  # type: ignore[attr-defined]
                answer = judge.select([a1, a2], rankings)  # type: ignore[attr-defined]
            elif policy == "clone_dispatch":
                answer = await text_roles.implementer(prompt)  # type: ignore[attr-defined]
            elif policy == "self_extension_prompt":
                answer = "Self‑extension requests are not supported by this endpoint"
            elif policy == "cross_modal_synthesis":
                img_desc = context_txt if context_txt else None
                try:
                    answer = await text_roles.fusion_agent(prompt, image_description=img_desc)  # type: ignore[attr-defined]
                except Exception as exc:
                    answer = f"Error generating cross‑modal answer: {exc}"
            else:
                answer = await text_roles.implementer(prompt)  # type: ignore[attr-defined]
            policy_used = policy_used or policy or "single"
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
    if context_txt:
        result["context"] = context_txt
    if planner_hints:
        result["planner_hints"] = planner_hints  # type: ignore
    if reasoning_steps:
        result["reasoning_steps"] = reasoning_steps  # type: ignore
    return result

# Vision endpoint unchanged except for signature
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

# Mount GUI static content (SPA)
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