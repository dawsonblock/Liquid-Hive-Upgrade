"""Shared Pydantic schemas for the Feedback Loop + Oracle Meta-Loop system."""

from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    """Types of events in the system."""
    FEEDBACK_EXPLICIT = "feedback.explicit"  # User ratings, corrections
    FEEDBACK_IMPLICIT = "feedback.implicit"  # Usage patterns, success rates
    SYSTEM_METRIC = "system.metric"          # Performance, errors
    MUTATION_PLAN = "mutation.plan"          # Proposed changes
    MUTATION_RESULT = "mutation.result"      # Results of applied changes
    SAFETY_ALERT = "safety.alert"           # Security or safety concerns


class FeedbackEvent(BaseModel):
    """Core feedback event from user interactions or system monitoring."""
    
    # Identity and context
    event_id: str = Field(..., description="Unique event identifier")
    event_type: EventType = Field(..., description="Type of feedback event")
    agent_id: str = Field(..., description="ID of the agent being evaluated")
    session_id: str = Field(..., description="User session identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Context information
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Contextual information (query, conversation history, etc.)"
    )
    
    # Explicit feedback (user-provided)
    explicit: Dict[str, Any] = Field(
        default_factory=dict,
        description="Direct user feedback (ratings, corrections, preferences)"
    )
    
    # Implicit feedback (system-observed)
    implicit: Dict[str, float] = Field(
        default_factory=dict,
        description="Behavioral signals (click-through rates, dwell time, success rates)"
    )
    
    # Artifacts and evidence
    artifacts: Dict[str, str] = Field(
        default_factory=dict,
        description="Paths or references to logs, outputs, error traces"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for processing"
    )


class MutationOperationType(str, Enum):
    """Types of mutations that can be applied to the system."""
    PROMPT_PATCH = "prompt.patch"        # Modify system/user prompts
    MODEL_SWAP = "model.swap"           # Change AI model routing
    LORA_APPLY = "lora.apply"           # Apply LoRA adaptation
    LORA_REMOVE = "lora.remove"         # Remove LoRA adaptation
    PARAM_SET = "param.set"             # Update system parameters
    MEMORY_UPDATE = "memory.update"      # Update agent memory/context
    ROUTE_CHANGE = "route.change"       # Modify request routing
    FEATURE_TOGGLE = "feature.toggle"   # Enable/disable features


class MutationAction(BaseModel):
    """A single mutation action to be applied to the system."""
    
    action_id: str = Field(..., description="Unique action identifier")
    target: str = Field(..., description="Target component (agent_id, model_route, etc.)")
    operation: MutationOperationType = Field(..., description="Type of operation to perform")
    
    # Operation parameters
    args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments specific to the operation type"
    )
    
    # Execution context
    priority: int = Field(default=5, ge=1, le=10, description="Execution priority (1=highest)")
    timeout_seconds: int = Field(default=30, description="Maximum execution time")
    rollback_on_failure: bool = Field(default=True, description="Auto-rollback if action fails")
    
    # Validation and safety
    requires_approval: bool = Field(default=False, description="Requires manual approval")
    dry_run: bool = Field(default=False, description="Execute as simulation only")


class SafetyCheckType(str, Enum):
    """Types of safety checks that can be performed."""
    POLICY_VALIDATION = "policy.validation"    # Check against safety policies
    REGRESSION_TEST = "regression.test"        # Run regression test suite
    CANARY_DEPLOYMENT = "canary.deployment"    # Gradual rollout validation
    PERFORMANCE_CHECK = "performance.check"    # Performance impact assessment
    SECURITY_SCAN = "security.scan"           # Security vulnerability check


