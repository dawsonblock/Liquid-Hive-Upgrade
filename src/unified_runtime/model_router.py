class DSRouter:

     def __init__(self, config: RouterConfig = None):
         self.config = config or RouterConfig.from_env()
         self.logger = logging.getLogger(__name__)

         # Initialize providers
         self.providers: Dict[str, BaseProvider] = {}
         self._initialize_providers()
 
         # Initialize circuit breakers for each provider
         self.circuit_breakers: Dict[str, CircuitBreaker] = {}
         self._initialize_circuit_breakers()

         # Start background health check task
         self._health_check_task = None
         self._start_health_monitoring()
 
        # Load routing and policy profiles from providers.yaml if available
        self._routing_default: Optional[str] = None
        self._routing_fallback: list[str] = []
+        self._profiles: Dict[str, Dict[str, float]] = {}
+        self.routing_profile = os.getenv("ROUTING_PROFILE", "balanced")
+        self._load_routing_policies()
        self._demote_policies: list[dict] = []
        self._promote_policies: list[dict] = []
+
     def _initialize_circuit_breakers(self):

         try:
             import asyncio
             loop = asyncio.get_event_loop()
             self._health_check_task = loop.create_task(self._periodic_health_check())
         except Exception as e:
             self.logger.warning(f"Could not start health monitoring: {e}")

         except Exception as e:
             self.logger.warning(f"Oracle provider install failed; using built-ins: {e}")
 
+    def _load_routing_policies(self) -> None:
+        """Load routing default/fallback and cost profiles from providers.yaml if available."""
+        try:
+            from oracle.manager import ProviderManager
+            pm = ProviderManager()
+            providers, routing = pm.load()
+            self._routing_default = routing.get("default_provider")
+            self._routing_fallback = list(routing.get("fallback_chain", []) or [])
+            pol = (pm.policies or {}).get("profiles", {})
+            # Normalize profile values
+            for name, cfg in (pol or {}).items():
+                self._profiles[name] = {
+                    "max_tokens": float(cfg.get("max_tokens", 2048)),
+                    "max_cost_usd_per_req": float(cfg.get("max_cost_usd_per_req", 0.01)),
+                }
+            # demote/promote policies
+            dem = (pm.policies or {}).get("demote_on", []) or []
+            pro = (pm.policies or {}).get("promote_on", []) or []
+            self._demote_policies = list(dem)
+            self._promote_policies = list(pro)
+        except Exception as e:
+            self.logger.debug(f"Routing/policies not loaded from providers.yaml: {e}")
+
     async def _call_provider_with_circuit_breaker(self, provider_name: str, request: GenRequest) -> GenResponse:
         """Call provider with circuit breaker protection."""
         circuit_breaker = self.circuit_breakers.get(provider_name)
         provider = self.providers.get(provider_name)

-        try:
+        try:
             # Make the actual provider call with timeout, wrapped in OTEL span if available
-            if getattr(self, "_tracer", None):
+            # Apply routing profile token caps
+            request = self._apply_profile_limits(request)
+            if getattr(self, "_tracer", None):
                 with self._tracer.start_as_current_span("provider.generate", attributes={
                     "provider.name": provider_name,
                     "timeout": circuit_breaker.config.timeout_seconds,
                 }):
                     response = await asyncio.wait_for(
                         provider.generate(request),
                         timeout=circuit_breaker.config.timeout_seconds
                     )
             else:
                 response = await asyncio.wait_for(
                     provider.generate(request),
                     timeout=circuit_breaker.config.timeout_seconds
                 )

             raise
+
+    def _apply_profile_limits(self, req: GenRequest) -> GenRequest:
+        """Apply routing profile caps (max_tokens and cost guards)."""
+        try:
+            prof = self._profiles.get(self.routing_profile) or {}
+            cap = int(prof.get("max_tokens", 0) or 0)
+            if cap > 0:
+                # dataclass is mutable; set max_tokens to min(current, cap)
+                if req.max_tokens is None:
+                    req.max_tokens = cap
+                else:
+                    req.max_tokens = min(int(req.max_tokens), cap)
+        except Exception:
+            pass
+        return req

