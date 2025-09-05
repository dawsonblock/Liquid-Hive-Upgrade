"""Fusion server with Autonomy, Trust, Estimator, and Model Routing
===============================================================
"""

# pyright: reportMissingImports=false, reportDeprecated=false, reportUnusedImport=false, reportUnusedFunction=false
from __future__ import annotations

import asyncio
import json
import json as _json
import logging
import os
import sys
import time
import urllib.parse as _u
import urllib.request as _req
import uuid
from datetime import datetime
from typing import Any, cast

import httpx

log = logging.getLogger(__name__)

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Request, UploadFile

# Integrate internet agent advanced routes and metrics
try:
    from internet_agent_advanced.fastapi_plugin import metrics_app as internet_metrics_app
    from internet_agent_advanced.fastapi_plugin import router as internet_tools_router
    from internet_agent_advanced.fastapi_plugin import test_router as internet_test_router
except Exception:
    internet_tools_router = None  # type: ignore
    internet_metrics_app = None  # type: ignore
    internet_test_router = None  # type: ignore

# Add src to Python path for imports

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "src"))

from capsule_brain.security.input_sanitizer import sanitize_input

try:
    from capsule_brain.core.capsule_engine import CapsuleEngine
    from capsule_brain.observability.metrics import MetricsMiddleware
    from capsule_brain.observability.metrics import router as metrics_router
    from capsule_brain.planner.plan import plan_once
except Exception:
    MetricsMiddleware = None  # type: ignore
    metrics_router = None  # type: ignore
    plan_once = None  # type: ignore
    CapsuleEngine = None  # type: ignore

try:
    from hivemind.config import Settings
except Exception:
    Settings = None  # type: ignore

try:
    from .model_router import DSRouter, RouterConfig
except Exception as e:
    DSRouter = None  # type: ignore
    RouterConfig = None  # type: ignore
    log.warning(f"model_router import failed: {e}")

try:
    from .providers import (
        BaseProvider,
        DeepSeekChatProvider,
        DeepSeekR1Provider,
        DeepSeekThinkingProvider,
        GenRequest,
        GenResponse,
        QwenCPUProvider,
        StreamChunk,
    )
except Exception:
    BaseProvider = None  # type: ignore
    GenRequest = None  # type: ignore
    GenResponse = None  # type: ignore
    StreamChunk = None  # type: ignore
    DeepSeekChatProvider = None  # type: ignore
    DeepSeekThinkingProvider = None  # type: ignore
    DeepSeekR1Provider = None  # type: ignore
    QwenCPUProvider = None  # type: ignore

try:
    import importlib as _importlib

    _hm_roles_text = _importlib.import_module("hivemind.roles_text")
    TextRoles = getattr(_hm_roles_text, "TextRoles", None)
    _hm_judge = _importlib.import_module("hivemind.judge")
    Judge = getattr(_hm_judge, "Judge", None)
    _hm_policies = _importlib.import_module("hivemind.policies")
    decide_policy = getattr(_hm_policies, "decide_policy", None)
    StrategySelector = getattr(
        _importlib.import_module("hivemind.strategy_selector"), "StrategySelector", None
    )
    Retriever = getattr(_importlib.import_module("hivemind.rag.retriever"), "Retriever", None)
    format_context = getattr(
        _importlib.import_module("hivemind.rag.citations"), "format_context", None
    )
    VLLMClient = getattr(
        _importlib.import_module("hivemind.clients.vllm_client"), "VLLMClient", None
    )
    VLClient = getattr(_importlib.import_module("hivemind.clients.vl_client"), "VLClient", None)
    VisionRoles = getattr(_importlib.import_module("hivemind.roles_vl"), "VisionRoles", None)
    ResourceEstimator = getattr(
        _importlib.import_module("hivemind.resource_estimator"), "ResourceEstimator", None
    )
    AdapterDeploymentManager = getattr(
        _importlib.import_module("hivemind.adapter_deployment_manager"),
        "AdapterDeploymentManager",
        None,
    )
    ToolAuditor = getattr(_importlib.import_module("hivemind.tool_auditor"), "ToolAuditor", None)
    ConfidenceModeler = getattr(
        _importlib.import_module("hivemind.confidence_modeler"), "ConfidenceModeler", None
    )
    TrustPolicy = getattr(
        _importlib.import_module("hivemind.confidence_modeler"), "TrustPolicy", None
    )
except Exception:
    TextRoles = None  # type: ignore
    Judge = None  # type: ignore
    decide_policy = None  # type: ignore
    StrategySelector = None  # type: ignore
    Retriever = None  # type: ignore
    format_context = None  # type: ignore
    VLLMClient = None  # type: ignore
    VLClient = None  # type: ignore
    VisionRoles = None  # type: ignore
    ResourceEstimator = None  # type: ignore
    AdapterDeploymentManager = None  # type: ignore
    ToolAuditor = None  # type: ignore
    IntentModeler = None  # type: ignore
    ConfidenceModeler = None  # type: ignore
    TrustPolicy = None  # type: ignore

try:
    import importlib as _importlib

    _tools_mod = _importlib.import_module("hivemind.tools")
    ToolRegistry = getattr(_tools_mod, "ToolRegistry", None)
    global_registry = getattr(_tools_mod, "global_registry", None)
    CalculatorTool = getattr(
        _importlib.import_module("hivemind.tools.calculator_tool"), "CalculatorTool", None
    )
    WebSearchTool = getattr(
        _importlib.import_module("hivemind.tools.web_search_tool"), "WebSearchTool", None
    )
    FileOperationsTool = getattr(
        _importlib.import_module("hivemind.tools.file_operations_tool"), "FileOperationsTool", None
    )
    DatabaseQueryTool = getattr(
        _importlib.import_module("hivemind.tools.database_query_tool"), "DatabaseQueryTool", None
    )
    CodeAnalysisTool = getattr(
        _importlib.import_module("hivemind.tools.code_analysis_tool"), "CodeAnalysisTool", None
    )
    TextProcessingTool = getattr(
        _importlib.import_module("hivemind.tools.text_processing_tool"), "TextProcessingTool", None
    )
    SystemInfoTool = getattr(
        _importlib.import_module("hivemind.tools.system_info_tool"), "SystemInfoTool", None
    )
except Exception:
    ToolRegistry = None  # type: ignore
    global_registry = None  # type: ignore
    CalculatorTool = None  # type: ignore
    WebSearchTool = None  # type: ignore
    FileOperationsTool = None  # type: ignore
    DatabaseQueryTool = None  # type: ignore
    CodeAnalysisTool = None  # type: ignore
    TextProcessingTool = None  # type: ignore
    SystemInfoTool = None  # type: ignore

try:
    import redis  # type: ignore
except Exception:
    redis = None  # type: ignore

try:
    from hivemind.cache import SemanticCache, create_cache_manager, get_semantic_cache
except Exception:
    SemanticCache = None
    get_semantic_cache = None
    create_cache_manager = None

# Secrets manager (optional import, endpoints guard against absence)
try:
    from hivemind.secrets_manager import SecretProvider as _SecretProvider
    from hivemind.secrets_manager import secrets_manager as _secrets_manager  # type: ignore
except Exception:
    _secrets_manager = None  # type: ignore
    _SecretProvider = None  # type: ignore

# Curiosity Engine (Genesis Spark)
try:
    from hivemind.autonomy.curiosity import CuriosityEngine  # type: ignore
except Exception:
    CuriosityEngine = None  # type: ignore

API_PREFIX = "/api"


