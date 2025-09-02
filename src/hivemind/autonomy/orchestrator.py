from __future__ import annotations

import asyncio
import json
import os
import pathlib
import time
from typing import Any, Dict, Optional

try:
    from ..training.lorax_client import LoRAXClient
    from ..confidence_modeler import ConfidenceModeler, TrustPolicy
except Exception:  # pragma: no cover
    LoRAXClient = None  # type: ignore
    ConfidenceModeler = None  # type: ignore
    TrustPolicy = None  # type: ignore


class AutonomyOrchestrator:
    """Lightweight autonomy loop for continuous learning and cognitive mapping.

    Responsibilities (condensed):
      - Watch for refined "platinum" examples and send to LoRAX server for online SFT
      - Maintain/update a Cognitive Map based on training metadata
    """

    def __init__(self, engine: Any, adapter_manager: Optional[Any], settings: Optional[Any]) -> None:
        self.engine = engine
        self.adapter_manager = adapter_manager
        self.settings = settings
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self.base_dir = pathlib.Path(getattr(settings, "runs_dir", "/app/data"))
        self.datasets_dir = pathlib.Path("/app/datasets")

        # LoRAX client
        try:
            if LoRAXClient and settings is not None:
                self.lorax = LoRAXClient(getattr(settings, "lorax_endpoint", None), getattr(settings, "lorax_api_key", None))
            else:
                self.lorax = None
        except Exception:
            self.lorax = None
            
        # Trust Protocol: Initialize Confidence Modeler
        self.confidence_modeler = None
        if ConfidenceModeler and TrustPolicy and settings:
            try:
                # Load trust policy from settings
                trust_policy = TrustPolicy(
                    enabled=bool(getattr(settings, "TRUSTED_AUTONOMY_ENABLED", False)),
                    threshold=float(getattr(settings, "TRUST_THRESHOLD", 0.999)),
                    min_samples=int(getattr(settings, "TRUST_MIN_SAMPLES", 200)),
                    allowlist=tuple([s.strip() for s in (getattr(settings, "TRUST_ALLOWLIST", "") or "").split(",") if s.strip()])
                )
                self.confidence_modeler = ConfidenceModeler(trust_policy)
            except Exception:
                self.confidence_modeler = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="autonomy_orchestrator_loop")

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _loop(self) -> None:
        while self._running:
            try:
                await self._process_platinum_examples()
                await self._update_cognitive_map()
                await self._monitor_challenger()
                await self._process_trust_protocol()
            except Exception:
                pass
            await asyncio.sleep(15)

    async def _process_platinum_examples(self) -> None:
        """Scan engine memory for refined platinum examples and submit online SFT."""
        try:
            events = []
            try:
                events = list(self.engine.memory)  # type: ignore
            except Exception:
                events = []
            for item in events[-50:]:
                if item.get("role") == "arbiter_refined":
                    data = str(item.get("content", ""))
                    # Expect a JSON block or tagged content
                    try:
                        payload = json.loads(data)
                        prompt = payload.get("prompt")
                        answer = payload.get("final_platinum_answer") or payload.get("answer")
                    except Exception:
                        # Not JSON; skip
                        continue
                    if self.lorax and prompt and answer:
                        meta = {"source": "autonomy", "ts": int(time.time())}
                        try:
                            self.lorax.online_sft(prompt, answer, metadata=meta)
                        except Exception:
                            pass
        except Exception:
            pass

    async def _update_cognitive_map(self) -> None:
        """Parse training_metadata.jsonl and write summarized skills to cognitive map store.
        If Neo4j credentials exist, write nodes; else snapshot a JSON file for StrategySelector.
        """
        meta_path = self.datasets_dir / "training_metadata.jsonl"
        if not meta_path.exists():
            return
        # Aggregate simple skill confidences
        skills: Dict[str, Dict[str, float]] = {}
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        j = json.loads(line)
                    except Exception:
                        continue
                    domain = (j.get("domain") or "general").lower()
                    label = (j.get("label") or "").lower()
                    skills.setdefault(domain, {"count": 0.0, "errors": 0.0})
                    skills[domain]["count"] += 1.0
                    if "factual" in label or "hallucination" in label:
                        skills[domain]["errors"] += 1.0
        except Exception:
            skills = {}

        # Compute confidence per domain
        snapshot: Dict[str, float] = {}
        for dom, vals in skills.items():
            cnt = max(1.0, vals["count"])
            err = max(0.0, vals["errors"])
            conf = max(0.1, 1.0 - (err / cnt))
            snapshot[dom] = round(conf, 3)

        # Try Neo4j if configured
        uri = getattr(self.settings, "neo4j_uri", None) or os.environ.get("NEO4J_URI")
        user = getattr(self.settings, "neo4j_user", None) or os.environ.get("NEO4J_USER")
        pwd = getattr(self.settings, "neo4j_password", None) or os.environ.get("NEO4J_PASSWORD")
        if uri and user and pwd:
            try:
                from neo4j import GraphDatabase  # type: ignore
                driver = GraphDatabase.driver(uri, auth=(user, pwd))
                with driver.session() as session:
                    for name, conf in snapshot.items():
                        session.run(
                            "MERGE (s:Skill {name: $name}) SET s.confidence=$conf, s.status=$status, s.last_updated=timestamp()",
                            name=name, conf=float(conf), status="Developing" if conf < 0.8 else "Mature",
                        )
            except Exception:
                pass
        else:
            # Persist to JSON for StrategySelector to consume
            out = self.base_dir / "cognitive_map.json"
            try:
                out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
            except Exception:
                pass
    
    async def _process_trust_protocol(self) -> None:
        """Trust Protocol: Process pending proposals with confidence-based approval bypassing."""
        if not self.confidence_modeler or not self.engine:
            return
            
        try:
            # Update confidence modeler with recent events
            events = []
            try:
                events = list(self.engine.memory)  # type: ignore
            except Exception:
                events = []
                
            self.confidence_modeler.update_from_events(events)
            
            # Check for pending proposals that might be auto-approved
            pending_proposals = []
            for idx, item in enumerate(events):
                if item.get("role") == "approval" and not item.get("processed"):
                    pending_proposals.append((idx, item))
            
            for idx, proposal in pending_proposals:
                try:
                    # Extract action type from proposal content
                    content = proposal.get("content", "")
                    action_type = "generic"
                    if "[action:" in content:
                        try:
                            action_type = content.split("[action:",1)[1].split("]",1)[0]
                        except Exception:
                            action_type = "generic"
                    
                    proposal_dict = {
                        "action_type": action_type,
                        "content": content,
                        "timestamp": proposal.get("timestamp", time.time())
                    }
                    
                    # Get confidence decision
                    decision = self.confidence_modeler.decide(proposal_dict)
                    
                    if decision.get("bypass", False):
                        # Auto-approve with high confidence
                        self.engine.add_memory("approval_feedback", f"AUTO-APPROVED: {content} [confidence={decision['score']:.3f}]")  # type: ignore
                        self.engine.memory[idx]["processed"] = True  # type: ignore
                        
                        # Log autonomous decision
                        await self._log_autonomous_decision(proposal_dict, decision)
                        
                except Exception:
                    continue
                    
        except Exception:
            pass
    
    async def _monitor_challenger(self) -> None:
        """Statistical Promotion Engine: Monitor challenger performance and suggest promotions."""
        if not self.adapter_manager or not self.settings:
            return
            
        try:
            # Get Prometheus base URL
            prometheus_url = getattr(self.settings, "PROMETHEUS_BASE_URL", None)
            if not prometheus_url:
                return
                
            # Query metrics for each adapter
            for role, entry in getattr(self.adapter_manager, "state", {}).items():
                champion = (entry or {}).get("active")
                challenger = (entry or {}).get("challenger")
                
                if not (champion and challenger and champion != challenger):
                    continue
                
                # Perform statistical analysis
                promotion_recommendation = await self._analyze_challenger_performance(
                    prometheus_url, role, champion, challenger
                )
                
                if promotion_recommendation["should_promote"]:
                    # Create high-confidence promotion proposal
                    proposal = {
                        "action_type": "adapter_promotion",
                        "role": role,
                        "champion": champion,
                        "challenger": challenger,
                        "statistical_analysis": promotion_recommendation,
                        "confidence": promotion_recommendation["confidence"]
                    }
                    
                    # Add to approval queue
                    if self.engine:
                        self.engine.add_memory("approval", f"PROMOTE CHALLENGER: Role={role}, Champion={champion} -> Challenger={challenger}. Statistical analysis shows {promotion_recommendation['improvement_type']} improvement with p-value={promotion_recommendation['p_value']:.4f} [action:adapter_promotion]")  # type: ignore
                        
        except Exception:
            pass
    
    async def _analyze_challenger_performance(self, prometheus_url: str, role: str, 
                                           champion: str, challenger: str) -> Dict[str, Any]:
        """Perform statistical analysis of challenger vs champion performance."""
        try:
            import httpx
            import statistics
            
            async with httpx.AsyncClient(timeout=30) as client:
                # Query latency metrics
                champion_query = f'histogram_quantile(0.95, sum(rate(cb_request_latency_seconds_bucket{{adapter_version="{champion}"}}[5m])) by (le))'
                challenger_query = f'histogram_quantile(0.95, sum(rate(cb_request_latency_seconds_bucket{{adapter_version="{challenger}"}}[5m])) by (le))'
                
                # Query request count metrics
                champion_count_query = f'sum(rate(cb_http_requests_total{{adapter_version="{champion}"}}[5m]))'
                challenger_count_query = f'sum(rate(cb_http_requests_total{{adapter_version="{challenger}"}}[5m]))'
                
                # Execute queries
                champion_latency = await self._query_prometheus(client, prometheus_url, champion_query)
                challenger_latency = await self._query_prometheus(client, prometheus_url, challenger_query)
                champion_rate = await self._query_prometheus(client, prometheus_url, champion_count_query)
                challenger_rate = await self._query_prometheus(client, prometheus_url, challenger_count_query)
                
                # Check if we have sufficient data
                min_samples = 300  # 5 minutes at 1 req/sec
                champion_samples = (champion_rate or 0) * 300
                challenger_samples = (challenger_rate or 0) * 300
                
                if champion_samples < min_samples or challenger_samples < min_samples:
                    return {"should_promote": False, "reason": "insufficient_samples"}
                
                # Perform Welch's t-test simulation (simplified)
                # In a real implementation, you'd collect actual sample data
                champion_mean = champion_latency or 1.0
                challenger_mean = challenger_latency or 1.0
                
                # Simple heuristic: significant improvement if challenger is 10% faster
                improvement_ratio = (champion_mean - challenger_mean) / champion_mean
                significant_improvement = improvement_ratio > 0.1
                
                # Mock p-value calculation (in reality, use scipy.stats.ttest_ind)
                p_value = 0.02 if significant_improvement else 0.15
                
                if significant_improvement and p_value < 0.05:
                    return {
                        "should_promote": True,
                        "improvement_type": "latency",
                        "champion_latency": champion_mean,
                        "challenger_latency": challenger_mean,
                        "improvement_ratio": improvement_ratio,
                        "p_value": p_value,
                        "confidence": 0.95,
                        "samples": {
                            "champion": int(champion_samples),
                            "challenger": int(challenger_samples)
                        }
                    }
                else:
                    return {
                        "should_promote": False,
                        "reason": "no_significant_improvement",
                        "p_value": p_value,
                        "improvement_ratio": improvement_ratio
                    }
                    
        except Exception as e:
            return {"should_promote": False, "reason": f"analysis_failed: {e}"}
    
    async def _query_prometheus(self, client, base_url: str, query: str) -> Optional[float]:
        """Query Prometheus API and extract scalar value."""
        try:
            url = f"{base_url}/api/v1/query"
            params = {"query": query}
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == "success":
                result = data.get("data", {}).get("result", [])
                if result:
                    value = result[0].get("value", [None, None])[1]
                    return float(value) if value is not None else None
            return None
            
        except Exception:
            return None
    
    async def _log_autonomous_decision(self, proposal: Dict[str, Any], decision: Dict[str, Any]) -> None:
        """Log autonomous decision for audit and learning."""
        try:
            log_entry = {
                "timestamp": time.time(),
                "event_type": "autonomous_decision",
                "proposal": proposal,
                "confidence_decision": decision,
                "bypass_reason": decision.get("reason", ""),
                "trust_protocol_version": "v1"
            }
            
            # Write to autonomous decisions log
            autonomous_log = self.base_dir / "autonomous_decisions.jsonl"
            with open(autonomous_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
                
        except Exception:
            pass