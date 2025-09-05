"""FastAPI router for Oracle decision engine endpoints."""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import structlog

from services.shared.schemas import (
    AnalysisFindings, MutationPlan, MutationAction, 
    EventEnvelope, ValidationResult
)
from services.event_bus.bus import get_default_event_bus
from .analyzer import FeedbackAnalyzer
from .planner import OraclePlanner
from .validator import SafetyValidator

logger = structlog.get_logger(__name__)

# Create router
oracle_router = APIRouter()

# Global instances (would use dependency injection in production)
_analyzer: Optional[FeedbackAnalyzer] = None
_planner: Optional[OraclePlanner] = None
_validator: Optional[SafetyValidator] = None


def get_analyzer() -> FeedbackAnalyzer:
    """Get feedback analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = FeedbackAnalyzer()
    return _analyzer


def get_planner() -> OraclePlanner:
    """Get Oracle planner instance."""
    global _planner
    if _planner is None:
        _planner = OraclePlanner()
    return _planner


def get_validator() -> SafetyValidator:
    """Get safety validator instance."""
    global _validator
    if _validator is None:
        _validator = SafetyValidator()
    return _validator


# Request/Response models
class AnalyzeRequest(BaseModel):
    """Request model for feedback analysis."""
    
    time_window_hours: int = Field(default=24, ge=1, le=168, description="Analysis time window")
    event_limit: int = Field(default=1000, ge=10, le=10000, description="Maximum events to analyze")
    force_analysis: bool = Field(default=False, description="Force analysis even with few events")


class AnalyzeResponse(BaseModel):
    """Response model for feedback analysis."""
    
    analysis: AnalysisFindings
    message: str
    processing_time_seconds: float


class PlanRequest(BaseModel):
    """Request model for mutation plan generation."""
    
    analysis_id: Optional[str] = Field(None, description="ID of analysis to base plan on")
    findings: Optional[AnalysisFindings] = Field(None, description="Analysis findings to use")
    force_planning: bool = Field(default=False, description="Force planning even with low confidence")


class PlanResponse(BaseModel):
    """Response model for mutation plan generation."""
    
    plan: Optional[MutationPlan] = Field(None, description="Generated mutation plan")
    message: str
    planning_time_seconds: float
    recommendations: List[str] = Field(default_factory=list)


class ValidateRequest(BaseModel):
    """Request model for plan validation."""
    
    plan: MutationPlan = Field(..., description="Mutation plan to validate")
    skip_slow_checks: bool = Field(default=False, description="Skip time-consuming validation checks")


class ValidateResponse(BaseModel):
    """Response model for plan validation."""
    
    validation_results: Dict[str, ValidationResult]
    overall_passed: bool
    message: str
    validation_time_seconds: float


class ExecuteRequest(BaseModel):
    """Request model for plan execution."""
    
    plan: MutationPlan = Field(..., description="Mutation plan to execute")
    dry_run: bool = Field(default=True, description="Execute as simulation only")
    force_execution: bool = Field(default=False, description="Skip additional safety checks")


class ExecuteResponse(BaseModel):
    """Response model for plan execution."""
    
    execution_id: str
    status: str
    message: str
    executed_actions: List[str] = Field(default_factory=list)
    failed_actions: List[str] = Field(default_factory=list)


class OracleStatusResponse(BaseModel):
    """Response model for Oracle system status."""
    
    status: str
    uptime_hours: float
    analysis_stats: Dict[str, Any]
    planning_stats: Dict[str, Any]
    validation_stats: Dict[str, Any]
    event_bus_stats: Dict[str, Any]
    recent_activity: List[Dict[str, Any]]


@oracle_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_feedback(
    request: AnalyzeRequest,
    http_request: Request,
    analyzer: FeedbackAnalyzer = Depends(get_analyzer)
) -> AnalyzeResponse:
    """Analyze feedback events for patterns and insights.
    
    This endpoint retrieves recent feedback events from the event bus,
    analyzes them for patterns, and returns findings with recommendations.
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info(
            "Starting feedback analysis",
            time_window_hours=request.time_window_hours,
            event_limit=request.event_limit
        )
        
        # Get event bus and retrieve events
        event_bus = await get_default_event_bus()
        
        # Subscribe to get events (simplified - in production would use proper subscriber)
        events = []  # Would implement proper event retrieval here
        
        # For demo, create some sample events
        sample_events = await _create_sample_events(request.event_limit)
        
        # Analyze the events
        findings = await analyzer.analyze_feedback_batch(
            sample_events, 
            request.time_window_hours
        )
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        message = (
            f"Analyzed {findings.event_count} events over {request.time_window_hours}h window. "
            f"Found {len(findings.patterns)} patterns and {len(findings.issues)} issues."
        )
        
        logger.info(
            "Feedback analysis completed",
            analysis_id=findings.analysis_id,
            patterns_found=len(findings.patterns),
            issues_found=len(findings.issues),
            processing_time=processing_time
        )
        
        return AnalyzeResponse(
            analysis=findings,
            message=message,
            processing_time_seconds=processing_time
        )
        
    except Exception as e:
        logger.error("Error in feedback analysis", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@oracle_router.post("/plan", response_model=PlanResponse)
async def generate_mutation_plan(
    request: PlanRequest,
    http_request: Request,
    planner: OraclePlanner = Depends(get_planner)
) -> PlanResponse:
    """Generate a mutation plan based on analysis findings.
    
    This endpoint takes analysis findings and generates a comprehensive
    mutation plan with safety checks and rollback mechanisms.
    """
    start_time = datetime.utcnow()
    
    try:
        # Get findings either from request or by analysis_id
        if request.findings:
            findings = request.findings
        elif request.analysis_id:
            # In production, would retrieve from storage
            raise HTTPException(
                status_code=400,
                detail="Analysis retrieval by ID not implemented in demo"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'findings' or 'analysis_id'"
            )
        
        logger.info(
            "Generating mutation plan",
            analysis_id=findings.analysis_id,
            patterns=len(findings.patterns),
            issues=len(findings.issues)
        )
        
        # Generate the mutation plan
        plan = await planner.generate_mutation_plan(findings)
        
        planning_time = (datetime.utcnow() - start_time).total_seconds()
        
        if plan:
            message = (
                f"Generated mutation plan with {len(plan.actions)} actions. "
                f"Confidence: {plan.confidence_score:.2f}. "
                f"Safety checks: {len(plan.safety_checks)}."
            )
            
            recommendations = findings.recommendations
            
            logger.info(
                "Mutation plan generated",
                plan_id=plan.plan_id,
                actions=len(plan.actions),
                confidence=plan.confidence_score,
                planning_time=planning_time
            )
        else:
            message = "No mutation plan generated - insufficient evidence or confidence."
            recommendations = ["Collect more feedback data", "Monitor system performance"]
            
            logger.info("No mutation plan generated", reason="insufficient_confidence")
        
        return PlanResponse(
            plan=plan,
            message=message,
            planning_time_seconds=planning_time,
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error("Error generating mutation plan", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Planning failed: {str(e)}"
        )


@oracle_router.post("/validate", response_model=ValidateResponse)
async def validate_mutation_plan(
    request: ValidateRequest,
    http_request: Request,
    validator: SafetyValidator = Depends(get_validator)
) -> ValidateResponse:
    """Validate a mutation plan for safety and feasibility.
    
    This endpoint runs comprehensive safety checks on a mutation plan,
    including policy validation, regression tests, and security scans.
    """
    start_time = datetime.utcnow()
    
    try:
        plan = request.plan
        
        logger.info(
            "Validating mutation plan",
            plan_id=plan.plan_id,
            actions=len(plan.actions),
            safety_checks=len(plan.safety_checks)
        )
        
        # Run safety validation
        validation_results = await validator.validate_mutation_plan(plan)
        
        # Determine overall result
        overall_passed = all(result.passed for result in validation_results.values())
        
        validation_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Generate message
        passed_checks = sum(1 for result in validation_results.values() if result.passed)
        total_checks = len(validation_results)
        
        if overall_passed:
            message = f"All {total_checks} safety checks passed. Plan approved for execution."
        else:
            failed_checks = total_checks - passed_checks
            message = f"{failed_checks} of {total_checks} safety checks failed. Plan requires review."
        
        logger.info(
            "Plan validation completed",
            plan_id=plan.plan_id,
            overall_passed=overall_passed,
            passed_checks=passed_checks,
            total_checks=total_checks,
            validation_time=validation_time
        )
        
        return ValidateResponse(
            validation_results=validation_results,
            overall_passed=overall_passed,
            message=message,
            validation_time_seconds=validation_time
        )
        
    except Exception as e:
        logger.error("Error validating mutation plan", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Validation failed: {str(e)}"
        )


@oracle_router.post("/execute", response_model=ExecuteResponse)
async def execute_mutation_plan(
    request: ExecuteRequest,
    http_request: Request,
    background_tasks: BackgroundTasks
) -> ExecuteResponse:
    """Execute a validated mutation plan.
    
    This endpoint executes approved mutation actions with monitoring
    and rollback capabilities. Can be run in dry-run mode for testing.
    """
    try:
        plan = request.plan
        
        logger.info(
            "Executing mutation plan",
            plan_id=plan.plan_id,
            actions=len(plan.actions),
            dry_run=request.dry_run
        )
        
        if not request.dry_run and not request.force_execution:
            # In production, would check if plan is validated and approved
            logger.warning("Production execution requires validation - use dry_run or force_execution")
        
        # Generate execution ID
        execution_id = f"exec_{plan.plan_id}_{int(datetime.utcnow().timestamp())}"
        
        # Start background execution task
        background_tasks.add_task(
            _execute_plan_background,
            plan,
            execution_id,
            request.dry_run
        )
        
        return ExecuteResponse(
            execution_id=execution_id,
            status="started",
            message=f"Plan execution started ({'dry-run' if request.dry_run else 'live'}) with ID: {execution_id}",
            executed_actions=[],
            failed_actions=[]
        )
        
    except Exception as e:
        logger.error("Error executing mutation plan", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Execution failed: {str(e)}"
        )


@oracle_router.get("/status", response_model=OracleStatusResponse)
async def get_oracle_status(
    analyzer: FeedbackAnalyzer = Depends(get_analyzer),
    planner: OraclePlanner = Depends(get_planner),
    validator: SafetyValidator = Depends(get_validator)
) -> OracleStatusResponse:
    """Get comprehensive Oracle system status and statistics.
    
    This endpoint provides health information, performance metrics,
    and recent activity for monitoring and debugging.
    """
    try:
        # Get event bus stats
        event_bus = await get_default_event_bus()
        bus_stats = await event_bus.get_stats()
        
        # Get component stats
        planning_stats = await planner.get_planning_stats()
        validation_stats = await validator.get_validation_stats()
        
        # Calculate uptime (simplified)
        uptime_hours = 24.0  # Would track actual start time
        
        # Recent activity (simplified)
        recent_activity = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "type": "status_check",
                "description": "Oracle status requested"
            }
        ]
        
        return OracleStatusResponse(
            status="healthy",
            uptime_hours=uptime_hours,
            analysis_stats={
                "analyses_run": 42,  # Would track actual numbers
                "avg_processing_time_seconds": 2.3,
                "patterns_detected_total": 156
            },
            planning_stats=planning_stats,
            validation_stats=validation_stats,
            event_bus_stats={
                "events_published": bus_stats.get("events_published", 0),
                "events_delivered": bus_stats.get("events_delivered", 0),
                "active_subscriptions": bus_stats.get("active_subscriptions", 0)
            },
            recent_activity=recent_activity
        )
        
    except Exception as e:
        logger.error("Error getting Oracle status", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Status retrieval failed: {str(e)}"
        )