# Lifespan function must be defined before app creation
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize global components on startup."""
    global settings, retriever, engine, text_roles, judge, strategy_selector, vl_roles
    global \
        resource_estimator, \
        adapter_manager, \
        tool_auditor, \
        intent_modeler, \
        confidence_modeler, \
        ds_router, \
        tool_registry
    global get_semantic_cache, semantic_cache, cache_manager
    global autonomy_orchestrator, _autonomy_lock
    global text_roles_small, text_roles_large

    # Initialize settings
    if Settings is not None:
        try:
            settings = Settings()
            print("✅ Settings initialized")
        except Exception as e:
            print(f"❌ Settings initialization failed: {e}")
            settings = None
    else:
        settings = None

    # Initialize DS-Router
    if DSRouter is not None and RouterConfig is not None:
        try:
            router_config = RouterConfig.from_env()
            ds_router = DSRouter(router_config)
            print("✅ DS-Router initialized")
        except Exception as e:
            print(f"❌ DS-Router initialization failed: {e}")
            ds_router = None
    else:
        ds_router = None

    # Initialize retriever
    if settings is not None:
        try:
            if hasattr(settings, "rag_index") and hasattr(settings, "embed_model"):
                retriever = Retriever(settings.rag_index, settings.embed_model)
                print("✅ FAISS Retriever initialized")
        except Exception:
            retriever = None
    else:
        retriever = None

    # Initialize other components...
    if settings is not None:
        try:
            if TextRoles is not None:
                text_roles = TextRoles(settings)
                print("✅ Text Roles initialized")
        except Exception as e:
            print(f"❌ Text Roles initialization failed: {e}")
            text_roles = None

        try:
            if Judge is not None:
                judge = Judge(settings)
                print("✅ Judge initialized")
        except Exception as e:
            print(f"❌ Judge initialization failed: {e}")
            judge = None

    # Initialize Semantic Cache
    if get_semantic_cache is not None:
        try:
            semantic_cache = await get_semantic_cache(
                redis_url=getattr(settings, "redis_url", "redis://localhost:6379/0")
                if settings
                else "redis://localhost:6379/0",
                embedding_model=getattr(settings, "embed_model", "all-MiniLM-L6-v2")
                if settings
                else "all-MiniLM-L6-v2",
            )
            if semantic_cache and semantic_cache.is_ready:
                print("🧠 Semantic Cache initialized successfully")
                if create_cache_manager is not None:
                    cache_manager = await create_cache_manager(semantic_cache)
                    if cache_manager:
                        print("📈 Cache Manager initialized successfully")
                    else:
                        print("⚠️ Cache Manager initialization failed")
            else:
                print("⚠️ Semantic Cache initialization failed")

        except Exception as e:
            print(f"❌ Failed to initialize Semantic Cache: {e}")
            semantic_cache = None
            cache_manager = None

    # Initialize other components as needed
    # ... (additional component initialization can be added here)

    yield  # App is running

    # Cleanup on shutdown


app = FastAPI(title="Fusion HiveMind Capsule", version="0.1.7", lifespan=lifespan)

if MetricsMiddleware is not None:
    app.add_middleware(MetricsMiddleware)
if metrics_router is not None:
    app.include_router(metrics_router)


# Middleware to ensure arena is mounted when needed
@app.middleware("http")
async def arena_mounting_middleware(request, call_next):
    # Check if request is for arena and mount if needed
    if request.url.path.startswith("/api/arena"):
        ensure_arena_mounted()
    response = await call_next(request)
    return response


# Helper function to dynamically mount arena router
def ensure_arena_mounted():
    """Ensure arena router is mounted if ENABLE_ARENA is true."""
    try:
        enabled = str(os.getenv("ENABLE_ARENA", "false")).lower() == "true"
        if enabled:
            # Check if already mounted
            already = any(
                getattr(r, "path", "") and "/arena" in getattr(r, "path", "") for r in app.routes
            )
            if not already:
                from .arena import router as arena_router

                app.include_router(arena_router)
                log.info("✅ Arena router mounted dynamically")
    except Exception as e:
        log.error(f"❌ Failed to mount arena router: {e}")


# Mount arena router if enabled (for tests that set ENABLE_ARENA)
try:
    if str(os.getenv("ENABLE_ARENA", "false")).lower() == "true":
        from .arena import router as arena_router

        app.include_router(arena_router)
        log.info("✅ Arena router mounted at startup")
except Exception as e:
    log.error(f"❌ Failed to mount arena router at startup: {e}")

# Conditionally mount Arena service if enabled
try:
    from .arena import router as arena_router
except Exception:
    arena_router = None  # type: ignore

if False and arena_router is not None:
    # legacy static include disabled; we include dynamically in startup
    pass

# Include internet agent advanced routers and metrics if available
if "internet_tools_router" in globals() and internet_tools_router is not None:
    app.include_router(internet_tools_router)
if "internet_test_router" in globals() and internet_test_router is not None:
    app.include_router(internet_test_router)
if "internet_metrics_app" in globals() and internet_metrics_app is not None:
    # Mount under separate path to avoid conflict with existing metrics
    app.mount("/internet-agent-metrics", internet_metrics_app)

engine: Any | None = None
text_roles: Any | None = None
text_roles_small: Any | None = None
text_roles_large: Any | None = None
judge: Any | None = None
retriever: Any | None = None
settings: Any | None = None
strategy_selector: Any | None = None
vl_roles: Any | None = None
resource_estimator: Any | None = None
adapter_manager: Any | None = None
tool_auditor: Any | None = None
intent_modeler: Any | None = None
confidence_modeler: Any | None = None
ds_router: Any | None = None
tool_registry: Any | None = None

try:
    from hivemind.autonomy.orchestrator import AutonomyOrchestrator
except Exception:
    AutonomyOrchestrator = None  # type: ignore
    # Conditionally mount Arena at runtime (env may be mutated in tests)
    try:
        from .arena import router as arena_router  # type: ignore
    except Exception:
        arena_router = None  # type: ignore

    # Try to mount if enabled
    try:
        enabled = str(os.getenv("ENABLE_ARENA", "false")).lower() == "true"
        already = any(getattr(r, "prefix", "") == f"{API_PREFIX}/arena" for r in app.router.routes)
        if enabled and not already and arena_router is not None:
            app.include_router(arena_router)
    except Exception:
        pass


autonomy_orchestrator: Any | None = None
_autonomy_lock: Any = None
_autonomy_lock_key = "liquid_hive:autonomy_leader"
_autonomy_id = uuid.uuid4().hex

# Semantic cache
semantic_cache: Any | None = None
cache_manager = None

websockets: list[WebSocket] = []


# Original startup function converted to lifespan (duplicate removed)
async def startup_components():
    """Initialize global components on startup."""
    global settings, retriever, engine, text_roles, judge, strategy_selector, vl_roles
    global \
        resource_estimator, \
        adapter_manager, \
        tool_auditor, \
        intent_modeler, \
        confidence_modeler, \
        ds_router, \
        tool_registry
    global semantic_cache, cache_manager
    # Initialize OTEL tracer (if enabled)
    try:
        from .observability import setup_tracing_if_enabled  # type: ignore

        setup_tracing_if_enabled()
    except Exception:
        pass

    # Mount Arena router dynamically based on env (useful for tests)
    try:
        from .arena import router as arena_router  # type: ignore

        enabled = str(os.getenv("ENABLE_ARENA", "false")).lower() == "true"
        already = any(getattr(r, "prefix", "") == f"{API_PREFIX}/arena" for r in app.router.routes)
        if enabled and not already:
            app.include_router(arena_router)
            print("✅ Arena router mounted")
    except Exception as e:
        print(f"❌ Failed to mount arena router: {e}")
    # Mount Providers admin endpoints if present (keys redacted)
    try:
        from .providers_admin_mount import mount_admin_providers  # type: ignore

        mount_admin_providers(app)
    except Exception:
        pass

    # Initialize settings
    if Settings is not None:
        settings = Settings()

    # Initialize DS-Router
    if DSRouter is not None and RouterConfig is not None:
        router_config = RouterConfig.from_env()
        ds_router = DSRouter(router_config)

    # Initialize retriever
    if Retriever is not None and settings is not None:
        # Try to initialize enhanced retriever with Qdrant support
        try:
            from hivemind.rag.hybrid_retriever import create_hybrid_retriever

            retriever = create_hybrid_retriever(settings)
            if retriever is not None and getattr(retriever, "is_ready", False):
                log.info("✅ Enhanced Hybrid RAG Retriever initialized successfully")
            else:
                # Fallback to original FAISS retriever
                retriever = Retriever(settings.rag_index, settings.embed_model)
                if getattr(retriever, "is_ready", False):
                    log.info("✅ FAISS RAG Retriever initialized (fallback mode)")
        except Exception as e:
            log.warning(f"Failed to initialize hybrid retriever: {e}")
            # Fallback to original retriever
            retriever = Retriever(settings.rag_index, settings.embed_model)

    # Initialize engine
    if CapsuleEngine is not None:
        engine = CapsuleEngine()

    # Initialize text roles
    if TextRoles is not None and settings is not None:
        # runtime import may be optional
        text_roles = TextRoles(settings)  # type: ignore[call-arg]

    # Initialize Tool Registry and discover tools
    if ToolRegistry is not None and global_registry is not None:
        tool_registry = global_registry

        # Register built-in tools (guard methods defensively)
        if tool_registry is not None and hasattr(tool_registry, "register_tool_class"):
            if CalculatorTool is not None:
                tool_registry.register_tool_class(CalculatorTool)
            if WebSearchTool is not None:
                tool_registry.register_tool_class(WebSearchTool)
            if FileOperationsTool is not None:
                tool_registry.register_tool_class(FileOperationsTool)
            if DatabaseQueryTool is not None:
                tool_registry.register_tool_class(DatabaseQueryTool)
            if CodeAnalysisTool is not None:
                tool_registry.register_tool_class(CodeAnalysisTool)
            if TextProcessingTool is not None:
                tool_registry.register_tool_class(TextProcessingTool)
            if SystemInfoTool is not None:
                tool_registry.register_tool_class(SystemInfoTool)

        # Discover additional tools
        if tool_registry is not None and hasattr(tool_registry, "discover_tools"):
            _ = tool_registry.discover_tools()
            try:
                tool_count = len(getattr(tool_registry, "tools", []))
            except Exception:
                tool_count = 0
            print(f"🛠️ Enhanced Tool Registry initialized with {tool_count} tools")
            if hasattr(tool_registry, "get_tools_by_category"):
                try:
                    cats = tool_registry.get_tools_by_category().keys()
                    print(f"📊 Tool categories: {', '.join(list(cats))}")
                except Exception:
                    pass
            if hasattr(tool_registry, "get_approval_required_tools"):
                try:
                    approval_tools = tool_registry.get_approval_required_tools()
                    if approval_tools:
                        print(f"🔒 Tools requiring approval: {', '.join(approval_tools)}")
                except Exception:
                    pass

    # Initialize Semantic Cache
    if get_semantic_cache is not None and settings is not None:
        try:
            redis_url = settings.redis_url or "redis://localhost:6379"
            semantic_cache = await get_semantic_cache(
                redis_url=redis_url,
                embedding_model=settings.embed_model or "all-MiniLM-L6-v2",
                # Lower threshold to improve recall for paraphrases
                similarity_threshold=0.88,
            )

            if semantic_cache and semantic_cache.is_ready:
                print("🧠 Semantic Cache initialized successfully")

                # Initialize cache manager
                if create_cache_manager is not None:
                    cache_manager = await create_cache_manager(redis_url)
                    if cache_manager:
                        print("📈 Cache Manager initialized successfully")
            else:
                print("⚠️ Semantic Cache initialization failed")

        except Exception as e:
            print(f"❌ Failed to initialize Semantic Cache: {e}")
            semantic_cache = None
            cache_manager = None

    # Initialize other components as needed
    # ... (additional component initialization can be added here)

    yield  # App is running

    # Cleanup on shutdown


def _env_write(key: str, value: str) -> None:
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        lines: list[str] = []
        if os.path.exists(env_path):
            with open(env_path, encoding="utf-8") as f:
                lines = f.read().splitlines()
        found = False
        new_lines: list[str] = []
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


def _prom_q(base_url: str | None, promql: str) -> dict[str, Any] | None:
    if not base_url:
        return None
    try:
        params = _u.urlencode({"query": promql})
        with _req.urlopen(f"{base_url}/api/v1/query?{params}") as r:  # nosec B310 - controlled prometheus URL
            data = cast(dict[str, Any], _json.loads(r.read().decode()))
            if data.get("status") == "success":
                return cast(dict[str, Any] | None, data.get("data"))
    except Exception:
        return None
    return None


def _scalar(data: dict[str, Any] | None) -> float | None:
    if not data:
        return None
    try:
        res_any: Any = data.get("result", [])
        if isinstance(res_any, list) and res_any and isinstance(res_any[0], dict):
            first: dict[str, Any] = cast(dict[str, Any], res_any[0])
            v = first.get("value", [None, None])[1]
            return float(v) if v is not None else None
        return None
    except Exception:
        return None


async def _broadcast_autonomy_event(event: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
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
async def vllm_models() -> dict[str, Any]:
    """Helper endpoint to query vLLM service for loaded models."""
    try:
        if settings is None or settings.vllm_endpoint is None:
            return {"error": "vLLM endpoint not configured"}
        url = settings.vllm_endpoint.rstrip("/") + "/v1/models"
        with _req.urlopen(url, timeout=5) as r:  # nosec B310 - controlled vLLM endpoint URL
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


@app.get(f"{API_PREFIX}/secrets/exists")
async def secret_exists(name: str) -> dict[str, Any]:
    """Check whether a secret exists (without returning its value)."""
    try:
        if _secrets_manager is None:
            return {"error": "Secrets manager unavailable"}
        # Guardrail for name format
        if not name or not all(c.isalnum() or c in ("_", ".", "/", "-") for c in name):
            return {"error": "Invalid secret name"}
        exists = _secrets_manager.get_secret(name) is not None  # type: ignore
        return {"name": name, "exists": bool(exists)}
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/secrets/set")
async def secret_set(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    """Store a secret via the configured secrets provider.

    Expected body: { "name": string, "value": string | object }
    - For provider 'vault': writes to Vault KV (if configured)
    - For provider 'environment': writes to process env and persists to .env
    - For provider 'aws_secrets_manager': returns an error (write not supported here)
    """
    try:
        if _secrets_manager is None:
            return {"error": "Secrets manager unavailable"}
        # Optional admin token check: if ADMIN_TOKEN is set, require matching header
        admin_token = os.getenv("ADMIN_TOKEN")
        if admin_token:
            header_token = request.headers.get("x-admin-token") or request.headers.get(
                "X-Admin-Token"
            )
            if header_token != admin_token:
                return {"error": "Unauthorized"}

        name = str(payload.get("name") or "").strip()
        value = payload.get("value")
        if not name:
            return {"error": "Missing secret name"}
        if not all(c.isalnum() or c in ("_", ".", "/", "-") for c in name):
            return {"error": "Invalid secret name"}
        if value is None:
            return {"error": "Missing secret value"}

        provider = _secrets_manager.get_provider()  # type: ignore
        # Disallow overly large values to avoid abuse
        try:
            serialized = json.dumps(value)
        except Exception:
            # Fallback to string conversion
            serialized = str(value)
        if len(serialized) > 32 * 1024:
            return {"error": "Secret value too large"}

        # Attempt to store via secrets manager
        ok = _secrets_manager.store_secret(name, value)  # type: ignore
        if not ok:
            # If provider is AWS, inform user to set secrets via AWS console or CI
            prov_name = provider.value if provider else "unknown"
            return {
                "error": f"Write not supported for provider '{prov_name}'. Configure this secret in your provider.",
                "provider": prov_name,
            }

        # Persist to .env when using environment provider to survive restarts
        if _SecretProvider is not None and provider == _SecretProvider.ENVIRONMENT:
            try:
                _env_write(name, serialized if isinstance(value, dict | list) else str(value))
            except Exception:
                # Non-fatal
                pass

        # Do not return the secret value
        return {"status": "stored", "name": name, "provider": provider.value if provider else None}
    except Exception as exc:
        return {"error": str(exc)}


async def _get_approvals() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
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
async def list_approvals() -> list[dict[str, Any]]:
    return await _get_approvals()


@app.post(f"{API_PREFIX}/approvals/{{idx}}/approve")
async def approve_proposal(idx: int) -> dict[str, str]:
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
async def deny_proposal(idx: int) -> dict[str, str]:
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
async def list_adapters() -> list[dict[str, Any]]:
    table: list[dict[str, Any]] = []
    if adapter_manager is None:
        return table
    try:
        for role, entry in adapter_manager.state.items():  # type: ignore
            table.append(
                {
                    "role": role,
                    "champion": entry.get("active") or "",
                    "challenger": entry.get("challenger") or "",
                }
            )
    except Exception:
        pass
    return table


@app.get(f"{API_PREFIX}/adapters/state")
async def adapters_state() -> dict[str, Any]:
    if adapter_manager is None:
        return {"state": {}}
    try:
        return {"state": adapter_manager.state}  # type: ignore
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/adapters/promote/{{role}}")
async def promote_adapter(role: str) -> dict[str, Any]:
    if adapter_manager is None:
        return {"error": "Adapter manager unavailable"}
    try:
        new_active = adapter_manager.promote_challenger(role)  # type: ignore
        return {"role": role, "new_active": new_active}
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/config/governor")
async def get_governor() -> dict[str, Any]:
    if settings is None:
        return {"ENABLE_ORACLE_REFINEMENT": None, "FORCE_DEEPSEEK_R1_ARBITER": None}
    try:
        return {
            "ENABLE_ORACLE_REFINEMENT": bool(getattr(settings, "ENABLE_ORACLE_REFINEMENT", False)),
            "FORCE_DEEPSEEK_R1_ARBITER": bool(
                getattr(settings, "FORCE_DEEPSEEK_R1_ARBITER", False)
            ),
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/config/governor")
async def update_governor(cfg: dict[str, Any]) -> dict[str, str]:
    global settings
    if settings is None:
        return {"error": "Settings unavailable"}
    try:
        enable_val = cfg.get("ENABLE_ORACLE_REFINEMENT")
        force_val = cfg.get("FORCE_DEEPSEEK_R1_ARBITER")
        if enable_val is None and "enabled" in cfg:
            enable_val = cfg["enabled"]
        if force_val is None and "force_deepseek_r1" in cfg:
            force_val = cfg["force_deepseek_r1"]
        # Legacy support for old GPT-4o parameter name
        if force_val is None and "force_gpt4o" in cfg:
            force_val = cfg["force_gpt4o"]
        if enable_val is not None:
            settings.ENABLE_ORACLE_REFINEMENT = bool(enable_val)  # type: ignore
            _env_write("ENABLE_ORACLE_REFINEMENT", "true" if bool(enable_val) else "false")
        if force_val is not None:
            settings.FORCE_DEEPSEEK_R1_ARBITER = bool(force_val)  # type: ignore
            _env_write("FORCE_DEEPSEEK_R1_ARBITER", "true" if bool(force_val) else "false")
        return {"status": "updated"}
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/trust/policy")
async def get_trust_policy() -> dict[str, Any]:
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
async def set_trust_policy(cfg: dict[str, Any]) -> dict[str, Any]:
    global settings, confidence_modeler
    if settings is None or ConfidenceModeler is None or TrustPolicy is None:
        return {"error": "Trust module unavailable"}
    try:
        if "enabled" in cfg:
            settings.TRUSTED_AUTONOMY_ENABLED = bool(cfg["enabled"])  # type: ignore
            _env_write(
                "TRUSTED_AUTONOMY_ENABLED", "true" if settings.TRUSTED_AUTONOMY_ENABLED else "false"
            )
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
        allow_t = tuple(
            [s.strip() for s in (settings.TRUST_ALLOWLIST or "").split(",") if s.strip()]
        )  # type: ignore
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
async def trust_score(proposal: dict[str, Any]) -> dict[str, Any]:
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
async def delegate_task(task_data: dict[str, Any]) -> dict[str, Any]:
    """Task Delegation API: Allows one LIQUID-HIVE instance to offload sub-tasks to others.
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
async def swarm_status() -> dict[str, Any]:
    """Get swarm coordination status and node information."""
    try:
        from hivemind.swarm_protocol import get_swarm_coordinator

        swarm = await get_swarm_coordinator()
        if not swarm:
            return {"swarm_enabled": False, "reason": "coordinator_unavailable"}

        # Get swarm state
        if swarm.redis_client:
            nodes_data_any: Any = cast(Any, swarm.redis_client).hgetall("swarm:nodes")
            nodes_data: dict[str, Any]
            if asyncio.iscoroutine(nodes_data_any):  # type: ignore[attr-defined]
                nodes_data = await nodes_data_any  # type: ignore[assignment]
            else:
                nodes_data = cast(dict[str, Any], nodes_data_any)
            nodes: list[dict[str, Any]] = []
            for _node_id, node_json in nodes_data.items():
                try:
                    if isinstance(node_json, str):
                        node_info = json.loads(node_json)
                    elif isinstance(node_json, dict):
                        node_info = cast(dict[str, Any], node_json)
                    else:
                        continue
                    if isinstance(node_info, dict):
                        nodes.append(cast(dict[str, Any], node_info))
                except Exception:
                    continue

            return {
                "swarm_enabled": True,
                "node_id": swarm.node_id,
                "active_nodes": len(nodes),
                "nodes": nodes,
                "active_tasks": len(swarm.active_tasks),
                "capabilities": swarm.capabilities,
            }
        else:
            return {"swarm_enabled": False, "reason": "redis_unavailable"}

    except Exception as exc:
        return {"swarm_enabled": False, "error": str(exc)}


