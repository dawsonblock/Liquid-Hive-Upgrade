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

# Optional: integrate internet_agent_advanced plugin routes and metrics if available
try:
    from internet_agent_advanced.fastapi_plugin import router as tools_router, metrics_app as ia_metrics_app, test_router as ia_test_router  # type: ignore
    # Mount tool/test routers under API prefix to satisfy ingress rules
    app.include_router(tools_router, prefix=API_PREFIX)
    app.include_router(ia_test_router, prefix=API_PREFIX)
    # Mount metrics app under API prefix; avoid conflict with existing /api/metrics
    try:
        app.mount(f"{API_PREFIX}/internet-agent-metrics", ia_metrics_app)
    except Exception:
        pass
except Exception:
    # Plugin not present; continue without IA advanced features
    pass

app = FastAPI(title="Fusion HiveMind Capsule", version="0.1.12")

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
    global settings, retriever, engine, text_roles, judge, strategy_selector, vl_roles
    global resource_estimator, adapter_manager, tool_auditor, intent_modeler, confidence_modeler, ds_router
    if Settings is not None:
        settings = Settings()
    if DSRouter is not None and RouterConfig is not None:
        router_config = RouterConfig.from_env()
        ds_router = DSRouter(router_config)
        try:
            asyncio.get_event_loop().create_task(ds_router.get_provider_status())
        except Exception:
            pass
    if Retriever is not None and settings is not None:
        try:
            retriever = Retriever(settings.rag_index, settings.embed_model)
        except Exception:
            retriever = None
    if CapsuleEngine is not None:
        try:
            engine = CapsuleEngine()
        except Exception:
            engine = None
    if TextRoles is not None and settings is not None:
        try:
            text_roles = TextRoles(settings)
        except Exception:
            text_roles = None
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


@app.get(f"{API_PREFIX}/healthz")
async def healthz() -> dict[str, Any]:
    return {
        "ok": bool(ds_router is not None),
        "engine_ready": bool(engine is not None),
        "router_ready": bool(ds_router is not None)
    }


@app.get(f"{API_PREFIX}/vllm/models")
async def vllm_models() -> Dict[str, Any]:
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


@app.get(f"{API_PREFIX}/providers")
async def get_providers_status() -> Dict[str, Any]:
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


@app.get(f"{API_PREFIX}/state")
async def state() -> dict[str, Any]:
    if engine is None:
        return {"engine_ready": False}
    return engine.get_state_summary()


@app.websocket(f"{API_PREFIX}/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    websockets.append(websocket)  # type: ignore
    try:
        while True:
            await asyncio.sleep(10)
            try:
                await websocket.send_json({
                    "type": "heartbeat",
                    "payload": {"ts": asyncio.get_event_loop().time(), "engine_ready": engine is not None}
                })
                if engine is not None:
                    summary = engine.get_state_summary()
                    await websocket.send_json({"type": "state_update", "payload": summary})
                    approvals = await _get_approvals()
                    await websocket.send_json({"type": "approvals_update", "payload": approvals})
                else:
                    await websocket.send_json({"type": "state_update", "payload": {"engine_ready": False}})
                    await websocket.send_json({"type": "approvals_update", "payload": []})
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
    q = sanitize_input(q)
    if engine is not None:
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
        # Compute chat timeout allowing R1 if escalation is enabled
        base_chat_timeout = float(os.getenv("CHAT_TIMEOUT_SECS", "15"))
        r1_timeout = float(os.getenv("R1_TIMEOUT_SECS", "30"))
        enable_r1 = str(os.getenv("ENABLE_R1_ESCALATION", "false")).lower() in ("1", "true", "yes")
        chat_timeout = max(base_chat_timeout, r1_timeout + 5.0) if enable_r1 else base_chat_timeout

        gen_response = await asyncio.wait_for(ds_router.generate(gen_request), timeout=chat_timeout)
        answer = gen_response.content
        provider_used = gen_response.provider
        confidence = gen_response.confidence
        escalated = gen_response.metadata.get("escalated", False)

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
        answer = (
            "I apologize, but I'm currently unable to process your request due to temporary "
            "system limitations. Please try again shortly."
        )
        provider_used = "system_fallback"
        confidence = 0.0
        escalated = False

    if engine is not None:
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