@oracle_router.post("/tick")
async def oracle_tick(
    background_tasks: BackgroundTasks,
    analyzer: FeedbackAnalyzer = Depends(get_analyzer),
    planner: OraclePlanner = Depends(get_planner),
    validator: SafetyValidator = Depends(get_validator)
):
    """Trigger Oracle processing cycle (analyze → plan → validate → execute).
    
    This endpoint runs the complete Oracle feedback loop:
    1. Analyze recent feedback events
    2. Generate mutation plan if needed
    3. Validate plan for safety
    4. Execute approved actions
    
    Designed to be called periodically by schedulers or webhooks.
    """
    try:
        logger.info("Oracle processing tick started")
        
        # Start background processing
        background_tasks.add_task(
            _oracle_tick_background,
            analyzer,
            planner,
            validator
        )
        
        return {
            "status": "started",
            "message": "Oracle processing cycle initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Error in Oracle tick", error=str(e))
        raise HTTPException(
            status_code=500,
            detail=f"Oracle tick failed: {str(e)}"
        )


# Background task functions
async def _oracle_tick_background(
    analyzer: FeedbackAnalyzer,
    planner: OraclePlanner, 
    validator: SafetyValidator
):
    """Background task for complete Oracle processing cycle."""
    try:
        logger.info("Starting Oracle background processing")
        
        # Step 1: Analyze recent feedback
        sample_events = await _create_sample_events(100)
        findings = await analyzer.analyze_feedback_batch(sample_events, 24)
        
        logger.info(
            "Analysis completed",
            analysis_id=findings.analysis_id,
            patterns=len(findings.patterns),
            issues=len(findings.issues)
        )
        
        # Step 2: Generate mutation plan if warranted
        plan = await planner.generate_mutation_plan(findings)
        
        if not plan:
            logger.info("No mutation plan generated")
            return
        
        logger.info(
            "Plan generated",
            plan_id=plan.plan_id,
            actions=len(plan.actions),
            confidence=plan.confidence_score
        )
        
        # Step 3: Validate plan
        validation_results = await validator.validate_mutation_plan(plan)
        overall_passed = all(result.passed for result in validation_results.values())
        
        logger.info(
            "Plan validated",
            plan_id=plan.plan_id,
            passed=overall_passed,
            checks=len(validation_results)
        )
        
        # Step 4: Execute if approved (dry-run for safety)
        if overall_passed:
            await _execute_plan_background(plan, f"auto_{plan.plan_id}", dry_run=True)
        else:
            logger.info("Plan execution skipped - validation failed")
        
        logger.info("Oracle background processing completed")
        
    except Exception as e:
        logger.error("Error in Oracle background processing", error=str(e))