@app.get(f"{API_PREFIX}/providers")
async def get_providers_status() -> dict[str, Any]:
    """Get status of all DS-Router providers."""
    if ds_router is None:
        return {"error": "DS-Router not available"}

    try:
        provider_status = await ds_router.get_provider_status()
        return {
            "providers": provider_status,
            "router_active": True,
            "timestamp": asyncio.get_event_loop().time(),
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/admin/budget/reset")
async def reset_budget() -> dict[str, Any]:
    """Reset daily budget counters (Admin only)."""
    admin_token = os.environ.get("ADMIN_TOKEN")
    if not admin_token:
        return {"error": "Admin token not configured"}

    # Reset using the enhanced distributed budget tracker
    if ds_router is not None and hasattr(ds_router, "_budget_tracker"):
        result = await ds_router._budget_tracker.reset_daily_budget()
        return {"status": "budget_reset", "details": result}
    else:
        return {"error": "Router or budget tracker not available"}


@app.post(f"{API_PREFIX}/admin/router/reload-secrets")
async def reload_router_secrets(request: Request) -> dict[str, Any]:
    """Reload DS-Router config from environment after secrets update.

    Requires x-admin-token header if ADMIN_TOKEN is configured.
    """
    try:
        admin_token = os.environ.get("ADMIN_TOKEN")
        if admin_token:
            header_token = request.headers.get("x-admin-token") or request.headers.get(
                "X-Admin-Token"
            )
            if header_token != admin_token:
                return {"error": "Unauthorized"}

        if ds_router is None:
            return {"error": "DS-Router not available"}
        # DSRouter exposes refresh_config_from_env()
        if hasattr(ds_router, "refresh_config_from_env"):
            ds_router.refresh_config_from_env()  # type: ignore
            return {"status": "reloaded"}
        else:
            return {"error": "Reload not supported in this build"}
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/admin/providers/qwen/warm")
async def warm_qwen_provider(request: Request) -> dict[str, Any]:
    """Warm the Qwen CPU provider by initializing its local model.

    Requires x-admin-token header if ADMIN_TOKEN is configured.
    This triggers the Qwen provider to load its tokenizer/model pipeline in a thread,
    so subsequent requests won't incur the cold-start cost.
    """
    try:
        admin_token = os.environ.get("ADMIN_TOKEN")
        if admin_token:
            header_token = request.headers.get("x-admin-token") or request.headers.get(
                "X-Admin-Token"
            )
            if header_token != admin_token:
                return {"error": "Unauthorized"}

        if ds_router is None:
            return {"error": "DS-Router not available"}

        # Locate Qwen CPU provider
        qwen: Any = None
        try:
            qwen = cast(Any, ds_router.providers.get("qwen_cpu"))  # type: ignore[attr-defined]
        except Exception:
            qwen = None

        if not qwen:
            return {"error": "Qwen CPU provider not configured"}

        # If provider already loaded, return early
        is_loaded = getattr(qwen, "is_loaded", False)
        model_name = getattr(qwen, "model_name", None)
        if is_loaded:
            return {"status": "already_loaded", "provider": "qwen_cpu", "model": model_name}

        # Trigger private initialize method in executor to avoid blocking event loop
        init_fn = getattr(qwen, "_initialize_model", None)
        if not callable(init_fn):
            return {"error": "Warm not supported for this provider build"}

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, init_fn)

        # Re-check state
        is_loaded = getattr(qwen, "is_loaded", False)
        load_error = getattr(qwen, "load_error", None)
        return {
            "status": "warmed" if is_loaded else "failed",
            "provider": "qwen_cpu",
            "model": getattr(qwen, "model_name", None),
            "error": None if is_loaded else load_error,
        }
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/tools")
async def list_tools() -> dict[str, Any]:
    """Get list of all available tools."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    return {
        "tools": tool_registry.get_all_schemas(),
        "categories": tool_registry.get_tools_by_category(),
        "high_risk": tool_registry.get_high_risk_tools(),
        "approval_required": tool_registry.get_approval_required_tools(),
        "total_count": len(tool_registry.tools),
    }


@app.get(f"{API_PREFIX}/tools/{{tool_name}}")
async def get_tool_schema(tool_name: str) -> dict[str, Any]:
    """Get schema for a specific tool."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    schema = tool_registry.get_tool_schema(tool_name)
    if schema is None:
        return {"error": f"Tool '{tool_name}' not found"}

    return schema