-        try:
-            response = await self._call_provider_with_circuit_breaker(decision.provider, request)
+        try:
+            # If decision provider is 'default', resolve from routing config
+            prov_name = decision.provider
+            if decision.provider == "default" and self._routing_default:
+                prov_name = self._routing_default
+            response = await self._call_provider_with_circuit_breaker(prov_name, request)
+            # Apply promotion/demotion flags into response metadata for analytics
+            if getattr(self, "_promote_policies", None):
+                response.metadata["promote_policies"] = self._promote_policies
+            if getattr(self, "_demote_policies", None):
+                response.metadata["demote_policies"] = self._demote_policies
             response.metadata.update({
-                "routing_decision": decision.provider,
+                "routing_decision": prov_name,
                 "routing_reasoning": decision.reasoning
             })
             return response
             
         except Exception as e:
             # If primary provider fails, attempt fallback
             self.logger.warning(f"Provider {decision.provider} failed: {e}")
             
             # Try fallback providers in order
-            fallback_order = ["qwen_cpu"]  # Local fallback
+            fallback_order = list(self._routing_fallback) if getattr(self, "_routing_fallback", None) else []
+            if "qwen_cpu" in self.providers and "qwen_cpu" not in fallback_order:
+                fallback_order.append("qwen_cpu")
             
             for fallback_provider in fallback_order:
                 if fallback_provider == decision.provider:
                     continue  # Skip if it's the same provider that failed
                 
                 try:
                     response = await self._call_provider_with_circuit_breaker(fallback_provider, request)
                     response.metadata.update({
                         "routing_decision": fallback_provider,
                         "routing_reasoning": f"fallback_from_{decision.provider}",
                         "original_provider_failed": decision.provider,
                         "fallback_reason": str(e)
                     })
                     return response

     async def _audit_log(self, request: GenRequest, response: GenResponse, routing: 'RoutingDecision', 
                         pre_guard=None, post_guard=None):
         """Log audit information for compliance and monitoring."""
-        audit_entry = {
+        audit_entry = {
             "timestamp": datetime.utcnow().isoformat(),
             "input_sha256": self._hash_content(request.prompt),
             "provider": response.provider,
             "confidence": response.confidence,
             "routing_decision": routing.provider,
             "routing_reasoning": routing.reasoning,
             "blocked": response.metadata.get("blocked", False),
             "escalated": response.metadata.get("escalated", False),
             "filters": {
                 "pre_guard": pre_guard.status if pre_guard else "disabled",
                 "post_guard": post_guard.status if post_guard else "disabled"
             },
             "tokens": {
                 "prompt": response.prompt_tokens,
                 "output": response.output_tokens
             },
             "cost_usd": response.cost_usd,
             "latency_ms": response.latency_ms
         }
-        
-        # In production, send to audit log service
-        self.logger.info("Audit log", extra={"audit": audit_entry})
+        # Sign audit entry if AUDIT_HMAC_KEY set and optionally write to file
+        try:
+            import hmac, hashlib, os, json
+            key = os.getenv("AUDIT_HMAC_KEY")
+            if key:
+                payload = json.dumps(audit_entry, sort_keys=True).encode()
+                sig = hmac.new(key.encode(), payload, hashlib.sha256).hexdigest()
+                audit_entry["signature"] = sig
+                # Write to file if configured
+                path = os.getenv("AUDIT_LOG_FILE", "/app/data/runs/audit.log")
+                os.makedirs(os.path.dirname(path), exist_ok=True)
+                with open(path, "a", encoding="utf-8") as f:
+                    f.write(json.dumps(audit_entry) + "\n")
+        except Exception:
+            pass
+        # Also send to logger
+        self.logger.info("Audit log", extra={"audit": audit_entry})