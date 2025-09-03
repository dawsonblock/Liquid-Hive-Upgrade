# Planner and DAG Executor

This repo includes a lightweight Planner module with a typed DAG schema (pydantic) and an async executor supporting concurrency, retries, timeouts, and fan-in/out. Enable via ENABLE_PLANNER=true.

- capsule_brain/planner/schema.py defines TaskNode and Plan, including cycle detection.
- capsule_brain/planner/engine.py implements PlanExecutor and a tiny NL helper plan_from_query.
- tests/test_planner.py covers cycle, retry, timeout, and fan-in/out cases.
