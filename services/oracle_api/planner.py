"""Oracle mutation planning engine for system optimization."""

import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import structlog

from services.shared.schemas import (
    AnalysisFindings, MutationPlan, MutationAction, MutationOperationType,
    SafetyCheckType, OracleConfig
)

logger = structlog.get_logger(__name__)


class MutationStrategy:
    """Strategies for generating specific types of mutations."""
    
    @staticmethod
    def create_performance_optimizations(
        agent_id: str,
        degradation_metrics: Dict[str, Any],
        confidence: float
    ) -> List[MutationAction]:
        """Create mutations to address performance degradation.
        
        Args:
            agent_id: ID of the agent with performance issues
            degradation_metrics: Metrics showing the degradation
            confidence: Confidence level in the degradation detection
            
        Returns:
            List of mutation actions to improve performance
        """
        actions = []
        
        # Response time optimization
        if degradation_metrics.get("response_time_increase_percent", 0) > 20:
            actions.append(MutationAction(
                action_id=f"optimize_response_{uuid.uuid4().hex[:8]}",
                target=f"agent/{agent_id}",
                operation=MutationOperationType.PROMPT_PATCH,
                args={
                    "patch_type": "conciseness_optimization",
                    "description": "Optimize prompts for faster responses",
                    "changes": [
                        "Add explicit instructions for concise responses",
                        "Remove unnecessary context in system prompts",
                        "Add timeout guidance for long operations"
                    ]
                },
                priority=8,  # High priority for performance
                timeout_seconds=60
            ))
            
            # Consider model swap for severe degradation
            if degradation_metrics.get("response_time_increase_percent", 0) > 50:
                actions.append(MutationAction(
                    action_id=f"model_swap_{uuid.uuid4().hex[:8]}",
                    target=f"model_route/{agent_id}",
                    operation=MutationOperationType.MODEL_SWAP,
                    args={
                        "current_model": "gpt-4",
                        "target_model": "gpt-3.5-turbo",
                        "reason": "Performance optimization - faster model",
                        "rollback_threshold": 0.1  # Rollback if quality drops >10%
                    },
                    priority=6,
                    timeout_seconds=30,
                    requires_approval=True  # Model changes need approval
                ))
        
        # Memory optimization for context handling
        if degradation_metrics.get("memory_usage_mb", 0) > 1000:
            actions.append(MutationAction(
                action_id=f"memory_optimize_{uuid.uuid4().hex[:8]}",
                target=f"agent/{agent_id}",
                operation=MutationOperationType.MEMORY_UPDATE,
                args={
                    "operation": "context_pruning",
                    "max_context_length": 8000,
                    "pruning_strategy": "relevance_based",
                    "preserve_recent_turns": 3
                },
                priority=7,
                timeout_seconds=45
            ))
        
        return actions
    
    @staticmethod
    def create_satisfaction_improvements(
        agent_id: str,
        satisfaction_metrics: Dict[str, Any],
        complaints: List[Dict[str, Any]] = None
    ) -> List[MutationAction]:
        """Create mutations to improve user satisfaction.
        
        Args:
            agent_id: ID of the agent with satisfaction issues
            satisfaction_metrics: Metrics showing dissatisfaction
            complaints: Optional list of user complaints
            
        Returns:
            List of mutation actions to improve satisfaction
        """
        actions = []
        
        # Prompt improvements based on rating data
        if satisfaction_metrics.get("average_rating", 5.0) < 3.5:
            actions.append(MutationAction(
                action_id=f"satisfaction_prompt_{uuid.uuid4().hex[:8]}",
                target=f"agent/{agent_id}",
                operation=MutationOperationType.PROMPT_PATCH,
                args={
                    "patch_type": "satisfaction_enhancement",
                    "description": "Improve prompts based on user feedback",
                    "changes": [
                        "Add more empathetic language",
                        "Include clarification questions",
                        "Provide more detailed explanations",
                        "Add confidence indicators"
                    ],
                    "current_avg_rating": satisfaction_metrics.get("average_rating"),
                    "target_improvement": 0.8
                },
                priority=7,
                timeout_seconds=90
            ))
        
        # Address specific complaint patterns
        if complaints and len(complaints) > 2:
            complaint_patterns = MutationStrategy._analyze_complaint_patterns(complaints)
            
            for pattern_type, pattern_info in complaint_patterns.items():
                actions.append(MutationAction(
                    action_id=f"complaint_fix_{pattern_type}_{uuid.uuid4().hex[:8]}",
                    target=f"agent/{agent_id}",
                    operation=MutationOperationType.PROMPT_PATCH,
                    args={
                        "patch_type": f"complaint_resolution_{pattern_type}",
                        "description": f"Address {pattern_type} complaints",
                        "complaint_examples": pattern_info["examples"][:2],
                        "suggested_improvements": pattern_info["suggestions"]
                    },
                    priority=6,
                    timeout_seconds=120,
                    requires_approval=True  # Manual review for complaint-based changes
                ))
        
        # LoRA fine-tuning for persistent satisfaction issues
        if satisfaction_metrics.get("average_rating", 5.0) < 3.0 and satisfaction_metrics.get("total_ratings", 0) > 10:
            actions.append(MutationAction(
                action_id=f"lora_satisfaction_{uuid.uuid4().hex[:8]}",
                target=f"model/{agent_id}",
                operation=MutationOperationType.LORA_APPLY,
                args={
                    "adapter_name": f"satisfaction_tuning_{agent_id}",
                    "base_model": "gpt-3.5-turbo",
                    "training_data_source": "recent_negative_feedback",
                    "alpha": 0.6,
                    "target_improvement": "user_satisfaction"
                },
                priority=5,
                timeout_seconds=300,
                requires_approval=True,  # LoRA changes need approval
                dry_run=True  # Start with dry run
            ))
        
        return actions
    
    @staticmethod
    def create_utilization_optimizations(
        patterns: List[Dict[str, Any]]
    ) -> List[MutationAction]:
        """Create mutations to optimize agent utilization.
        
        Args:
            patterns: Usage patterns detected in the analysis
            
        Returns:
            List of mutation actions for utilization optimization
        """
        actions = []
        
        for pattern in patterns:
            if pattern["type"] == "underutilized_agent":
                agent_id = pattern["agent_id"]
                
                # Route more traffic to underutilized agents
                actions.append(MutationAction(
                    action_id=f"route_balance_{uuid.uuid4().hex[:8]}",
                    target="routing_system",
                    operation=MutationOperationType.ROUTE_CHANGE,
                    args={
                        "agent_id": agent_id,
                        "current_weight": pattern.get("usage_percentage", 5) / 100,
                        "target_weight": 0.15,  # Increase to 15%
                        "ramp_up_duration_minutes": 60,
                        "monitoring_required": True
                    },
                    priority=4,
                    timeout_seconds=180
                ))
                
                # Improve agent visibility/promotion
                actions.append(MutationAction(
                    action_id=f"promote_agent_{uuid.uuid4().hex[:8]}",
                    target=f"agent/{agent_id}",
                    operation=MutationOperationType.PARAM_SET,
                    args={
                        "parameter": "visibility_boost",
                        "value": True,
                        "description": f"Increase visibility for underutilized agent",
                        "duration_hours": 24
                    },
                    priority=3,
                    timeout_seconds=30
                ))
            
            elif pattern["type"] == "agent_dominance":
                dominant_agent = pattern["dominant_agent"]
                
                # Redistribute load from dominant agent
                actions.append(MutationAction(
                    action_id=f"load_balance_{uuid.uuid4().hex[:8]}",
                    target="routing_system",
                    operation=MutationOperationType.ROUTE_CHANGE,
                    args={
                        "agent_id": dominant_agent,
                        "current_weight": pattern.get("usage_percentage", 50) / 100,
                        "target_weight": 0.35,  # Reduce to 35%
                        "redistribution_strategy": "capability_based",
                        "gradual_transition": True,
                        "transition_duration_hours": 6
                    },
                    priority=5,
                    timeout_seconds=300
                ))
        
        return actions
    
    @staticmethod
    def _analyze_complaint_patterns(complaints: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Analyze complaint patterns to identify common issues.
        
        Args:
            complaints: List of user complaints
            
        Returns:
            Dictionary mapping complaint types to pattern information
        """
        patterns = {}
        
        # Simple keyword-based pattern detection
        accuracy_keywords = ["wrong", "incorrect", "mistake", "error"]
        helpfulness_keywords = ["unhelpful", "useless", "not helpful", "unclear"]
        speed_keywords = ["slow", "taking too long", "timeout"]
        
        accuracy_complaints = []
        helpfulness_complaints = []
        speed_complaints = []
        
        for complaint in complaints:
            complaint_text = str(complaint.get("feedback", {})).lower()
            
            if any(keyword in complaint_text for keyword in accuracy_keywords):
                accuracy_complaints.append(complaint)
            elif any(keyword in complaint_text for keyword in helpfulness_keywords):
                helpfulness_complaints.append(complaint)
            elif any(keyword in complaint_text for keyword in speed_keywords):
                speed_complaints.append(complaint)
        
        if accuracy_complaints:
            patterns["accuracy"] = {
                "count": len(accuracy_complaints),
                "examples": accuracy_complaints,
                "suggestions": [
                    "Improve fact-checking mechanisms",
                    "Add confidence indicators",
                    "Include source citations"
                ]
            }
        
        if helpfulness_complaints:
            patterns["helpfulness"] = {
                "count": len(helpfulness_complaints),
                "examples": helpfulness_complaints,
                "suggestions": [
                    "Provide more detailed explanations",
                    "Ask clarifying questions",
                    "Offer alternative approaches"
                ]
            }
        
        if speed_complaints:
            patterns["speed"] = {
                "count": len(speed_complaints),
                "examples": speed_complaints,
                "suggestions": [
                    "Optimize response generation",
                    "Implement streaming responses",
                    "Add progress indicators"
                ]
            }
        
        return patterns


class OraclePlanner:
    """Main Oracle planning engine that generates mutation plans from analysis findings."""
    
    def __init__(self, config: Optional[OracleConfig] = None):
        """Initialize the Oracle planner.
        
        Args:
            config: Configuration for the planner
        """
        self.config = config or OracleConfig()
        self.mutation_history = []  # Track recent mutations
        self.planning_stats = {
            "plans_generated": 0,
            "mutations_suggested": 0,
            "high_confidence_plans": 0,
            "safety_blocked_plans": 0
        }
        
        logger.info("OraclePlanner initialized", config=self.config.dict())
    
    async def generate_mutation_plan(self, findings: AnalysisFindings) -> Optional[MutationPlan]:
        """Generate a comprehensive mutation plan from analysis findings.
        
        Args:
            findings: Analysis findings with detected patterns and issues
            
        Returns:
            MutationPlan if mutations are recommended, None otherwise
        """
        try:
            logger.info(
                "Generating mutation plan",
                analysis_id=findings.analysis_id,
                patterns_count=len(findings.patterns),
                issues_count=len(findings.issues)
            )
            
            # Check if we should generate a plan
            if not self._should_generate_plan(findings):
                logger.info("No mutation plan needed based on findings")
                return None
            
            # Check rate limiting
            if not self._check_rate_limits():
                logger.warning("Rate limit exceeded, skipping mutation plan generation")
                self.planning_stats["safety_blocked_plans"] += 1
                return None
            
            # Generate mutation actions
            all_actions = []
            
            # Process patterns to generate actions
            for pattern in findings.patterns:
                actions = self._create_actions_for_pattern(pattern)
                all_actions.extend(actions)
            
            # Process issues to generate actions
            for issue in findings.issues:
                actions = self._create_actions_for_issue(issue)
                all_actions.extend(actions)
            
            if not all_actions:
                logger.info("No mutation actions generated from findings")
                return None
            
            # Prioritize and filter actions
            prioritized_actions = self._prioritize_actions(all_actions)
            
            # Limit concurrent mutations
            if len(prioritized_actions) > self.config.max_concurrent_mutations:
                prioritized_actions = prioritized_actions[:self.config.max_concurrent_mutations]
            
            # Calculate confidence and plan details
            confidence_score = self._calculate_plan_confidence(findings, prioritized_actions)
            rationale = self._generate_rationale(findings, prioritized_actions)
            expected_impact = self._describe_expected_impact(prioritized_actions)
            
            # Determine safety checks needed
            safety_checks = self._determine_safety_checks(prioritized_actions)
            
            # Create the mutation plan
            plan = MutationPlan(
                plan_id=f"plan_{uuid.uuid4().hex}",
                created_at=datetime.utcnow(),
                created_by="oracle_planner",
                rationale=rationale,
                confidence_score=confidence_score,
                expected_impact=expected_impact,
                actions=prioritized_actions,
                safety_checks=safety_checks,
                rollback_key=f"rollback_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                max_rollback_time=300  # 5 minutes
            )
            
            # Update statistics
            self.planning_stats["plans_generated"] += 1
            self.planning_stats["mutations_suggested"] += len(prioritized_actions)
            
            if confidence_score >= self.config.confidence_threshold:
                self.planning_stats["high_confidence_plans"] += 1
            
            # Track in history
            self.mutation_history.append({
                "plan_id": plan.plan_id,
                "created_at": plan.created_at,
                "action_count": len(plan.actions),
                "confidence": confidence_score,
                "findings_id": findings.analysis_id
            })
            
            # Keep history manageable
            if len(self.mutation_history) > 100:
                self.mutation_history = self.mutation_history[-50:]
            
            logger.info(
                "Mutation plan generated successfully",
                plan_id=plan.plan_id,
                actions_count=len(plan.actions),
                confidence_score=confidence_score,
                safety_checks=len(safety_checks)
            )
            
            return plan
            
        except Exception as e:
            logger.error("Error generating mutation plan", error=str(e))
            return None
    
    def _should_generate_plan(self, findings: AnalysisFindings) -> bool:
        """Determine if a mutation plan should be generated.
        
        Args:
            findings: Analysis findings
            
        Returns:
            True if plan should be generated
        """
        # Minimum event threshold
        if findings.event_count < self.config.min_events_for_analysis:
            return False
        
        # Must have patterns or issues
        if not findings.patterns and not findings.issues:
            return False
        
        # Check for high-confidence patterns or critical issues
        has_significant_findings = any(
            pattern.get("confidence", 0) > 0.7 or pattern.get("severity") == "high"
            for pattern in findings.patterns
        )
        
        has_critical_issues = any(
            issue.get("severity") in ["high", "critical"]
            for issue in findings.issues
        )
        
        return has_significant_findings or has_critical_issues
    
    def _check_rate_limits(self) -> bool:
        """Check if rate limits allow for new mutation plan.
        
        Returns:
            True if within rate limits
        """
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        # Count recent plans
        recent_plans = [
            entry for entry in self.mutation_history
            if entry["created_at"] > one_hour_ago
        ]
        
        return len(recent_plans) < self.config.max_mutations_per_hour
    
    def _create_actions_for_pattern(self, pattern: Dict[str, Any]) -> List[MutationAction]:
        """Create mutation actions for a detected pattern.
        
        Args:
            pattern: Detected pattern from analysis
            
        Returns:
            List of mutation actions
        """
        actions = []
        
        pattern_type = pattern.get("type")
        confidence = pattern.get("confidence", 0.5)
        
        if pattern_type == "performance_degradation":
            actions.extend(MutationStrategy.create_performance_optimizations(
                agent_id=pattern.get("agent_id"),
                degradation_metrics=pattern.get("metrics", {}),
                confidence=confidence
            ))
        
        elif pattern_type == "user_dissatisfaction":
            actions.extend(MutationStrategy.create_satisfaction_improvements(
                agent_id=pattern.get("agent_id"),
                satisfaction_metrics=pattern.get("metrics", {}),
                complaints=None  # Would need to pass complaint data
            ))
        
        elif pattern_type in ["underutilized_agent", "agent_dominance"]:
            actions.extend(MutationStrategy.create_utilization_optimizations([pattern]))
        
        return actions
    
    def _create_actions_for_issue(self, issue: Dict[str, Any]) -> List[MutationAction]:
        """Create mutation actions for an identified issue.
        
        Args:
            issue: Identified issue from analysis
            
        Returns:
            List of mutation actions
        """
        actions = []
        
        issue_type = issue.get("type")
        severity = issue.get("severity", "medium")
        
        if issue_type == "critical_performance_issue":
            # Immediate performance fixes
            actions.append(MutationAction(
                action_id=f"urgent_perf_{uuid.uuid4().hex[:8]}",
                target=f"agent/{issue.get('agent_id')}",
                operation=MutationOperationType.PARAM_SET,
                args={
                    "parameter": "max_response_time_ms",
                    "value": 5000,  # 5 second limit
                    "urgent": True,
                    "reason": "Critical performance issue detected"
                },
                priority=10,  # Highest priority
                timeout_seconds=30
            ))
        
        elif issue_type == "user_satisfaction_issue":
            # User satisfaction improvements
            actions.extend(MutationStrategy.create_satisfaction_improvements(
                agent_id=issue.get("agent_id"),
                satisfaction_metrics=issue.get("metrics", {})
            ))
        
        elif issue_type == "user_complaint_issue":
            # Address complaints directly
            actions.append(MutationAction(
                action_id=f"complaint_response_{uuid.uuid4().hex[:8]}",
                target=f"agent/{issue.get('agent_id')}",
                operation=MutationOperationType.FEATURE_TOGGLE,
                args={
                    "feature": "enhanced_explanation_mode",
                    "enabled": True,
                    "reason": f"Response to {issue.get('complaint_count', 0)} user complaints",
                    "trial_duration_hours": 48
                },
                priority=7,
                timeout_seconds=60
            ))
        
        return actions
    
    def _prioritize_actions(self, actions: List[MutationAction]) -> List[MutationAction]:
        """Prioritize and filter mutation actions.
        
        Args:
            actions: List of mutation actions to prioritize
            
        Returns:
            Prioritized list of actions
        """
        # Sort by priority (higher = more important)
        actions.sort(key=lambda a: a.priority, reverse=True)
        
        # Remove duplicate targets (keep highest priority)
        seen_targets = set()
        filtered_actions = []
        
        for action in actions:
            target_key = f"{action.target}:{action.operation.value}"
            
            if target_key not in seen_targets:
                filtered_actions.append(action)
                seen_targets.add(target_key)
        
        return filtered_actions
    
    def _calculate_plan_confidence(
        self, 
        findings: AnalysisFindings, 
        actions: List[MutationAction]
    ) -> float:
        """Calculate confidence score for the mutation plan.
        
        Args:
            findings: Analysis findings
            actions: Planned mutation actions
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence from findings
        pattern_confidences = [
            pattern.get("confidence", 0.5) 
            for pattern in findings.patterns
        ]
        
        if pattern_confidences:
            base_confidence = sum(pattern_confidences) / len(pattern_confidences)
        else:
            base_confidence = 0.5
        
        # Adjust based on event count
        event_factor = min(findings.event_count / 50, 1.0)  # Max confidence at 50+ events
        
        # Adjust based on action complexity
        high_risk_operations = {
            MutationOperationType.MODEL_SWAP,
            MutationOperationType.LORA_APPLY,
            MutationOperationType.ROUTE_CHANGE
        }
        
        risk_factor = 1.0
        for action in actions:
            if action.operation in high_risk_operations:
                risk_factor *= 0.9  # Reduce confidence for risky operations
        
        final_confidence = base_confidence * event_factor * risk_factor
        
        return min(max(final_confidence, 0.0), 1.0)
    
    def _generate_rationale(
        self, 
        findings: AnalysisFindings, 
        actions: List[MutationAction]
    ) -> str:
        """Generate human-readable rationale for the mutation plan.
        
        Args:
            findings: Analysis findings
            actions: Planned mutation actions
            
        Returns:
            Rationale string
        """
        rationale_parts = []
        
        # Summarize findings
        if findings.patterns:
            pattern_types = [p.get("type") for p in findings.patterns]
            rationale_parts.append(
                f"Analysis of {findings.event_count} events over {findings.time_window_hours}h "
                f"revealed {len(findings.patterns)} significant patterns: {', '.join(set(pattern_types))}"
            )
        
        if findings.issues:
            issue_types = [i.get("type") for i in findings.issues]
            rationale_parts.append(
                f"Identified {len(findings.issues)} issues requiring attention: {', '.join(set(issue_types))}"
            )
        
        # Summarize planned actions
        action_types = [a.operation.value for a in actions]
        rationale_parts.append(
            f"Proposing {len(actions)} optimizations: {', '.join(set(action_types))}"
        )
        
        # Add performance context
        perf_metrics = findings.performance_metrics
        if perf_metrics.get("avg_response_time_ms"):
            rationale_parts.append(
                f"Current avg response time: {perf_metrics['avg_response_time_ms']:.0f}ms"
            )
        
        if perf_metrics.get("avg_success_rate"):
            rationale_parts.append(
                f"Current success rate: {perf_metrics['avg_success_rate']*100:.1f}%"
            )
        
        return " | ".join(rationale_parts)
    
    def _describe_expected_impact(self, actions: List[MutationAction]) -> str:
        """Describe expected impact of the mutation plan.
        
        Args:
            actions: Planned mutation actions
            
        Returns:
            Expected impact description
        """
        impact_areas = set()
        
        for action in actions:
            if action.operation in [
                MutationOperationType.PROMPT_PATCH, 
                MutationOperationType.MODEL_SWAP
            ]:
                impact_areas.add("response_quality")
            
            if "performance" in action.args.get("description", "").lower():
                impact_areas.add("response_time")
            
            if action.operation == MutationOperationType.ROUTE_CHANGE:
                impact_areas.add("load_distribution")
            
            if "satisfaction" in action.args.get("description", "").lower():
                impact_areas.add("user_satisfaction")
        
        if not impact_areas:
            return "General system optimization improvements"
        
        impact_descriptions = {
            "response_quality": "improved response accuracy and relevance",
            "response_time": "faster response generation",
            "load_distribution": "better resource utilization",
            "user_satisfaction": "higher user satisfaction ratings"
        }
        
        expected_impacts = [
            impact_descriptions.get(area, area) 
            for area in impact_areas
        ]
        
        return f"Expected improvements: {', '.join(expected_impacts)}"
    
    def _determine_safety_checks(self, actions: List[MutationAction]) -> List[SafetyCheckType]:
        """Determine what safety checks are needed for the plan.
        
        Args:
            actions: Planned mutation actions
            
        Returns:
            List of required safety checks
        """
        safety_checks = set()
        
        # Always run policy validation
        safety_checks.add(SafetyCheckType.POLICY_VALIDATION)
        
        # Check for operations that need specific validations
        for action in actions:
            if action.operation in [
                MutationOperationType.MODEL_SWAP,
                MutationOperationType.LORA_APPLY
            ]:
                safety_checks.add(SafetyCheckType.REGRESSION_TEST)
                safety_checks.add(SafetyCheckType.PERFORMANCE_CHECK)
            
            if action.operation == MutationOperationType.ROUTE_CHANGE:
                safety_checks.add(SafetyCheckType.CANARY_DEPLOYMENT)
            
            if action.requires_approval:
                safety_checks.add(SafetyCheckType.SECURITY_SCAN)
        
        return list(safety_checks)
    
    async def get_planning_stats(self) -> Dict[str, Any]:
        """Get statistics about plan generation.
        
        Returns:
            Dictionary with planning statistics
        """
        recent_plans = len([
            entry for entry in self.mutation_history
            if entry["created_at"] > datetime.utcnow() - timedelta(hours=24)
        ])
        
        return {
            **self.planning_stats,
            "recent_plans_24h": recent_plans,
            "avg_actions_per_plan": (
                self.planning_stats["mutations_suggested"] / 
                max(self.planning_stats["plans_generated"], 1)
            ),
            "high_confidence_rate": (
                self.planning_stats["high_confidence_plans"] / 
                max(self.planning_stats["plans_generated"], 1)
            )
        }