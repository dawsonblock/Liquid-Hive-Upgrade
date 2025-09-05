from __future__ import annotations

import asyncio
import json
import os
import pathlib
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class KnowledgeFrontier:
    kind: str  # orphan_nodes | weak_component | semantic_gap
    description: str
    nodes: list[str] = field(default_factory=list)
    missing_edge: tuple[str, str] | None = None


class CuriosityEngine:
    """CuriosityEngine periodically analyzes the knowledge graph to identify "frontiers",
    formulates a self-generated research question, submits it for operator approval,
    and upon approval executes an autonomous research & synthesis workflow.

    The engine is resilient: if optional dependencies (Neo4j, roles, retriever) are
    unavailable, it degrades gracefully and still records intents in memory.
    """

    def __init__(
        self,
        engine: Any,
        roles: Any | None = None,
        retriever: Any | None = None,
        settings: Any | None = None,
        loop_interval_sec: int = 900,  # 15 minutes
    ) -> None:
        self.engine = engine
        self.roles = roles
        self.retriever = retriever
        self.settings = settings
        self.loop_interval_sec = loop_interval_sec

        self._task: asyncio.Task | None = None
        self._approvals_task: asyncio.Task | None = None
        self._running = False

        # Storage
        self.base_dir = pathlib.Path(getattr(settings, "runs_dir", "/app/data"))
        self.curiosity_dir = self.base_dir / "curiosity"
        self.curiosity_dir.mkdir(parents=True, exist_ok=True)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop(), name="curiosity_frontier_loop")
        self._approvals_task = asyncio.create_task(
            self._approvals_watcher(), name="curiosity_approvals_watcher"
        )

    async def stop(self) -> None:
        self._running = False
        for t in (self._task, self._approvals_task):
            if t and not t.done():
                t.cancel()
        self._task = None
        self._approvals_task = None

    # ---- Phase 1: Knowledge Frontier ----
    async def _run_loop(self) -> None:
        while self._running:
            try:
                frontiers = await self._analyze_knowledge_graph()
                for fr in frontiers:
                    q = await self._generate_question(fr)
                    if q:
                        await self._submit_curiosity_quest(fr, q)
            except Exception:
                # Never crash the loop
                pass
            await asyncio.sleep(self.loop_interval_sec)

    async def _analyze_knowledge_graph(self) -> list[KnowledgeFrontier]:
        """Analyze the knowledge graph via CapsuleEngine or Neo4j (if available).
        Returns a list of frontier descriptors.
        """
        results: list[KnowledgeFrontier] = []

        # Preferred: use engine hooks if present
        try:
            # Heuristic: engine may expose a graph snapshot
            graph_info = None
            if hasattr(self.engine, "get_graph_snapshot"):
                graph_info = await self.engine.get_graph_snapshot()  # type: ignore
            elif hasattr(self.engine, "knowledge_graph"):
                graph_info = self.engine.knowledge_graph

            if graph_info:
                # Expect nodes: [{id, degree, labels}], edges: [(src, dst)]
                nodes = graph_info.get("nodes", [])
                edges = graph_info.get("edges", [])
                id_to_deg = {
                    n.get("id"): int(n.get("degree", 0)) for n in nodes if n.get("id") is not None
                }
                # Orphans / near-orphans
                orphan_nodes = [nid for nid, deg in id_to_deg.items() if deg <= 1]
                if orphan_nodes:
                    results.append(
                        KnowledgeFrontier(
                            kind="orphan_nodes",
                            description=f"{len(orphan_nodes)} low-degree nodes detected",
                            nodes=orphan_nodes[:20],
                        )
                    )
                # Weak components: naive detection using edges
                try:
                    comp = self._weakly_connected_components(nodes, edges)
                    if len(comp) > 1:
                        # Identify small components
                        small = [c for c in comp if len(c) < max(5, int(0.05 * len(nodes)))]
                        if small:
                            # Flatten small comps as nodes list
                            nodes_small = [n for sub in small for n in sub][:50]
                            results.append(
                                KnowledgeFrontier(
                                    kind="weak_component",
                                    description=f"{len(small)} small weakly-connected components",
                                    nodes=nodes_small,
                                )
                            )
                except Exception:
                    pass
            # Semantic gaps: heuristic - pick two high-degree nodes with no edge
            try:
                if graph_info:
                    nodes = graph_info.get("nodes", [])
                    edges_set = set()
                    for s, t in graph_info.get("edges", []):
                        edges_set.add((s, t))
                        edges_set.add((t, s))
                    ranked = sorted(nodes, key=lambda n: int(n.get("degree", 0)), reverse=True)
                    if len(ranked) >= 10:
                        a = ranked[0].get("id")
                        b = ranked[1].get("id")
                        if a and b and (a, b) not in edges_set:
                            results.append(
                                KnowledgeFrontier(
                                    kind="semantic_gap",
                                    description=f"High-degree nodes '{a}' and '{b}' are unconnected",
                                    nodes=[a, b],
                                    missing_edge=(a, b),
                                )
                            )
            except Exception:
                pass
        except Exception:
            pass

        # Fallback: Neo4j direct analysis if configured
        if not results:
            try:
                uri = getattr(self.settings, "neo4j_uri", None) or os.environ.get("NEO4J_URI")
                user = getattr(self.settings, "neo4j_user", None) or os.environ.get("NEO4J_USER")
                pwd = getattr(self.settings, "neo4j_password", None) or os.environ.get(
                    "NEO4J_PASSWORD"
                )
                if uri and user and pwd:
                    try:
                        from neo4j import GraphDatabase  # type: ignore
                    except Exception:
                        return results
                    driver = GraphDatabase.driver(uri, auth=(user, pwd))
                    with driver.session() as session:
                        # Orphans: nodes with degree <= 1
                        orphan = session.run(
                            """
                            MATCH (n)
                            WITH n, size((n)--()) as deg
                            WHERE deg <= 1
                            RETURN n.id as id
                            LIMIT 50
                        """
                        )
                        orphan_ids = [r["id"] for r in orphan if r.get("id")]
                        if orphan_ids:
                            results.append(
                                KnowledgeFrontier(
                                    kind="orphan_nodes",
                                    description=f"{len(orphan_ids)} low-degree nodes detected",
                                    nodes=orphan_ids,
                                )
                            )
            except Exception:
                pass

        return results

    def _weakly_connected_components(
        self, nodes: list[dict[str, Any]], edges: list[tuple[str, str]]
    ):
        idx = {n.get("id"): i for i, n in enumerate(nodes) if n.get("id") is not None}
        parent = list(range(len(idx)))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for s, t in edges:
            if s in idx and t in idx:
                union(idx[s], idx[t])

        comps: dict[int, list[str]] = {}
        rev = {v: k for k, v in idx.items()}
        for i in range(len(idx)):
            r = find(i)
            comps.setdefault(r, []).append(rev[i])
        return list(comps.values())

    # ---- Phase 2: Question Generator ----
    async def _generate_question(self, frontier: KnowledgeFrontier) -> str | None:
        prompt = (
            "You are a Research Scientist AI. You will be given a description of a gap in your own knowledge graph. "
            "Your mission is to formulate a single, powerful, and open-ended question that, if answered, would help you bridge this gap. "
            "The question should provoke deep, non-obvious connections. Return only the question.\n\n"
            f"[FRONTIER_KIND]: {frontier.kind}\n"
            f"[DESCRIPTION]: {frontier.description}\n"
            f"[NODES]: {', '.join(frontier.nodes[:10])}\n"
        )
        try:
            if self.roles is not None:
                # Prefer an Architect-style role if available
                if hasattr(self.roles, "architect"):
                    return await self.roles.architect(prompt)  # type: ignore
                # Fallback to implementer
                if hasattr(self.roles, "implementer"):
                    return await self.roles.implementer(prompt)  # type: ignore
        except Exception:
            pass
        # Fallback heuristic
        if frontier.kind == "semantic_gap" and len(frontier.nodes) >= 2:
            a, b = frontier.nodes[0], frontier.nodes[1]
            return f"What are the shared underlying principles that could bridge '{a}' and '{b}', and what second-order effects might emerge from their integration?"
        if frontier.nodes:
            return f"What unknown relationships connect the following sparse concepts: {', '.join(frontier.nodes[:5])}?"
        return None

    async def _submit_curiosity_quest(self, frontier: KnowledgeFrontier, question: str) -> None:
        quest_id = uuid.uuid4().hex
        payload = {
            "type": "curiosity_quest",
            "id": quest_id,
            "question": question,
            "frontier": frontier.__dict__,
            "ts": int(time.time()),
        }
        text = f"[Curiosity Quest] {json.dumps(payload)}"
        try:
            self.engine.add_memory("approval", text)
        except Exception:
            pass
        # Persist payload for traceability
        try:
            (self.curiosity_dir / f"quest_{quest_id}.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    # ---- Phase 3: Autonomous Research & Synthesis ----
    async def _approvals_watcher(self) -> None:
        """Watches for approval feedback and triggers research workflow."""
        seen: set[str] = set()
        while self._running:
            try:
                events = []
                try:
                    events = list(self.engine.memory)  # type: ignore
                except Exception:
                    events = []
                for item in events:
                    if item.get("role") == "approval_feedback":
                        content = str(item.get("content", ""))
                        if content.startswith("APPROVED: ") and "[Curiosity Quest]" in content:
                            # Extract JSON payload
                            try:
                                json_start = content.index("[Curiosity Quest]") + len(
                                    "[Curiosity Quest]"
                                )
                                payload_str = content[json_start:].strip()
                                payload = json.loads(payload_str)
                                qid = payload.get("id")
                                if qid and qid not in seen:
                                    seen.add(qid)
                                    asyncio.create_task(self._research_workflow(payload))
                            except Exception:
                                pass
                await asyncio.sleep(5)
            except Exception:
                await asyncio.sleep(5)

    async def _research_workflow(self, payload: dict[str, Any]) -> None:
        quest_id = payload.get("id", uuid.uuid4().hex)
        question = payload.get("question", "")
        workdir = self.curiosity_dir / f"quest_{quest_id}"
        workdir.mkdir(parents=True, exist_ok=True)

        # 1) Decomposition
        subqueries: list[str] = []
        try:
            if self.roles is not None and hasattr(self.roles, "architect"):
                prompt = (
                    "Decompose the following research question into 5-8 specific search queries. "
                    "Return them as bullet points only, one per line.\n\n" + question
                )
                plan = await self.roles.architect(prompt)  # type: ignore
                subqueries = [ln.strip("- •* ") for ln in plan.strip().splitlines() if ln.strip()]
        except Exception:
            pass
        if not subqueries:
            # Heuristic fallback
            subqueries = [question, f"background {question}", f"key concepts {question}"]

        # 2) Exploration (web search or local retrieval)
        docs: list[str] = []
        # Preferred: use retriever if available to avoid external integrations
        try:
            if self.retriever is not None:
                for q in subqueries[:10]:
                    try:
                        res = self.retriever.search(q, k=3)  # type: ignore
                        for d in res:
                            txt = str(getattr(d, "text", getattr(d, "page_content", "")))
                            if txt:
                                docs.append(txt)
                    except Exception:
                        pass
        except Exception:
            pass
        # Persist quarantined docs
        try:
            (workdir / "quarantine.txt").write_text("\n\n---\n\n".join(docs), encoding="utf-8")
        except Exception:
            pass

        # 3) Ingestion: placeholder quarantine stage (could notify rag watcher if available)
        try:
            marker = {"quest_id": quest_id, "count": len(docs), "ts": int(time.time())}
            (workdir / "quarantine_meta.json").write_text(
                json.dumps(marker, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

        # 4) Synthesis
        synthesis = ""
        try:
            context = "\n\n".join(docs[:20])
            synthesis_prompt = (
                "You are FusionAgent. Synthesize a comprehensive, cited answer to the RESEARCH QUESTION below. "
                "Ground only in the provided CONTEXT; if insufficient, state limitations. Use clear structure.\n\n"
                f"[RESEARCH QUESTION]: {question}\n\n[CONTEXT]:\n{context}\n"
            )
            if self.roles is not None:
                if hasattr(self.roles, "fusion_agent"):
                    synthesis = await self.roles.fusion_agent(synthesis_prompt)  # type: ignore
                elif hasattr(self.roles, "implementer"):
                    synthesis = await self.roles.implementer(synthesis_prompt)  # type: ignore
        except Exception:
            pass

        # Present finding to operator
        finding_payload = {
            "type": "curiosity_finding",
            "quest_id": quest_id,
            "question": question,
            "summary": synthesis,
            "ts": int(time.time()),
        }
        try:
            self.engine.add_memory("approval", f"[Curiosity Finding] {json.dumps(finding_payload)}")
        except Exception:
            pass

        # Record full finding
        try:
            (workdir / "finding.json").write_text(
                json.dumps(finding_payload, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

        # Await operator approval to merge
        await self._await_merge_decision(quest_id, workdir)

    async def _await_merge_decision(self, quest_id: str, workdir: pathlib.Path) -> None:
        """Await operator approval and automatically feed findings into RAG system.
        This closes the autonomous learning loop!
        """
        seen = False
        while True:
            try:
                events = []
                try:
                    events = list(self.engine.memory)  # type: ignore
                except Exception:
                    events = []
                for item in events:
                    if item.get("role") == "approval_feedback":
                        content = str(item.get("content", ""))
                        if (
                            "[Curiosity Finding]" in content
                            and "APPROVED:" in content
                            and quest_id in content
                        ):
                            # ENHANCED: Auto-feed to RAG ingestion for autonomous learning
                            await self._integrate_finding_into_rag(quest_id, workdir)

                            # Mark as merged (existing functionality)
                            try:
                                (workdir / "merged").write_text("approved", encoding="utf-8")
                            except Exception:
                                pass
                            try:
                                self.engine.add_memory(
                                    "self_extension",
                                    f"Merged curiosity finding {quest_id} into KB and RAG index.",
                                )
                            except Exception:
                                pass
                            seen = True
                            break
                if seen:
                    break
                await asyncio.sleep(5)
            except Exception:
                await asyncio.sleep(5)

    async def _integrate_finding_into_rag(self, quest_id: str, workdir: pathlib.Path) -> None:
        """Automatically integrate approved curiosity findings into the RAG system.
        This creates the closed-loop autonomous learning capability!
        """
        try:
            # Load the finding data
            finding_file = workdir / "finding.json"
            if not finding_file.exists():
                return

            finding_data = json.loads(finding_file.read_text(encoding="utf-8"))

            # Extract key information
            question = finding_data.get("question", "Unknown Question")
            summary = finding_data.get("summary", "No summary available")
            timestamp = finding_data.get("ts", int(time.time()))

            # Format as a comprehensive knowledge document
            knowledge_doc = f"""# Autonomous Research Finding: {quest_id}

**Research Question:** {question}

**Generated:** {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(timestamp))}

**Research Summary:**
{summary}

**Source:** Autonomous Curiosity Engine - Self-Generated Research

**Tags:** #autonomous-research #curiosity-engine #knowledge-synthesis

---

This document was automatically generated by the LIQUID-HIVE Curiosity Engine through autonomous knowledge gap identification, research execution, and synthesis. It represents a self-directed learning outcome that has been reviewed and approved by the human operator.

The findings above extend the AI system's knowledge base through active exploration of conceptual frontiers and knowledge graph analysis.
"""

            # Determine RAG ingestion directory
            ingest_dir = self._get_rag_ingest_directory()
            if not ingest_dir:
                return

            # Create filename with timestamp and quest ID
            filename = f"curiosity_finding_{quest_id}_{timestamp}.md"
            ingest_file = ingest_dir / filename

            # Write to ingestion directory for automatic processing
            ingest_file.write_text(knowledge_doc, encoding="utf-8")

            # Log the integration
            try:
                self.engine.add_memory(
                    "system",
                    f"🧠 Autonomous Learning: Finding {quest_id} integrated into RAG knowledge base at {filename}",
                )
            except Exception:
                pass

        except Exception as e:
            # Log error but don't crash the process
            try:
                self.engine.add_memory(
                    "system", f"❌ Failed to integrate finding {quest_id} into RAG: {e!s}"
                )
            except Exception:
                pass

    def _get_rag_ingest_directory(self) -> pathlib.Path | None:
        """Get the RAG ingestion directory path."""
        try:
            # Try to get from settings first
            if self.settings and hasattr(self.settings, "ingest_dir"):
                ingest_dir = pathlib.Path(self.settings.ingest_dir)
                if ingest_dir.exists():
                    return ingest_dir

            # Try standard locations
            standard_paths = [
                pathlib.Path("/app/data/ingest"),
                self.base_dir / "ingest",
                pathlib.Path(os.getcwd()) / "data" / "ingest",
            ]

            for path in standard_paths:
                if path.exists():
                    return path

            # Create default ingestion directory
            default_ingest = self.base_dir / "ingest"
            default_ingest.mkdir(parents=True, exist_ok=True)
            return default_ingest

        except Exception:
            return None
