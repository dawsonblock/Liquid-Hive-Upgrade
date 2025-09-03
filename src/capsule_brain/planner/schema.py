from __future__ import annotations

from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field, model_validator


OpKind = Literal[
    "local_search",    # stubbed local search
    "calculator",      # safe calculator
    "flaky",           # helper for tests: fails N times before success
    "sleep",           # helper op: sleep N ms
]


class TaskNode(BaseModel):
    id: str = Field(..., description="Unique node id")
    op: OpKind = Field(..., description="Operation kind")
    params: Dict[str, Any] = Field(default_factory=dict)
    depends_on: List[str] = Field(default_factory=list)
    retries: int = Field(0, ge=0, le=5)
    timeout_sec: Optional[float] = Field(None, ge=0.01, description="Per-node timeout")


class Plan(BaseModel):
    nodes: Dict[str, TaskNode] = Field(default_factory=dict)
    description: Optional[str] = None

    @model_validator(mode="after")
    def _validate_dag(self) -> "Plan":
        # Simple cycle detection using DFS
        visited: Dict[str, int] = {}
        stack: List[str] = []

        def dfs(u: str):
            visited[u] = 1
            stack.append(u)
            for v in self.nodes.get(u, TaskNode(id=u, op="sleep")).depends_on:
                if v not in self.nodes:
                    raise ValueError(f"Plan references unknown node '{v}' in depends_on of '{u}'")
                state = visited.get(v, 0)
                if state == 0:
                    dfs(v)
                elif state == 1:
                    path = " -> ".join(stack + [v])
                    raise ValueError(f"Cycle detected in plan: {path}")
            visited[u] = 2
            stack.pop()

        for nid in self.nodes:
            if visited.get(nid, 0) == 0:
                dfs(nid)
        return self