# -----------------------------
# Semantic Cache HTTP Endpoints
# -----------------------------


@app.get(f"{API_PREFIX}/cache/health")
async def cache_health() -> dict[str, Any]:
    """Health status for the semantic cache."""
    try:
        if semantic_cache is None:
            return {"error": "Semantic cache not available"}
        return await semantic_cache.health_check()  # type: ignore[func-returns-value]
    except Exception as exc:
        return {"error": str(exc)}


@app.get(f"{API_PREFIX}/cache/analytics")
async def cache_analytics() -> dict[str, Any]:
    """Analytics snapshot for the semantic cache."""
    try:
        if semantic_cache is None:
            return {"error": "Semantic cache not available"}
        return await semantic_cache.get_analytics()  # type: ignore[func-returns-value]
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/cache/clear")
async def cache_clear(request: Request, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Clear semantic cache entries. Optional body: { "pattern": "substring" }

    If ADMIN_TOKEN is set, requires X-Admin-Token header.
    """
    try:
        # Check authorization first
        admin_token = os.environ.get("ADMIN_TOKEN")
        if admin_token:
            header_token = request.headers.get("x-admin-token") or request.headers.get(
                "X-Admin-Token"
            )
            if header_token != admin_token:
                return {"error": "Unauthorized"}

        if semantic_cache is None:
            return {"error": "Semantic cache not available"}

        pattern = None
        if payload:
            p = payload.get("pattern")
            if isinstance(p, str):
                pattern = p

        result = await semantic_cache.clear_cache(pattern)  # type: ignore[func-returns-value]
        return result
    except Exception as exc:
        return {"error": str(exc)}


@app.post(f"{API_PREFIX}/tools/{{tool_name}}/execute")
async def execute_tool(
    tool_name: str, parameters: dict[str, Any], request: Request
) -> dict[str, Any]:
    """Execute a tool with given parameters."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    # Get operator ID from request if available
    operator_id = request.headers.get("X-Operator-ID")

    # Check if tool requires approval
    tool = tool_registry.get_tool(tool_name)
    if tool and tool.requires_approval:
        # Enhanced approval check
        approval_status = await check_tool_approval(tool_name, parameters, operator_id)
        if not approval_status["approved"]:
            return {
                "error": f"Tool '{tool_name}' requires approval",
                "approval_required": True,
                "approval_id": approval_status.get("approval_id"),
                "risk_level": tool.risk_level,
                "reason": approval_status.get("reason"),
            }

    # Execute the tool with enhanced tracking
    result = await tool_registry.execute_tool(tool_name, parameters, operator_id)
    return result.to_dict()


async def check_tool_approval(
    tool_name: str, parameters: dict[str, Any], operator_id: str | None
) -> dict[str, Any]:
    """Check tool approval status."""
    # This would integrate with your approval system
    # For now, return mock approval check
    return {
        "approved": False,
        "reason": "Tool requires operator approval due to security requirements",
    }


@app.get(f"{API_PREFIX}/tools/analytics")
async def get_tool_analytics() -> dict[str, Any]:
    """Get comprehensive tool analytics."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    return tool_registry.get_tool_analytics()


@app.get(f"{API_PREFIX}/tools/analytics/{{tool_name}}")
async def get_tool_analytics_specific(tool_name: str, days: int = 7) -> dict[str, Any]:
    """Get analytics for a specific tool."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    return tool_registry.get_tool_analytics(tool_name, days)


@app.get(f"{API_PREFIX}/tools/approvals")
async def get_pending_approvals() -> dict[str, Any]:
    """Get pending tool execution approvals."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    return {
        "pending_approvals": tool_registry.get_pending_approvals(),
        "approval_history": tool_registry.approval_history[-20:],  # Last 20 approvals
    }


@app.post(f"{API_PREFIX}/tools/approvals/{{approval_id}}/approve")
async def approve_tool_execution(approval_id: str, request: Request) -> dict[str, Any]:
    """Approve a pending tool execution."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    approver_id = request.headers.get("X-Operator-ID", "unknown")

    success = tool_registry.approve_tool_execution(approval_id, approver_id)

    if success:
        return {"status": "approved", "approval_id": approval_id, "approved_by": approver_id}
    else:
        return {"error": f"Approval {approval_id} not found or already processed"}


@app.post(f"{API_PREFIX}/tools/approvals/{{approval_id}}/deny")
async def deny_tool_execution(
    approval_id: str, request: Request, denial_reason: str = ""
) -> dict[str, Any]:
    """Deny a pending tool execution."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    approver_id = request.headers.get("X-Operator-ID", "unknown") if request else "unknown"

    success = tool_registry.deny_tool_execution(approval_id, approver_id, denial_reason)

    if success:
        return {"status": "denied", "approval_id": approval_id, "denied_by": approver_id}
    else:
        return {"error": f"Approval {approval_id} not found or already processed"}


@app.get(f"{API_PREFIX}/cache/status")
async def get_cache_status() -> dict[str, Any]:
    """Get semantic cache status and analytics."""
    if not semantic_cache:
        return {"status": "disabled", "reason": "Semantic cache not initialized"}

    try:
        analytics = await semantic_cache.get_analytics()
        health = await semantic_cache.health_check()

        return {
            "status": "enabled" if semantic_cache.is_ready else "error",
            "health": health,
            "analytics": analytics,
            "timestamp": datetime.now(datetime.timezone.utc).isoformat(),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get(f"{API_PREFIX}/cache/report")
async def get_cache_report() -> dict[str, Any]:
    """Get comprehensive cache performance report."""
    if not cache_manager:
        return {"error": "Cache manager not available"}

    try:
        report = await cache_manager.cache_statistics_report()
        return {"report": report}
    except Exception as e:
        return {"error": str(e)}

    # Note: POST /cache/clear is defined earlier with admin-token guard


@app.post(f"{API_PREFIX}/cache/optimize")
async def optimize_cache(target_hit_rate: float = 0.5) -> dict[str, Any]:
    """Optimize cache settings for better performance."""
    if not cache_manager:
        return {"error": "Cache manager not available"}

    try:
        if target_hit_rate < 0.1 or target_hit_rate > 0.9:
            return {"error": "Target hit rate must be between 0.1 and 0.9"}

        result = await cache_manager.optimize_cache_settings(target_hit_rate)
        return result
    except Exception as e:
        return {"error": str(e)}


@app.post(f"{API_PREFIX}/cache/warm")
async def warm_cache() -> dict[str, Any]:
    """Warm the cache with common queries."""
    if not cache_manager:
        return {"error": "Cache manager not available"}

    try:
        # Use some default queries for warming
        common_queries: list[dict[str, Any]] = [
            {
                "query": "What is artificial intelligence?",
                "response": {
                    "answer": "Artificial Intelligence (AI) is a branch of computer science that focuses on creating systems capable of performing tasks that typically require human intelligence, such as learning, reasoning, problem-solving, and understanding natural language.",
                    "provider": "cache_warming",
                },
            },
            {
                "query": "How does machine learning work?",
                "response": {
                    "answer": "Machine learning works by using algorithms to analyze data, identify patterns, and make predictions or decisions without being explicitly programmed for each specific task. It involves training models on data so they can learn and improve their performance over time.",
                    "provider": "cache_warming",
                },
            },
            {
                "query": "Explain neural networks",
                "response": {
                    "answer": "Neural networks are computing systems inspired by biological neural networks. They consist of interconnected nodes (neurons) organized in layers that process information by passing signals through weighted connections. They can learn patterns in data through training.",
                    "provider": "cache_warming",
                },
            },
        ]
        result = await cache_manager.warm_cache(common_queries)
        return result

    except Exception as e:
        return {"error": str(e)}

    # Note: GET /cache/health is defined earlier


@app.get(f"{API_PREFIX}/tools/health")
async def get_tools_health() -> dict[str, Any]:
    """Get health status of all tools."""
    if tool_registry is None:
        return {"error": "Tool registry not available"}

    health_status = {}
    total_tools = len(tool_registry.tools)
    healthy_tools = 0

    for tool_name, tool in tool_registry.tools.items():
        try:
            # Basic health check - could be enhanced
            health_status[tool_name] = {
                "status": "healthy",
                "category": tool.category,
                "risk_level": tool.risk_level,
                "requires_approval": tool.requires_approval,
                "version": tool.version,
            }
            healthy_tools += 1
        except Exception as e:
            health_status[tool_name] = {"status": "unhealthy", "error": str(e)}

    return {
        "overall_health": "healthy" if healthy_tools == total_tools else "degraded",
        "healthy_tools": healthy_tools,
        "total_tools": total_tools,
        "tools": health_status,
    }


@app.post(f"{API_PREFIX}/tools/batch_execute")
async def batch_execute_tools(requests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Execute multiple tools in sequence."""
    if tool_registry is None:
        return [{"error": "Tool registry not available"}]

    results: list[dict[str, Any]] = []
    for request in requests:
        tool_name = request.get("tool")
        parameters = request.get("parameters", {})

        if not tool_name:
            results.append({"error": "Missing tool name in request"})
            continue

        # Check approval requirement
        tool = tool_registry.get_tool(tool_name)
        if tool and tool.requires_approval:
            results.append({"error": f"Tool '{tool_name}' requires operator approval"})
            continue

        # Execute
        result = await tool_registry.execute_tool(tool_name, parameters)
        results.append(result.to_dict())

    return results


@app.post(f"{API_PREFIX}/admin/router/set-thresholds")
async def set_router_thresholds(request: Request, thresholds: dict[str, float]) -> dict[str, Any]:
    """Set router confidence and support thresholds (Admin only)."""
    admin_token = os.environ.get("ADMIN_TOKEN")
    if admin_token:
        header_token = request.headers.get("x-admin-token") or request.headers.get("X-Admin-Token")
        if header_token != admin_token:
            return {"error": "Unauthorized"}

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
                "max_cot_tokens": ds_router.config.max_cot_tokens,
            },
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
    out: list[dict[str, Any]] = []
    # Build a representative prompt from recent user inputs to estimate costs
    representative_prompt = ""
    try:
        if engine is not None:
            user_msgs = [
                m.get("content", "") for m in list(engine.memory)[-200:] if m.get("role") == "user"
            ]  # type: ignore
            snippet = "\n".join(user_msgs[-5:])
            representative_prompt = snippet[:2000]
    except Exception:
        representative_prompt = "Evaluate adapter performance under typical conversational load."

    for role, entry in getattr(adapter_manager, "state", {}).items():  # type: ignore
        entry_map: dict[str, Any] = cast(dict[str, Any], (entry or {}))
        active = cast(str | None, entry_map.get("active"))
        challenger = cast(str | None, entry_map.get("challenger"))
        if not (active and challenger and active != challenger):
            continue
        r_active = (
            _scalar(
                _prom_q(
                    base, f'sum(rate(cb_requests_total{{adapter_version="{active}"}}[{window}]))'
                )
            )
            or 0.0
        )
        r_chall = (
            _scalar(
                _prom_q(
                    base,
                    f'sum(rate(cb_requests_total{{adapter_version="{challenger}"}}[{window}]))',
                )
            )
            or 0.0
        )
        if (r_active * 300) < min_samples or (r_chall * 300) < min_samples:
            continue
        p95_a = (
            _scalar(
                _prom_q(
                    base,
                    f'histogram_quantile(0.95, sum(rate(cb_request_latency_seconds_bucket{{adapter_version="{active}"}}[{window}])) by (le))',
                )
            )
            or 9e9
        )
        p95_c = (
            _scalar(
                _prom_q(
                    base,
                    f'histogram_quantile(0.95, sum(rate(cb_request_latency_seconds_bucket{{adapter_version="{challenger}"}}[{window}])) by (le))',
                )
            )
            or 9e9
        )
        try:
            cost_small = (
                resource_estimator.estimate_cost("implementer", "small", representative_prompt)
                if resource_estimator
                else {"predicted_cost_small": 1.0}
            )
            cost_large = (
                resource_estimator.estimate_cost("implementer", "large", representative_prompt)
                if resource_estimator
                else {"predicted_cost_large": 1.0}
            )
        except Exception:
            cost_small = {"predicted_cost_small": 1.0}
            cost_large = {"predicted_cost_large": 1.0}
        better_latency = p95_c <= (p95_a * 0.9)
        better_cost = (cost_large.get("predicted_cost_large", 1.0)) <= (
            cost_small.get("predicted_cost_small", 1.0)
        )
        if better_latency or better_cost:
            out.append(
                {
                    "role": role,
                    "active": active,
                    "challenger": challenger,
                    "p95_a": p95_a,
                    "p95_c": p95_c,
                    "predicted_cost_small": cost_small.get("predicted_cost_small"),
                    "predicted_cost_large": cost_large.get("predicted_cost_large"),
                    "reason": "latency" if better_latency else "cost",
                }
            )
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
            await asyncio.sleep(10)  # Or listen to engine.bus for immediate events
            try:
                if engine is not None:
                    summary = engine.get_state_summary()
                    await websocket.send_json({"type": "state_update", "payload": summary})

                    approvals = await _get_approvals()
                    await websocket.send_json({"type": "approvals_update", "payload": approvals})

                    # --- Add custom events here ---
                    # Example: Get recent self_extension memories
                    recent_autonomy_events = [
                        m
                        for m in list(engine.memory)[-50:]
                        if m.get("role") in ["self_extension", "approval_feedback"]
                    ]
                    if recent_autonomy_events:
                        await websocket.send_json(
                            {"type": "autonomy_events_recent", "payload": recent_autonomy_events}
                        )

                    # RAG system status
                    if retriever is not None:
                        rag_status: dict[str, Any] = {
                            "is_ready": retriever.is_ready,
                            "doc_count": len(retriever.doc_store) if retriever.doc_store else 0,
                            "embedding_model": retriever.embed_model_id,
                        }
                        await websocket.send_json({"type": "rag_status", "payload": rag_status})

                    # Enhanced Oracle/Arbiter system status (DeepSeek R1 ecosystem)
                    oracle_status: dict[str, Any] = {
                        "deepseek_available": bool(os.getenv("DEEPSEEK_API_KEY")),
                        "deepseek_r1_arbiter": bool(
                            os.getenv("DEEPSEEK_API_KEY")
                        ),  # R1 for reasoning
                        "unified_ecosystem": True,  # All DeepSeek, no mixed APIs
                        "refinement_enabled": (
                            getattr(settings, "ENABLE_ORACLE_REFINEMENT", False)
                            if settings
                            else False
                        ),
                        "cost_advantage": "70% cheaper than GPT-4o",
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
        import pathlib
        import subprocess
        import uuid as _uuid

        base = pathlib.Path(settings.adapters_dir if settings else "/app/adapters")  # type: ignore
        out_dir = base / "text" / f"adapter_{_uuid.uuid4().hex}"
        out_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "hivemind.training.sft_text",
                "--out",
                str(out_dir),
            ],
            check=True,
        )
        if settings is not None:
            settings.text_adapter_path = str(out_dir)
        return {"status": "success", "adapter_path": str(out_dir)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.post(f"{API_PREFIX}/chat")
async def chat(q: str, request: Request) -> dict[str, Any]:
    q = sanitize_input(q)
    if engine is None:
        return {"answer": "Engine not ready"}

    # Step 1: Check semantic cache first
    if semantic_cache and semantic_cache.is_ready:
        try:
            cached_response = await semantic_cache.get(q)
            if cached_response:
                # Return cached response with cache metadata
                cached_response["cached"] = True
                cached_response["cache_timestamp"] = time.time()
                return cached_response
        except Exception as e:
            log.warning(f"Semantic cache check failed: {e}")

    # Continue with normal processing if no cache hit
    if engine is not None:
        engine.add_memory("user", q)  # type: ignore

    planner_hints = None
    reasoning_steps = None
    # Use planner only when explicitly enabled
    use_planner = str(os.getenv("ENABLE_PLANNER", "false")).lower() == "true"
    if use_planner and plan_once is not None:
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
            docs = await retriever.search(q, k=5)  # type: ignore[operator]
            if hasattr(retriever, "format_context"):
                context_txt = str(retriever.format_context(docs))  # type: ignore[operator]
            else:
                context_txt = ""
            prompt = (
                f"[CONTEXT]\n{context_txt}\n\n"
                f"[QUESTION]\n{q}\n\n"
                "Cite using [#]. If not in context, say 'Not in context'."
            )
        except Exception:
            prompt = q

    answer = "Placeholder: HiveMind unavailable"
    provider_used = None
    confidence = None
    escalated = False

    # Use DS-Router if available, otherwise fallback to legacy routing
    if ds_router is not None and GenRequest is not None:
        try:
            # Create DS-Router request
            GenRequestAny = GenRequest  # type: ignore[assignment]
            gen_request: Any = GenRequestAny(
                prompt=prompt,
                system_prompt="You are a helpful AI assistant. Provide accurate and helpful responses.",
                max_tokens=(getattr(settings, "max_new_tokens", 512) if settings else 512),
                temperature=0.7,
            )

            # Generate using DS-Router
            gen_response: Any = await ds_router.generate(gen_request)  # type: ignore[operator]

            answer = gen_response.content
            provider_used = gen_response.provider
            confidence = gen_response.confidence
            escalated = gen_response.metadata.get("escalated", False)

            # Add routing info to request scope for metrics
            request.scope["provider_used"] = provider_used
            request.scope["router_confidence"] = confidence
            request.scope["escalated"] = escalated

        except Exception as exc:
            answer = f"Error with DS-Router: {exc}. Falling back to legacy routing."

    # Legacy routing fallback if DS-Router not available or failed
    if provider_used is None:
        policy_used = None
        roles_obj: Any = text_roles if text_roles is not None else None
        decision: dict[str, Any] | None = None
        try:
            routing = bool(getattr(settings, "MODEL_ROUTING_ENABLED", False)) if settings else False
            chosen_model = None
            ctx: dict[str, Any] = {}
            if resource_estimator is not None:
                try:
                    ctx["estimated_cost"] = resource_estimator.estimate_cost("implementer", "large")  # type: ignore[operator]
                except Exception:
                    pass
            if intent_modeler is not None:
                try:
                    ctx["operator_intent"] = intent_modeler.current_intent  # type: ignore[assignment]
                except Exception:
                    pass
            if engine is not None:
                try:
                    ctx["phi"] = (
                        engine.get_state_summary().get("self_awareness_metrics", {}).get("phi")
                    )  # type: ignore[operator]
                except Exception:
                    pass
            ctx["planner_hints"] = planner_hints or []
            ctx["reasoning_steps"] = reasoning_steps or ""
            # Cognitive map snapshot (if available)
            try:
                import json as __json
                import pathlib as __pathlib

                runs_dir = getattr(settings, "runs_dir", "/app/data") if settings else "/app/data"
                snap_path = __pathlib.Path(runs_dir) / "cognitive_map.json"
                if snap_path.exists():
                    with open(snap_path, encoding="utf-8") as __f:
                        ctx["cognitive_map"] = __json.load(__f)
            except Exception:
                pass
            if strategy_selector is not None:
                try:
                    decision = await strategy_selector.decide(prompt, ctx)  # type: ignore[operator]
                    policy_used = decision.get("strategy") if decision else None
                    if decision and decision.get("reason"):
                        request.scope["selector_reason"] = decision["reason"]
                    chosen_model = decision.get("model") if decision else None
                    if decision and decision.get("chosen_model"):
                        request.scope["chosen_model_alias"] = decision["chosen_model"]
                except Exception:
                    decision = None
            if routing:
                if not chosen_model:
                    short = len(q) < 160 and not context_txt
                    chosen_model = "small" if short else "large"
                # chosen_model from selector: "small" or "large" mapped to Courier/Master alias in request.scope
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
                roles_any = roles_obj  # type: ignore[assignment]
                judge_any = judge  # type: ignore[assignment]
                if policy == "committee":
                    tasks: list[str] = await asyncio.gather(
                        *[roles_any.implementer(prompt) for _ in range(settings.committee_k)]
                    )
                    rankings = await judge_any.rank(tasks, prompt=prompt)
                    answer = judge_any.merge(tasks, rankings)
                elif policy == "debate":
                    a1 = await roles_any.architect(prompt)
                    a2 = await roles_any.implementer(prompt)
                    rankings = await judge_any.rank([a1, a2], prompt=prompt)
                    answer = judge_any.select([a1, a2], rankings)
                elif policy == "ethical_deliberation":
                    # Ethical Synthesizer: Handle ethical dilemmas
                    if engine is not None:
                        ethical_analysis_raw: Any = (
                            decision.get("ethical_analysis", {}) if decision else {}
                        )
                        ethical_analysis: dict[str, Any] = cast(
                            dict[str, Any],
                            ethical_analysis_raw if isinstance(ethical_analysis_raw, dict) else {},
                        )
                        dilemma_type: str = str(ethical_analysis.get("dilemma_type", "unknown"))
                        severity: str = str(ethical_analysis.get("severity", "medium"))
                        detected_raw: Any = ethical_analysis.get("all_detected", [])
                        if not isinstance(detected_raw, list | tuple):
                            detected_raw = []
                        detected_list_any: list[Any] = (
                            list(detected_raw) if isinstance(detected_raw, list | tuple) else []
                        )  # type: ignore[list-item]
                        detected_list: list[str] = [str(x) for x in detected_list_any]

                        # Create ethical deliberation proposal
                        ethical_proposal = f"""ETHICAL DILEMMA DETECTED: {dilemma_type.upper()}
Severity: {severity}
Original Query: {q}
Detected Issues: {", ".join(detected_list)}

This query has been flagged for ethical review. Please provide guidance on how to respond appropriately while maintaining ethical standards. [action:ethical_review]"""

                        # Add to approval queue instead of answering directly
                        engine.add_memory("approval", ethical_proposal)
                        answer = f"This request requires ethical review due to potential {dilemma_type} concerns. It has been submitted for operator guidance."
                        request.scope["ethical_flag"] = True
                        request.scope["dilemma_type"] = dilemma_type
                    else:
                        answer = "This request contains potentially sensitive content and cannot be processed automatically."
                elif policy == "clone_dispatch":
                    answer = await roles_any.implementer(prompt)
                elif policy == "self_extension_prompt":
                    answer = "Self‑extension requests are not supported by this endpoint"
                elif policy == "cross_modal_synthesis":
                    img_desc = context_txt if context_txt else None
                    try:
                        answer = await roles_any.fusion_agent(prompt, image_description=img_desc)
                    except Exception as exc:
                        answer = f"Error generating cross‑modal answer: {exc}"
                else:
                    answer = await roles_any.implementer(prompt)

                provider_used = "legacy_routing"
            except httpx.RequestError as exc:
                answer = f"Error communicating with the model endpoint: {exc}"
            except (KeyError, IndexError) as exc:
                answer = f"Error processing model response or policy: {exc}"
            except Exception as exc:
                answer = f"An unexpected error occurred during answer generation: {exc}"

    if engine is not None:
        engine.add_memory("assistant", answer)  # type: ignore

    try:
        if text_roles is not None and hasattr(text_roles, "c"):
            client = text_roles.c  # type: ignore[attr-defined]
            adapter_version = getattr(client, "current_adapter_version", None)
            if adapter_version:
                request.scope["adapter_version"] = adapter_version
    except Exception:
        pass

    result: dict[str, Any] = {"answer": answer}

    # Add DS-Router specific information
    if provider_used:
        result["provider"] = provider_used
    if confidence is not None:
        result["confidence"] = confidence
    if escalated:
        result["escalated"] = escalated

    # Legacy information
    try:
        sr = request.scope.get("selector_reason")
        if sr:
            result["selector_reason"] = sr
        cm = request.scope.get("chosen_model_alias")
        if cm:
            result["chosen_model"] = cm
    except Exception:
        pass
    if context_txt:
        result["context"] = context_txt
    if planner_hints:
        result["planner_hints"] = planner_hints  # type: ignore
    if reasoning_steps:
        result["reasoning_steps"] = reasoning_steps  # type: ignore

    # Step: Cache the response for future similar queries
    sc_ready = (
        bool(getattr(semantic_cache, "is_ready", False)) if semantic_cache is not None else False
    )
    if sc_ready and not result.get("cached"):
        try:
            # Only cache successful responses
            if result.get("answer") and not result.get("error"):
                cache_context: dict[str, Any] = {
                    "provider": provider_used,
                    "has_context": bool(context_txt),
                    "query_length": len(q),
                }

                await cast(Any, semantic_cache).set(q, result, context=cache_context)
                log.debug(f"Cached response for query: {q[:50]}...")

        except Exception as e:
            log.warning(f"Failed to cache response: {e}")

    return result


@app.post(f"{API_PREFIX}/vision")
async def vision(
    request: Request, question: str, file: UploadFile = File(...), grounding_required: bool = False
):
    if engine is None:
        return {"answer": "Engine not ready"}
    if vl_roles is None or judge is None:
        return {"answer": "Vision pipeline unavailable"}
    image_data = await file.read()
    if engine is not None:
        engine.add_memory("user", question)  # type: ignore
    answer: str = "Vision processing unavailable"
    critique: str | None = None
    grounding: dict[str, Any] | None = None
    try:
        vl_any = vl_roles  # type: ignore[assignment]
        judge_any = judge  # type: ignore[assignment]
        candidates = await vl_any.vl_committee(question, image_data, k=2)  # type: ignore[operator]
        rankings = await judge_any.rank_vision(question, image_data, candidates)  # type: ignore[operator]
        wid = int(rankings.get("winner_id", 0))
        answer = candidates[wid] if 0 <= wid < len(candidates) else candidates[0]
        critique = rankings.get("critique")
        if grounding_required:
            grounding = vl_any.grounding_validator(question, image_data, answer)
    except Exception as exc:
        answer = f"Error processing vision request: {exc!s}"
    if engine is not None:
        engine.add_memory("assistant", answer)  # type: ignore
    try:
        request.scope["adapter_version"] = "vl"
    except Exception:
        pass
    resp: dict[str, Any] = {"answer": answer}
    if critique:
        resp["critique"] = critique
    if grounding:
        resp["grounding"] = grounding


@app.websocket(f"{API_PREFIX}/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """Enhanced WebSocket endpoint for streaming chat responses."""
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            message = await websocket.receive_text()

            try:
                data = json.loads(message)
                query = data.get("q", "")
                stream_mode = data.get("stream", True)

                if not query:
                    await websocket.send_json({"type": "error", "error": "Query is required"})
                    continue

                # Sanitize input
                query = sanitize_input(query)

                # Add to engine memory
                if engine is not None:
                    engine.add_memory("user", query)  # type: ignore

                # Check semantic cache first
                cached_response = None
                sc_ready_ws = (
                    bool(getattr(semantic_cache, "is_ready", False))
                    if semantic_cache is not None
                    else False
                )  # type: ignore
                if sc_ready_ws:
                    try:
                        cached_response = await semantic_cache.get(query)  # type: ignore
                    except Exception as e:
                        log.warning(f"Cache check failed: {e}")

                if cached_response:
                    cached_dict: dict[str, Any] = cast(dict[str, Any], cached_response)
                    # Send cached response immediately
                    await websocket.send_json(
                        {
                            "type": "cached_response",
                            "content": cached_dict.get("answer", ""),
                            "metadata": {
                                "cached": True,
                                "cache_similarity": cached_dict.get("cache_similarity", 1.0),
                                "provider": cached_dict.get("provider", "cache"),
                            },
                        }
                    )

                    # Add to engine memory
                    if engine is not None:
                        engine.add_memory("assistant", cached_dict.get("answer", ""))  # type: ignore

                    # Send completion signal
                    await websocket.send_json({"type": "stream_complete"})
                    continue

                # No cache hit - generate streaming response
                if stream_mode and ds_router is not None and GenRequest is not None:
                    await _handle_streaming_generation(websocket, query)
                else:
                    # Fallback to non-streaming
                    await _handle_non_streaming_generation(websocket, query)

            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON message"})
            except Exception as e:
                await websocket.send_json({"type": "error", "error": f"Processing error: {e!s}"})

    except WebSocketDisconnect:
        log.info("WebSocket client disconnected from streaming chat")
    except Exception as e:
        log.error(f"WebSocket chat error: {e}")


async def _handle_streaming_generation(websocket: WebSocket, query: str):
    """Handle streaming generation using DS-Router."""
    try:
        # Prepare RAG context
        context_txt: str = ""
        enhanced_prompt: str = query

        if retriever is not None:
            try:
                docs = await retriever.search(query, k=5)  # type: ignore
                if hasattr(retriever, "format_context"):
                    context_txt = str(retriever.format_context(docs))  # type: ignore
                else:
                    # Fallback context formatting
                    context_txt = "\n\n".join(
                        [getattr(doc, "page_content", "")[:200] for doc in docs[:3]]
                    )

                enhanced_prompt = (
                    f"[CONTEXT]\n{context_txt}\n\n"
                    f"[QUESTION]\n{query}\n\n"
                    "Cite using [#]. If not in context, say 'Not in context'."
                )
            except Exception as e:
                log.warning(f"RAG retrieval failed: {e}")
                enhanced_prompt = query

        # Create streaming request
        GenRequestAny = cast(Any, GenRequest)
        gen_request: Any = GenRequestAny(
            prompt=enhanced_prompt,
            system_prompt="You are a helpful AI assistant. Provide accurate and helpful responses.",
            max_tokens=(getattr(settings, "max_new_tokens", 1024) if settings else 1024),
            temperature=0.7,
            stream=True,
        )

        # Send stream start notification
        await websocket.send_json(
            {
                "type": "stream_start",
                "metadata": {
                    "has_context": bool(context_txt),
                    "enhanced_prompt_length": len(enhanced_prompt),
                },
            }
        )

        # Stream response chunks
        accumulated_content: str = ""
        chunk_count: int = 0
        last_provider: str | None = None
        router_any = cast(Any, ds_router)
        async for chunk in router_any.generate_stream(gen_request):
            part: str = getattr(chunk, "content", "")
            accumulated_content += part
            chunk_count += 1
            last_provider = cast(
                str | None, getattr(chunk, "provider", last_provider or "ds_router_stream")
            )

            # Send chunk to client
            await websocket.send_json(
                {
                    "type": "chunk",
                    "content": part,
                    "chunk_id": getattr(chunk, "chunk_id", chunk_count),
                    "is_final": bool(getattr(chunk, "is_final", False)),
                    "provider": last_provider,
                    "metadata": {
                        **(getattr(chunk, "metadata", {}) or {}),
                        "accumulated_length": len(accumulated_content),
                        "total_chunks": chunk_count,
                    },
                }
            )

            if bool(getattr(chunk, "is_final", False)):
                break

        # Add complete response to engine memory
        if engine is not None and accumulated_content:
            engine.add_memory("assistant", accumulated_content)  # type: ignore

        # Cache the complete response
        if (
            semantic_cache is not None
            and bool(getattr(semantic_cache, "is_ready", False))
            and accumulated_content
        ):  # type: ignore
            try:
                response_to_cache: dict[str, Any] = {
                    "answer": accumulated_content,
                    "provider": last_provider or "ds_router_stream",
                    "context": context_txt if context_txt else None,
                    "streaming": True,
                }
                await semantic_cache.set(query, response_to_cache)  # type: ignore
                log.debug(f"Cached streaming response for: {query[:50]}...")
            except Exception as e:
                log.warning(f"Failed to cache streaming response: {e}")

        # Send completion signal
        await websocket.send_json(
            {
                "type": "stream_complete",
                "metadata": {
                    "total_chunks": chunk_count,
                    "total_length": len(accumulated_content),
                    "cached": True if semantic_cache else False,
                },
            }
        )

    except Exception as e:
        await websocket.send_json(
            {
                "type": "error",
                "error": f"Streaming generation failed: {e!s}",
            }
        )


async def _handle_non_streaming_generation(websocket: WebSocket, query: str):
    """Handle non-streaming generation as fallback."""
    try:
        # Use the existing chat logic but send as stream
        # This is a simplified version - you could enhance this further

        await websocket.send_json({"type": "stream_start", "metadata": {"fallback_mode": True}})

        # Generate response (simplified)
        response_content = "This is a fallback response when streaming is not available."

        # Send as single chunk
        await websocket.send_json(
            {
                "type": "chunk",
                "content": response_content,
                "chunk_id": 0,
                "is_final": True,
                "provider": "fallback",
                "metadata": {"non_streaming_fallback": True},
            }
        )

        await websocket.send_json({"type": "stream_complete"})

    except Exception as e:
        await websocket.send_json({"type": "error", "error": f"Fallback generation failed: {e!s}"})


# Mount GUI SPA (prefer frontend/dist, then frontend/build, fallback to legacy gui paths)
try:
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    candidates = [
        repo_root / "frontend" / "dist",
        repo_root / "frontend" / "build",
        repo_root / "gui" / "dist",
        repo_root / "gui" / "build",
    ]
    static_root = next((p for p in candidates if p.exists()), None)
    if static_root is not None:
        app.mount("/", StaticFiles(directory=str(static_root), html=True), name="gui")
except Exception:
    pass
