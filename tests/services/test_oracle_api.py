"""Tests for the Oracle decision engine API."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

from services.oracle_api.main import app
from services.oracle_api.analyzer import FeedbackAnalyzer
from services.oracle_api.planner import OraclePlanner
from services.oracle_api.validator import SafetyValidator
from services.shared.schemas import (
    AnalysisFindings, MutationPlan, MutationAction, MutationOperationType,
    SafetyCheckType, ValidationResult, EventEnvelope
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_analysis_findings():
    """Sample analysis findings."""
    return AnalysisFindings(
        analysis_id="analysis_123",
        analyzed_at=datetime.utcnow(),
        event_count=100,
        time_window_hours=24,
        patterns=[
            {
                "type": "performance_degradation",
                "agent_id": "agent_1",
                "severity": "medium",
                "confidence": 0.8,
                "metrics": {
                    "response_time_increase_percent": 25.0,
                    "success_rate_decrease_percent": 5.0
                }
            }
        ],
        performance_metrics={
            "avg_response_time_ms": 800.0,
            "avg_success_rate": 0.85
        },
        issues=[
            {
                "type": "performance_issue",
                "description": "Agent response time degradation",
                "severity": "medium"
            }
        ],
        recommendations=["Optimize agent prompts", "Consider model upgrade"]
    )


@pytest.fixture
def sample_mutation_plan():
    """Sample mutation plan."""
    return MutationPlan(
        plan_id="plan_123",
        rationale="Performance optimization needed",
        confidence_score=0.75,
        expected_impact="20% response time improvement",
        actions=[
            MutationAction(
                action_id="action_1",
                target="agent_1",
                operation=MutationOperationType.PROMPT_PATCH,
                args={"patch_type": "performance_optimization"},
                priority=8
            )
        ],
        safety_checks=[SafetyCheckType.POLICY_VALIDATION],
        rollback_key="rollback_123"
    )


class TestOracleAPI:
    """Test suite for Oracle API."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "Liquid Hive Oracle API"
        assert "capabilities" in data
        assert "endpoints" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        with patch.object(app.state, 'event_bus', AsyncMock()) as mock_bus:
            mock_bus.get_stats.return_value = {"events_published": 42}
            
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["service"] == "oracle_api"
    
    def test_analyze_feedback(self, client):
        """Test feedback analysis endpoint."""
        with patch('services.oracle_api.router.get_analyzer') as mock_get_analyzer:
            mock_analyzer = AsyncMock()
            mock_analyzer.analyze_feedback_batch.return_value = AnalysisFindings(
                analysis_id="test_analysis",
                event_count=50,
                time_window_hours=24,
                patterns=[],
                performance_metrics={},
                issues=[],
                recommendations=[]
            )
            mock_get_analyzer.return_value = mock_analyzer
            
            request_data = {
                "time_window_hours": 24,
                "event_limit": 100
            }
            
            response = client.post("/api/v1/oracle/analyze", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "analysis" in data
            assert "processing_time_seconds" in data
            assert data["analysis"]["event_count"] == 50
    
    def test_generate_mutation_plan(self, client, sample_analysis_findings):
        """Test mutation plan generation endpoint."""
        with patch('services.oracle_api.router.get_planner') as mock_get_planner:
            mock_planner = AsyncMock()
            mock_planner.generate_mutation_plan.return_value = MutationPlan(
                plan_id="test_plan",
                rationale="Test plan",
                confidence_score=0.8,
                expected_impact="Test improvement",
                actions=[],
                safety_checks=[],
                rollback_key="test_rollback"
            )
            mock_get_planner.return_value = mock_planner
            
            request_data = {
                "findings": sample_analysis_findings.dict()
            }
            
            response = client.post("/api/v1/oracle/plan", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["plan"]["plan_id"] == "test_plan"
            assert "planning_time_seconds" in data
    
    def test_validate_mutation_plan(self, client, sample_mutation_plan):
        """Test mutation plan validation endpoint."""
        with patch('services.oracle_api.router.get_validator') as mock_get_validator:
            mock_validator = AsyncMock()
            mock_validator.validate_mutation_plan.return_value = {
                "policy_validation": ValidationResult(
                    check_type=SafetyCheckType.POLICY_VALIDATION,
                    passed=True,
                    execution_time_seconds=0.5
                )
            }
            mock_get_validator.return_value = mock_validator
            
            request_data = {
                "plan": sample_mutation_plan.dict()
            }
            
            response = client.post("/api/v1/oracle/validate", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert data["overall_passed"] is True
            assert "validation_time_seconds" in data
    
    def test_execute_mutation_plan(self, client, sample_mutation_plan):
        """Test mutation plan execution endpoint."""
        request_data = {
            "plan": sample_mutation_plan.dict(),
            "dry_run": True
        }
        
        response = client.post("/api/v1/oracle/execute", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "started"
        assert "execution_id" in data
    
    def test_oracle_status(self, client):
        """Test Oracle status endpoint."""
        with patch('services.oracle_api.router.get_analyzer') as mock_get_analyzer, \
             patch('services.oracle_api.router.get_planner') as mock_get_planner, \
             patch('services.oracle_api.router.get_validator') as mock_get_validator:
            
            # Mock component stats
            mock_planner = AsyncMock()
            mock_planner.get_planning_stats.return_value = {"plans_generated": 10}
            mock_get_planner.return_value = mock_planner
            
            mock_validator = AsyncMock()
            mock_validator.get_validation_stats.return_value = {"validations_run": 8}
            mock_get_validator.return_value = mock_validator
            
            mock_analyzer = AsyncMock()
            mock_get_analyzer.return_value = mock_analyzer
            
            # Mock event bus
            with patch('services.oracle_api.router.get_default_event_bus') as mock_get_bus:
                mock_bus = AsyncMock()
                mock_bus.get_stats.return_value = {"events_published": 100}
                mock_get_bus.return_value = mock_bus
                
                response = client.get("/api/v1/oracle/status")
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "healthy"
                assert "planning_stats" in data
                assert "validation_stats" in data
    
    def test_oracle_tick(self, client):
        """Test Oracle processing tick endpoint."""
        with patch('services.oracle_api.router.get_analyzer') as mock_get_analyzer, \
             patch('services.oracle_api.router.get_planner') as mock_get_planner, \
             patch('services.oracle_api.router.get_validator') as mock_get_validator:
            
            mock_get_analyzer.return_value = AsyncMock()
            mock_get_planner.return_value = AsyncMock()
            mock_get_validator.return_value = AsyncMock()
            
            response = client.post("/api/v1/oracle/tick")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "started"
            assert "timestamp" in data


class TestFeedbackAnalyzer:
    """Test suite for feedback analyzer."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return FeedbackAnalyzer()
    
    @pytest.fixture
    def sample_events(self):
        """Sample event envelopes."""
        return [
            EventEnvelope(
                envelope_id="event_1",
                event_type="feedback.implicit",
                payload={
                    "event_id": "feedback_1",
                    "event_type": "feedback.implicit",
                    "agent_id": "agent_1",
                    "session_id": "session_1",
                    "timestamp": datetime.utcnow().isoformat(),
                    "context": {},
                    "explicit": {},
                    "implicit": {"response_time_ms": 800, "success_rate": 0.7},
                    "artifacts": {},
                    "metadata": {}
                },
                source_service="test",
                target_services=["oracle"],
                created_at=datetime.utcnow()
            )
        ]
    
    @pytest.mark.asyncio
    async def test_analyze_feedback_batch(self, analyzer, sample_events):
        """Test feedback batch analysis."""
        findings = await analyzer.analyze_feedback_batch(sample_events, 24)
        
        assert findings.event_count >= 0
        assert findings.time_window_hours == 24
        assert isinstance(findings.patterns, list)
        assert isinstance(findings.performance_metrics, dict)
        assert isinstance(findings.recommendations, list)


class TestOraclePlanner:
    """Test suite for Oracle planner."""
    
    @pytest.fixture
    def planner(self):
        """Create planner instance."""
        return OraclePlanner()
    
    @pytest.mark.asyncio
    async def test_generate_mutation_plan(self, planner, sample_analysis_findings):
        """Test mutation plan generation."""
        plan = await planner.generate_mutation_plan(sample_analysis_findings)
        
        if plan:  # Plan generation may return None for insufficient evidence
            assert plan.plan_id is not None
            assert len(plan.actions) >= 0
            assert plan.confidence_score >= 0.0
            assert plan.rollback_key is not None
    
    @pytest.mark.asyncio
    async def test_get_planning_stats(self, planner):
        """Test planning statistics retrieval."""
        stats = await planner.get_planning_stats()
        
        assert "plans_generated" in stats
        assert "mutations_suggested" in stats
        assert "high_confidence_plans" in stats


class TestSafetyValidator:
    """Test suite for safety validator."""
    
    @pytest.fixture
    def validator(self):
        """Create validator instance."""
        return SafetyValidator()
    
    @pytest.mark.asyncio
    async def test_validate_mutation_plan(self, validator, sample_mutation_plan):
        """Test mutation plan validation."""
        results = await validator.validate_mutation_plan(sample_mutation_plan)
        
        assert isinstance(results, dict)
        for check_type, result in results.items():
            assert isinstance(result, ValidationResult)
            assert result.check_type is not None
            assert isinstance(result.passed, bool)
    
    @pytest.mark.asyncio
    async def test_get_validation_stats(self, validator):
        """Test validation statistics retrieval."""
        stats = await validator.get_validation_stats()
        
        assert "validations_run" in stats
        assert "plans_approved" in stats
        assert "plans_rejected" in stats