async def _execute_plan_background(plan: MutationPlan, execution_id: str, dry_run: bool = True):
    """Background task for plan execution."""
    try:
        logger.info(
            "Starting plan execution",
            plan_id=plan.plan_id,
            execution_id=execution_id,
            dry_run=dry_run
        )
        
        executed_actions = []
        failed_actions = []
        
        # Execute each action
        for action in plan.actions:
            try:
                if dry_run:
                    # Simulate execution
                    await asyncio.sleep(0.1)
                    logger.info(
                        "DRY RUN: Would execute action",
                        action_id=action.action_id,
                        operation=action.operation.value,
                        target=action.target
                    )
                    executed_actions.append(action.action_id)
                else:
                    # Real execution would go here
                    logger.info(
                        "LIVE: Executing action",
                        action_id=action.action_id,
                        operation=action.operation.value,
                        target=action.target
                    )
                    
                    # Placeholder for real execution logic
                    success = await _execute_single_action(action)
                    
                    if success:
                        executed_actions.append(action.action_id)
                    else:
                        failed_actions.append(action.action_id)
                        
            except Exception as e:
                logger.error(
                    "Action execution failed",
                    action_id=action.action_id,
                    error=str(e)
                )
                failed_actions.append(action.action_id)
        
        logger.info(
            "Plan execution completed",
            execution_id=execution_id,
            executed=len(executed_actions),
            failed=len(failed_actions),
            dry_run=dry_run
        )
        
    except Exception as e:
        logger.error("Error in plan execution", error=str(e), execution_id=execution_id)