class MutationPlan(BaseModel):
    """A complete plan for system mutations based on feedback analysis."""
    
    # Plan identity
    plan_id: str = Field(..., description="Unique plan identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="oracle_system", description="Entity that created the plan")
    
    # Plan details
    rationale: str = Field(..., description="Explanation of why these changes are needed")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence in plan effectiveness")
    expected_impact: str = Field(..., description="Expected impact description")
    
    # Actions to execute
    actions: List[MutationAction] = Field(..., description="List of mutations to apply")
    
    # Safety and validation
    safety_checks: List[SafetyCheckType] = Field(
        default_factory=list,
        description="Safety checks to perform before execution"
    )
    
    # Rollback configuration
    rollback_key: str = Field(..., description="Key for rollback identification")
    max_rollback_time: int = Field(default=300, description="Max time for rollback (seconds)")
    
    # Execution metadata
    status: Literal["pending", "approved", "executing", "completed", "failed", "rolled_back"] = Field(
        default="pending"
    )
    execution_log: List[str] = Field(default_factory=list)


class AnalysisFindings(BaseModel):
    """Results of feedback analysis showing patterns and insights."""
    
    # Analysis metadata
    analysis_id: str = Field(..., description="Unique analysis identifier")
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    event_count: int = Field(..., ge=0, description="Number of events analyzed")
    time_window_hours: int = Field(..., ge=1, description="Analysis time window")
    
    # Pattern detection
    patterns: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detected patterns in feedback data"
    )
    
    # Performance metrics
    performance_metrics: Dict[str, float] = Field(
        default_factory=dict,
        description="Key performance indicators from analysis"
    )
    
    # Issues identified
    issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Problems or concerns identified"
    )
    
    # Recommendations
    recommendations: List[str] = Field(
        default_factory=list,
        description="Suggested improvements"
    )
    
    # Statistical significance
    confidence_intervals: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="Statistical confidence for metrics"
    )


class SystemHealthMetric(BaseModel):
    """System health and performance metrics."""
    
    metric_name: str = Field(..., description="Name of the metric")
    value: float = Field(..., description="Current metric value")
    unit: str = Field(..., description="Unit of measurement")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Thresholds and alerting
    warning_threshold: Optional[float] = Field(None, description="Warning level threshold")
    critical_threshold: Optional[float] = Field(None, description="Critical level threshold")
    is_healthy: bool = Field(True, description="Whether metric is in healthy range")
    
    # Context
    component: str = Field(..., description="Component this metric relates to")
    tags: Dict[str, str] = Field(default_factory=dict, description="Additional tags/labels")


class ValidationResult(BaseModel):
    """Result of safety validation or testing."""
    
    check_type: SafetyCheckType = Field(..., description="Type of check performed")
    passed: bool = Field(..., description="Whether validation passed")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Validation score if applicable")
    
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed results and findings"
    )
    
    errors: List[str] = Field(default_factory=list, description="Error messages if any")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    
    execution_time_seconds: float = Field(..., ge=0.0, description="Time taken to execute check")
    checked_at: datetime = Field(default_factory=datetime.utcnow)


# Event wrapper for the event bus
class EventEnvelope(BaseModel):
    """Wrapper for events in the event bus system."""
    
    envelope_id: str = Field(..., description="Unique envelope identifier")
    event_type: str = Field(..., description="Type of the wrapped event")
    payload: Dict[str, Any] = Field(..., description="The actual event data")
    
    # Routing information
    source_service: str = Field(..., description="Service that generated the event")
    target_services: List[str] = Field(
        default_factory=list,
        description="Services that should receive this event"
    )
    
    # Processing metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_attempts: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=3, ge=1)
    
    # Correlation and tracing
    correlation_id: Optional[str] = Field(None, description="For request correlation")
    parent_event_id: Optional[str] = Field(None, description="Parent event if this is derived")


# Configuration schemas
class OracleConfig(BaseModel):
    """Configuration for the Oracle decision engine."""
    
    # Analysis settings
    min_events_for_analysis: int = Field(default=10, ge=1)
    analysis_window_hours: int = Field(default=24, ge=1)
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Mutation limits
    max_mutations_per_hour: int = Field(default=10, ge=1)
    max_concurrent_mutations: int = Field(default=3, ge=1)
    
    # Safety settings
    require_approval_for_high_impact: bool = Field(default=True)
    auto_rollback_on_failure: bool = Field(default=True)
    canary_percentage: float = Field(default=0.05, ge=0.01, le=0.5)


class EventBusConfig(BaseModel):
    """Configuration for the event bus system."""
    
    # Storage settings
    max_queue_size: int = Field(default=10000, ge=100)
    event_retention_hours: int = Field(default=72, ge=1)
    
    # Processing settings
    batch_size: int = Field(default=100, ge=1, le=1000)
    processing_interval_seconds: int = Field(default=5, ge=1)
    
    # Reliability settings
    max_retry_attempts: int = Field(default=3, ge=1)
    retry_backoff_seconds: int = Field(default=2, ge=1)