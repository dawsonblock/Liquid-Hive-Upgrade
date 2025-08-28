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

app = FastAPI(title="Fusion HiveMind Capsule", version="0.1.1")

# If available, attach the Prometheus metrics middleware and route
if MetricsMiddleware is not None:
    app.add_middleware(MetricsMiddleware)
if metrics_router is not None:
    app.include_router(metrics_router)

# Serve the React GUI if the build directory exists. Prefer Vite's dist/ but
# maintain compatibility with CRA's build/ if present.
try:
    import pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    gui_dist_path = repo_root / "gui" / "dist"
    gui_build_path = repo_root / "gui" / "build"
    static_root: Optional[pathlib.Path] = None
    if gui_dist_path.exists():
        static_root = gui_dist_path
    elif gui_build_path.exists():
        static_root = gui_build_path
    if static_root is not None:
        # Mount at root to serve index.html and assets. Keep html=True so unknown
        # routes fall back to index.html for SPA routing.
        app.mount("/", StaticFiles(directory=str(static_root), html=True), name="gui")
except Exception:
    pass

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
        # Load configuration from environment or .env file.  See hivemind/config.py
        # for details of the Settings fields.
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
        # Instantiate the strategy selector using the same VLLM client
        selector_ = StrategySelector(vclient) if StrategySelector else None
        # Initialise retriever for RAG.  If the configured index does not exist
        # then search() will return an empty list.
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
        # In constrained environments the imports above may fail.  Log and
        # continue with None placeholders.  Logging is deferred to the capsule
        # logger through the engine if available.
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
                        # Compose a self‑extension prompt and insert into memory
                        prompt = (
                            f"The tool '{tool_name}' has a high failure rate. "
                            f"Please analyze its implementation and propose a more resilient version."
                        )
                        # Log the prompt for future processing by the HiveMind
                        engine.add_memory("self_extension", prompt)
                    # Wait between analyses
                except Exception:
                    pass
                await asyncio.sleep(60)  # run every minute
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
                await asyncio.sleep(120)  # update every two minutes
        try:
            asyncio.get_event_loop().create_task(estimator_loop())
        except Exception:
            pass

    # Launch the autonomy orchestrator if enabled
    global autonomy_orchestrator
    if AutonomyOrchestrator is not None and engine is not None and settings is not None:
        try:
            # Ensure we use the same adapter manager as the main runtime
            autonomy_orchestrator = AutonomyOrchestrator(engine, adapter_manager, settings)  # type: ignore
            await autonomy_orchestrator.start()
        except Exception:
            pass


@app.on_event("shutdown")
async def shutdown() -> None:
    """Shutdown the Capsule engine when the service exits."""
    if engine is not None:
        await engine.shutdown()


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    """Health check endpoint.

    Returns ``{"ok": True}`` if the Capsule engine has been initialised, otherwise
    ``{"ok": False}``.
    """
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
    """Return pending approval proposals.

    Each item includes an ``id`` (index in memory) and the proposal content.
    """
    return await _get_approvals()


@app.post("/approvals/{idx}/approve")
async def approve_proposal(idx: int) -> Dict[str, str]:
    """Approve a proposal by index and record approval.

    When approved, the proposal is removed from memory and an 'approved'
    entry is recorded.
    """
    if engine is None:
        return {"error": "Engine not ready"}
    try:
        item = engine.memory[idx]  # type: ignore
        if item.get("role") != "approval":
            raise IndexError
        # Record approval feedback
        engine.add_memory("approval_feedback", f"APPROVED: {item.get('content', '')}")  # type: ignore
        # Remove the proposal
        del engine.memory[idx]  # type: ignore
        return {"status": "approved"}
    except Exception:
        return {"error": "Invalid approval index"}


@app.post("/approvals/{idx}/deny")
async def deny_proposal(idx: int) -> Dict[str, str]:
    """Deny a proposal by index and record denial."""
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
    """Return the current adapter deployment state.

    Each entry contains the role, the champion (active) adapter and the
    challenger adapter if present.
    """
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
    """Raw adapter manager state for detailed UI."""
    if adapter_manager is None:
        return {"state": {}}
    try:
        return {"state": adapter_manager.state}  # type: ignore
    except Exception as exc:
        return {"error": str(exc)}


@app.post("/adapters/promote/{role}")
async def promote_adapter(role: str) -> Dict[str, Any]:
    """Promote the challenger adapter to champion for the given role."""
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
    """Return current Arbiter governor flags."""
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
    """Update the Arbiter governor configuration.

    Accepts JSON with ENABLE_ORACLE_REFINEMENT and FORCE_GPT4O_ARBITER keys, or
    shorthand keys {"enabled": bool, "force_gpt4o": bool}. Updates in-memory
    settings and attempts to persist to the project .env file.
    """
    global settings
    if settings is None:
        return {"error": "Settings unavailable"}
    try:
        enable_val = cfg.get("ENABLE_ORACLE_REFINEMENT")
        force_val = cfg.get("FORCE_GPT4O_ARBITER")
        # Accept shorthand keys
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