async def _execute_single_action(action: MutationAction) -> bool:
    """Execute a single mutation action.
    
    Args:
        action: The mutation action to execute
        
    Returns:
        True if execution succeeded
    """
    try:
        # This would contain the actual implementation logic for each operation type
        if action.operation.value == "prompt.patch":
            # Apply prompt patches
            logger.info("Applying prompt patch", target=action.target)
            
        elif action.operation.value == "model.swap":
            # Swap AI models
            logger.info("Swapping model", target=action.target)
            
        elif action.operation.value.startswith("lora."):
            # LoRA operations
            logger.info("LoRA operation", operation=action.operation.value, target=action.target)
            
        elif action.operation.value == "param.set":
            # Set parameters
            logger.info("Setting parameter", target=action.target)
            
        elif action.operation.value == "route.change":
            # Route changes
            logger.info("Changing route", target=action.target)
            
        else:
            logger.warning("Unknown operation type", operation=action.operation.value)
            return False
        
        # Simulate some processing time
        await asyncio.sleep(0.5)
        
        return True
        
    except Exception as e:
        logger.error("Single action execution failed", action_id=action.action_id, error=str(e))
        return False


async def _create_sample_events(count: int) -> List[EventEnvelope]:
    """Create sample events for demonstration purposes.
    
    Args:
        count: Number of sample events to create
        
    Returns:
        List of sample EventEnvelope objects
    """
    # This would be replaced with actual event retrieval from the event bus
    sample_events = []
    
    # Create some sample feedback events for demonstration
    for i in range(min(count, 50)):
        envelope = EventEnvelope(
            envelope_id=f"sample_event_{i}",
            event_type="feedback.implicit",
            payload={
                "event_id": f"feedback_sample_{i}",
                "event_type": "feedback.implicit",
                "agent_id": f"agent_{i % 3}",  # 3 different agents
                "session_id": f"session_{i}",
                "timestamp": datetime.utcnow().isoformat(),
                "context": {"query": f"Sample query {i}"},
                "explicit": {},
                "implicit": {
                    "response_time_ms": 200 + (i % 100),  # Varying response times
                    "success_rate": 0.9 - (i % 10) * 0.05,  # Varying success rates
                },
                "artifacts": {},
                "metadata": {}
            },
            source_service="demo_generator",
            target_services=["oracle_api"],
            created_at=datetime.utcnow()
        )
        sample_events.append(envelope)
    
    return sample_events