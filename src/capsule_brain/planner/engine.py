from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .schema import Plan, TaskNode
from src.logging_config import get_logger

ENABLE_PLANNER = str(__import__("os").environ.get("ENABLE_PLANNER", "false").lower()) == "true"


@dataclass
class NodeResult:
    node_id: str
    ok: bool
    value: Any
    attempts: int
    duration_ms: float
    error: str | None = None


class PlanExecutor:
    def __init__(self, plan: Plan):
        self.plan = plan
        self.results: dict[str, NodeResult] = {}
        self._ops: dict[str, Callable[[TaskNode, dict[str, NodeResult]], Awaitable[Any]]] = {
            "local_search": self._op_local_search,
            "calculator": self._op_calculator,
            "flaky": self._op_flaky,
            "sleep": self._op_sleep,
        }

    # ---------- Built-in Ops (safe, self-contained, no network) ----------
    async def _op_local_search(self, node: TaskNode, ctx: dict[str, NodeResult]) -> Any:
        # Simulate a local search by returning tokens referencing the query.
        q = str(node.params.get("query") or node.params.get("q") or "")
        await asyncio.sleep(min(0.02 + len(q) / 1000.0, 0.2))
        return {
            "query": q,
            "results": [f"Result about {w}" for w in q.split()[:5]],
            "source": "stub/local",
        }

    async def _op_calculator(self, node: TaskNode, ctx: dict[str, NodeResult]) -> Any:
        expr = str(node.params.get("expression") or node.params.get("expr") or "0")
        # Extremely restricted evaluator: only numbers and +-*/() and whitespace
        allowed = set("0123456789+-*/(). eE")
        if not set(expr) <= allowed:
            raise ValueError("Expression contains disallowed characters")
        # Replace common tokens
        expr = expr.replace("^", "**")
        # Safe eval context
        safe_globals = {"__builtins__": {}}
        safe_locals = {
            "pi": math.pi,
            "e": math.e,
        }
        try:
            # Use ast.literal_eval for safer evaluation of simple expressions
            import ast

            val = ast.literal_eval(expr)
        except (ValueError, SyntaxError):
            # Fallback to restricted eval for complex expressions
            try:
                val = eval(expr, safe_globals, safe_locals)  # nosec B307 - restricted eval with safe globals
            except Exception as e:
                return f"Error: {e}"
        except Exception as e:
            raise ValueError(f"Bad expression: {e}")
        return {"expression": expr, "value": float(val)}

    async def _op_flaky(self, node: TaskNode, ctx: dict[str, NodeResult]) -> Any:
        # Fails the first N times this node is executed; success afterwards
        # We use an in-memory counter on the node via params mutation (ok for tests)
        fail_n = int(node.params.get("fail_first", 0))
        current = int(node.params.get("_attempt", 0))
        node.params["_attempt"] = current + 1
        if current < fail_n:
            raise RuntimeError("flaky failure")
        return {"ok": True, "attempt": current + 1}

    async def _op_sleep(self, node: TaskNode, ctx: dict[str, NodeResult]) -> Any:
        ms = float(node.params.get("ms", 10))
        await asyncio.sleep(ms / 1000.0)
        return {"slept_ms": ms}

    # ---------- Execution ----------
    async def execute(
        self, *, max_concurrency: int = 8, fail_fast: bool = False
    ) -> dict[str, NodeResult]:
        start = time.perf_counter()
        # Topologically sort and schedule by dependency readiness
        pending: dict[str, TaskNode] = dict(self.plan.nodes)
        in_progress: dict[str, asyncio.Task] = {}
        sem = asyncio.Semaphore(max_concurrency)

        async def run_node(n: TaskNode):
            async with sem:
                attempts = 0
                node_start = time.perf_counter()
                last_err: str | None = None
                timeout = n.timeout_sec
                while True:
                    try:
                        attempts += 1
                        coro = self._dispatch(n)
                        if timeout and timeout > 0:
                            val = await asyncio.wait_for(coro, timeout=timeout)
                        else:
                            val = await coro
                        duration = (time.perf_counter() - node_start) * 1000.0
                        res = NodeResult(
                            node_id=n.id,
                            ok=True,
                            value=val,
                            attempts=attempts,
                            duration_ms=duration,
                        )
                        self.results[n.id] = res
                        return
                    except TimeoutError:
                        last_err = "timeout"
                    except Exception as e:
                        last_err = str(e)
                    if attempts > n.retries:
                        duration = (time.perf_counter() - node_start) * 1000.0
                        self.results[n.id] = NodeResult(
                            node_id=n.id,
                            ok=False,
                            value=None,
                            attempts=attempts,
                            duration_ms=duration,
                            error=last_err,
                        )
                        if fail_fast:
                            raise RuntimeError(f"Node {n.id} failed: {last_err}")
                        return

        def ready_to_run(n: TaskNode) -> bool:
            # All dependencies must exist in results and be ok
            return all((dep in self.results and self.results[dep].ok) for dep in n.depends_on)

        try:
            loop = asyncio.get_event_loop()
            while pending or in_progress:
                # Schedule ready tasks
                to_start = [n for n in list(pending.values()) if ready_to_run(n)]
                for n in to_start:
                    task = loop.create_task(run_node(n))
                    in_progress[n.id] = task
                    del pending[n.id]

                if not in_progress and pending:
                    # Deadlock: dependencies failed or cycle in runtime (should be prevented by validation)
                    # Mark remaining as failed due to unmet deps
                    for nid, n in list(pending.items()):
                        self.results[nid] = NodeResult(
                            nid, False, None, 0, 0.0, "unmet_dependencies"
                        )
                        del pending[nid]
                    break

                if in_progress:
                    done, _ = await asyncio.wait(
                        in_progress.values(), return_when=asyncio.FIRST_COMPLETED
                    )
                    # Remove done tasks
                    for t in list(done):
                        # map back to node id
                        done_nid = None
                        for nid, task in list(in_progress.items()):
                            if task is t:
                                done_nid = nid
                                break
                        if done_nid:
                            del in_progress[done_nid]
                else:
                    await asyncio.sleep(0.005)
        finally:
            _ = (time.perf_counter() - start) * 1000.0
        return self.results

    async def _dispatch(self, node: TaskNode) -> Any:
        op = self._ops.get(node.op)
        if not op:
            raise ValueError(f"Unknown op: {node.op}")
        return await op(node, self.results)

    # Convenience: minimal NL plan builder used optionally by the API layer
    @staticmethod
    def plan_from_query(q: str) -> Plan:
        nodes: dict[str, TaskNode] = {}
        ql = q.lower()
        # optional search node
        if any(k in ql for k in ["latest", "current", "recent", "news"]):
            nodes["search"] = TaskNode(id="search", op="local_search", params={"query": q})
        # optional calc node
        if any(k in ql for k in ["calculate", "compute", "math", "+", "-", "*", "/"]):
            dep = ["search"] if "search" in nodes else []
            nodes["calc"] = TaskNode(
                id="calc", op="calculator", params={"expression": q}, depends_on=dep
            )
        if not nodes:
            nodes["noop"] = TaskNode(id="noop", op="sleep", params={"ms": 5})
        return Plan(nodes=nodes, description="auto-plan")