# Expose the internal state of the Capsule engine for introspection.  This
# endpoint returns a summary including memory size, knowledge graph stats and
# self‑awareness metrics such as the IIT surrogate Φ.
@app.get("/state")
async def state() -> dict[str, Any]:
    if engine is None:
        return {"error": "Engine not ready"}
    return engine.get_state_summary()


# WebSocket endpoint for real‑time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Stream periodic state updates to connected clients.

    Every 10 seconds this endpoint sends the current state summary under
    the ``state_update`` event type. Additionally it sends the current
    approvals list so clients can update in real-time.
    """
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


# Allow the operator to trigger the self‑improvement pipeline.  When called,
# this endpoint will attempt to build a new SFT/DPO dataset from recent run
# logs and fine‑tune the LoRA adapters.  In this environment heavy ML
# dependencies may not be available, so the function returns immediately
# with a placeholder response.
@app.post("/train")
async def train() -> dict[str, str]:
    """Kick off the self‑improvement training loop.

    This endpoint attempts to build new SFT/DPO datasets from the run logs
    and fine‑tune a LoRA adapter using the existing training scripts.  If the
    required ML dependencies are unavailable the endpoint will return an
    error.  When successful it returns the path to the new adapter.
    """
    try:
        # Step 1: build datasets from run logs
        from hivemind.training.dataset_build import build_text_sft_and_prefs
        build_text_sft_and_prefs()

        # Step 2: fine‑tune a new LoRA adapter.  Use a subprocess call to
        # leverage the existing script with command‑line arguments.  The
        # adapter will be written to the adapters/text/ directory.
        import subprocess, pathlib, uuid
        out_dir = pathlib.Path("adapters/text") / f"adapter_{uuid.uuid4().hex}"
        out_dir.mkdir(parents=True, exist_ok=True)
        # The training script expects a base model and dataset path; rely on
        # defaults defined in the script.  Adjust hyperparameters if needed.
        subprocess.run([
            sys.executable,
            "-m",
            "hivemind.training.sft_text",
            "--out",
            str(out_dir),
        ], check=True)

        # Update settings so that future requests use the new adapter
        if settings is not None:
            settings.text_adapter_path = str(out_dir)
        return {"status": "success", "adapter_path": str(out_dir)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post("/chat")
async def chat(q: str, request: Request) -> dict[str, str | dict[str, str]]:
    """Chat endpoint.

    Accepts a query string ``q``, records it into the Capsule memory and then
    orchestrates a response via HiveMind if available.  The returned payload
    always includes the key ``answer`` containing either a real answer from
    HiveMind or a placeholder.  If retrieval‑augmented generation was used, the
    RAG context is returned under the key ``context``.
    """
    if engine is None:
        return {"answer": "Engine not ready"}
    # Record the user query in the Capsule memory
    engine.add_memory("user", q)

    # First, run the planner to get high‑level hints about how to approach the query.
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

    # Prepare prompt and context
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
            # If retrieval fails fall back to the plain question
            prompt = q

    answer = "Placeholder: HiveMind unavailable"
    # Decide which reasoning strategy to apply.  Prefer the dynamic selector
    # when available; otherwise fall back to the static policy function.
    if text_roles is not None and judge is not None and settings is not None:
        try:
            # Prepare a minimal system context for the strategy selector
            ctx: dict[str, Any] = {}
            # GPU utilisation is not readily available in this runtime; leave as N/A
            ctx["gpu_utilization_percent"] = "N/A"
            # No explicit tools are exposed from CapsuleEngine; pass empty list
            ctx["tools"] = []
            # Include cost estimator if available; set an arbitrary max_cost
            if resource_estimator is not None:
                ctx["estimated_cost"] = resource_estimator.estimate_cost("implementer")
            # Provide the current operator intent if available
            try:
                if intent_modeler is not None:
                    ctx["operator_intent"] = intent_modeler.current_intent
            except Exception:
                pass
            # Include the latest IIT φ metric if available to give the selector
            # an indication of internal coherence.  φ closer to zero implies low
            # integration; higher values reflect more integrated state.
            try:
                if engine is not None:
                    phi = engine.get_state_summary().get("self_awareness_metrics", {}).get("phi")
                    ctx["phi"] = phi
            except Exception:
                pass
            # Provide planner hints and reasoning steps to the selector
            ctx["planner_hints"] = planner_hints or []
            ctx["reasoning_steps"] = reasoning_steps or ""
            policy = None
            # If the dynamic strategy selector is available, use it
            if strategy_selector is not None:
                decision = await strategy_selector.decide(prompt, ctx)
                policy = decision.get("strategy")
            # If the selector returns nothing or is unavailable, use the static policy
            if not policy and decide_policy is not None:
                policy = decide_policy(task_type="text", prompt=prompt)  # type: ignore[operator]
            # Execute the chosen policy
            if policy == "committee":
                # Run multiple implementers in parallel
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
                # Clone dispatch is not supported in this environment; fall back to single
                answer = await text_roles.implementer(prompt)  # type: ignore[attr-defined]
            elif policy == "self_extension_prompt":
                # Self‑extension prompts are not handled here; return a polite message
                answer = "Self‑extension requests are not supported by this endpoint"
            elif policy == "cross_modal_synthesis":
                # Cross‑modal synthesis: combine retrieval context (if any) as an image description
                img_desc = context_txt if context_txt else None
                try:
                    answer = await text_roles.fusion_agent(prompt, image_description=img_desc)  # type: ignore[attr-defined]
                except Exception as exc:
                    answer = f"Error generating cross‑modal answer: {exc}"
            else:
                # Default to the single implementer path
                answer = await text_roles.implementer(prompt)  # type: ignore[attr-defined]
        except Exception as exc:
            # If any HiveMind call fails capture the exception in the answer
            answer = f"Error generating answer: {exc}"

    # Record the assistant answer in Capsule memory
    engine.add_memory("assistant", answer)

    # If a VLLM client was used, expose the adapter version to the metrics middleware.
    try:
        if hasattr(text_roles, "c"):
            client = text_roles.c  # type: ignore[attr-defined]
            # Attempt to read adapter version attribute
            adapter_version = getattr(client, "current_adapter_version", None)
            if adapter_version:
                # Store in the request scope for metrics middleware
                request.scope["adapter_version"] = adapter_version
    except Exception:
        pass

    result: dict[str, str | dict[str, str]] = {"answer": answer}
    if context_txt:
        result["context"] = context_txt
    # Expose planner hints in the response for transparency
    if planner_hints:
        result["planner_hints"] = planner_hints  # type: ignore
    if reasoning_steps:
        result["reasoning_steps"] = reasoning_steps  # type: ignore
    return result


# ---------------------------------------------------------------------------
# Multi‑modal Vision Endpoint
#
# This endpoint implements a rudimentary vision pipeline.  It accepts an image
# upload and a question, generates candidate answers using the HiveMind
# ``VisionRoles`` (if available), ranks them with the multi‑modal judge and
# returns the selected answer.  Optionally the answer can be validated
# against the image via the grounding validator.
@app.post("/vision")
async def vision(question: str, file: UploadFile = File(...), grounding_required: bool = False, request: Request = None) -> dict[str, any]:
    """Answer a visual question using the HiveMind vision agents.

    This endpoint records the question, invokes the vision committee and
    judge, and optionally validates the answer using the grounding
    validator.  If the required models are unavailable the response will
    indicate that vision functionality is missing.

    Parameters
    ----------
    question: str
        The user's question about the uploaded image.
    file: UploadFile
        The image file provided by the client.
    grounding_required: bool, optional
        If True, perform grounding validation on the chosen answer.

    Returns
    -------
    dict
        A JSON response containing the answer and optional critique and
        grounding information.
    """
    # Ensure the engine is initialised
    if engine is None:
        return {"answer": "Engine not ready"}
    # Check that the vision pipeline is available
    if vl_roles is None or judge is None:
        return {"answer": "Vision pipeline unavailable"}
    # Read image bytes from the uploaded file
    image_data = await file.read()
    # Log the user question
    engine.add_memory("user", question)
    # Default response values
    answer: str = "Vision processing unavailable"
    critique: Optional[str] = None
    grounding: Optional[dict[str, any]] = None
    try:
        # Generate a small set of candidate answers via the vision committee
        candidates = await vl_roles.vl_committee(question, image_data, k=2)  # type: ignore[attr-defined]
        # Rank the candidates using the multi‑modal judge
        rankings = await judge.rank_vision(question, image_data, candidates)  # type: ignore[attr-defined]
        wid = int(rankings.get("winner_id", 0))
        answer = candidates[wid] if 0 <= wid < len(candidates) else candidates[0]
        critique = rankings.get("critique")
        # Perform grounding validation if requested
        if grounding_required:
            grounding = vl_roles.grounding_validator(question, image_data, answer)  # type: ignore[attr-defined]
    except Exception as exc:
        answer = f"Error processing vision request: {exc}"
    # Record the assistant answer
    engine.add_memory("assistant", answer)

    # For vision requests there is no adapter selection; annotate as 'vl' version
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