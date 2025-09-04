import asyncio
import os
import time
import pytest

from capsule_brain.planner.schema import Plan, TaskNode
from capsule_brain.planner.engine import PlanExecutor


@pytest.mark.asyncio
async def test_cycle_detection():
    # A -> B -> A
    a = TaskNode(id="A", op="sleep", params={"ms": 1}, depends_on=["B"])
    b = TaskNode(id="B", op="sleep", params={"ms": 1}, depends_on=["A"])
    with pytest.raises(ValueError):
        Plan(nodes={"A": a, "B": b})  # validated in model


@pytest.mark.asyncio
async def test_retry_flaky_passes():
    # Fails first 2 attempts, retries=2 should pass on third try
    n = TaskNode(id="F", op="flaky", params={"fail_first": 2}, retries=2)
    plan = Plan(nodes={"F": n})
    ex = PlanExecutor(plan)
    res = await ex.execute()
    assert res["F"].ok is True
    assert res["F"].attempts == 3


@pytest.mark.asyncio
async def test_timeout_enforced():
    # sleep 100ms with timeout 0.02s should fail
    n = TaskNode(id="S", op="sleep", params={"ms": 100}, timeout_sec=0.02, retries=0)
    plan = Plan(nodes={"S": n})
    ex = PlanExecutor(plan)
    res = await ex.execute()
    assert res["S"].ok is False
    assert res["S"].error == "timeout"


@pytest.mark.asyncio
async def test_fan_in_out():
    # P -> A, P -> B, and C depends on A & B (fan-in)
    p = TaskNode(id="P", op="sleep", params={"ms": 5})
    a = TaskNode(id="A", op="sleep", params={"ms": 5}, depends_on=["P"])
    b = TaskNode(id="B", op="sleep", params={"ms": 5}, depends_on=["P"])
    c = TaskNode(id="C", op="calculator", params={"expression": "1+1"}, depends_on=["A", "B"])
    plan = Plan(nodes={"P": p, "A": a, "B": b, "C": c})
    ex = PlanExecutor(plan)
    res = await ex.execute()

    assert all(res[n].ok for n in ["P", "A", "B", "C"])  # fan-out + fan-in executed
    assert res["C"].value["value"] == 2.0


@pytest.mark.asyncio
async def test_from_query_helper_runs():
    plan = PlanExecutor.plan_from_query(
        "Please calculate 2+2 and show the latest news about SpaceX"
    )
    ex = PlanExecutor(plan)
    res = await ex.execute()
    assert any(n.ok for n in res.values())
