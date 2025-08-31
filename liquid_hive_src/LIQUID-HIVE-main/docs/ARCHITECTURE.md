# LIQUID-HIVE Final Architecture (Canonical)

This document is the single source of truth for the final, fused architecture of LIQUID-HIVE.

## Overview
LIQUID-HIVE operates in two complementary modes that together form a production-grade, self-improving cognitive system:

- Live Operations (Conscious State): DS-Router handles all real-time requests with safety, intelligent routing, and budget governance.
- Offline Evolution (Dreaming State): The Autonomy Orchestrator curates experiences, forges training data via the Arbiter pipeline, fine-tunes LoRA adapters, and proposes upgrades gated by a Trust policy and operator approvals.

All runtime APIs are served by FastAPI in unified_runtime/server.py and are prefixed with /api.

## Live Operations: DS-Router Path (Only Path)
- PreGuard and PostGuard enforce a safety sandwich around every request.
- Routing logic chooses between providers:
  - deepseek_chat for simple queries
  - deepseek_thinking for complex queries (limited CoT budget)
  - deepseek_r1 as an escalation target on low confidence
  - qwen_cpu as a deterministic local fallback
- BudgetTracker enforces daily token/credit caps with hard or warn modes.
- Audit logging records provider, confidence, filters, tokens, cost, and latency.

The /api/chat endpoint exclusively calls DSRouter.generate(). Any failure is handled by the router’s internal fallback chain; there is no legacy StrategySelector path anymore.

## Retrieval Augmentation
- Retriever enriches prompts with context when available: [CONTEXT] + [QUESTION] + citation instructions.
- RAG support can influence routing thresholds in future iterations.

## Offline Evolution: Autonomy Orchestrator
- Leader-elected singleton using Redis.
- Triggers dataset_build to create platinum targets through the Oracle/Arbiter pipeline (DeepSeek first, GPT-4o fallback when enabled).
- Launches fine-tuning (Unsloth + QLoRA) to produce challenger adapters.
- Uses Prometheus metrics and Welch’s t-test to evaluate challengers.
- Submits proposals to the Approval Queue for operator control.

## Trust and Confidence
- ConfidenceModeler estimates approval likelihood from historical events (Phase 1). Future work: incorporate embeddings, cost, and ethics signals.
- TrustPolicy sets threshold, minimum samples, and allowlist for autonomous actions.

## Observability
- MetricsMiddleware exposes cb_* metrics and latency histograms; Grafana dashboards provided.
- Provider health: /api/providers
- System health: /api/healthz

## Admin and Governance
- Governor flags: ENABLE_ORACLE_REFINEMENT, FORCE_GPT4O_ARBITER
- Router tuning: /api/admin/router/set-thresholds
- Budget reset: /api/admin/budget/reset
- Adapter lifecycle: /api/adapters, /api/adapters/promote/{role}

## Security
- sanitize_input protects /api/chat
- Secrets loaded via Settings; no .env committed.

## Key Environment Variables
- DEEPSEEK_API_KEY: enables DeepSeek providers
- HF_TOKEN: enables local Qwen CPU provider
- TRUSTED_AUTONOMY_ENABLED, TRUST_THRESHOLD, TRUST_MIN_SAMPLES, TRUST_ALLOWLIST
- PROMETHEUS_BASE_URL, redis_url, adapters_dir

## Testing Notes
- Unit test live routes using FastAPI TestClient; mock providers if external keys are absent.
- Vision flow available at /api/vision when VisionRoles and Judge are configured.