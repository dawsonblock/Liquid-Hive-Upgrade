"""Tests for the feedback collection API."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import AsyncMock, patch

from services.feedback_api.main import app
from services.feedback_api.collector import FeedbackCollector
from services.shared.schemas import FeedbackEvent, EventType


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_feedback_request():
    """Sample feedback request data."""
    return {
        "agent_id": "test_agent_1",
        "session_id": "test_session_123",
        "context": {"query": "What is the weather like?"},
        "explicit": {"rating": 4.5, "helpful": True},
        "implicit": {"response_time_ms": 250.0, "success_rate": 0.95},
        "artifacts": {"log_path": "/logs/test.log"},
        "metadata": {"source": "test_suite"}
    }


class TestFeedbackAPI:
    """Test suite for feedback collection API."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "Liquid Hive Feedback API"
        assert "version" in data
        assert "endpoints" in data
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        with patch.object(app.state, 'event_bus', AsyncMock()) as mock_bus:
            mock_bus.get_stats.return_value = {"events_published": 42}
            
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] == "healthy"
            assert data["service"] == "feedback_api"
    
    def test_collect_feedback_success(self, client, sample_feedback_request):
        """Test successful feedback collection."""
        with patch('services.feedback_api.collector.get_feedback_collector') as mock_get_collector:
            mock_collector = AsyncMock()
            mock_collector.collect_feedback.return_value = True
            mock_get_collector.return_value = mock_collector
            
            response = client.post("/api/v1/feedback/collect", json=sample_feedback_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "collected"
            assert "event_id" in data
            assert data["event_id"].startswith("feedback_")
            assert "timestamp" in data
    
    def test_collect_feedback_failure(self, client, sample_feedback_request):
        """Test feedback collection failure."""
        with patch('services.feedback_api.collector.get_feedback_collector') as mock_get_collector:
            mock_collector = AsyncMock()
            mock_collector.collect_feedback.return_value = False
            mock_get_collector.return_value = mock_collector
            
            response = client.post("/api/v1/feedback/collect", json=sample_feedback_request)
            assert response.status_code == 500
    
    def test_collect_bulk_feedback(self, client, sample_feedback_request):
        """Test bulk feedback collection."""
        bulk_request = {
            "events": [sample_feedback_request, sample_feedback_request]
        }
        
        with patch('services.feedback_api.collector.get_feedback_collector') as mock_get_collector:
            mock_collector = AsyncMock()
            mock_collector.collect_feedback.return_value = True
            mock_get_collector.return_value = mock_collector
            
            response = client.post("/api/v1/feedback/collect/bulk", json=bulk_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data["collected_count"] == 2
            assert data["failed_count"] == 0
            assert len(data["event_ids"]) == 2
    
    def test_get_metrics(self, client):
        """Test feedback metrics endpoint."""
        with patch('services.feedback_api.collector.get_feedback_collector') as mock_get_collector:
            mock_collector = AsyncMock()
            mock_collector.get_metrics.return_value = {
                "total_events": 100,
                "events_by_type": {"feedback.explicit": 40, "feedback.implicit": 60},
                "events_by_agent": {"agent_1": 50, "agent_2": 50},
                "avg_rating": 4.2,
                "success_rate": 0.92
            }
            mock_get_collector.return_value = mock_collector
            
            response = client.get("/api/v1/feedback/metrics?hours=24")
            assert response.status_code == 200
            
            data = response.json()
            assert data["total_events"] == 100
            assert data["avg_rating"] == 4.2
            assert data["time_window_hours"] == 24
    
    def test_collect_system_metric(self, client):
        """Test system metric collection."""
        with patch('services.feedback_api.collector.get_feedback_collector') as mock_get_collector:
            mock_collector = AsyncMock()
            mock_collector.collect_feedback.return_value = True
            mock_get_collector.return_value = mock_collector
            
            response = client.post(
                "/api/v1/feedback/system/metric",
                params={
                    "metric_name": "response_time",
                    "metric_value": 250.5,
                    "component": "api_gateway",
                    "unit": "milliseconds"
                },
                json={"environment": "test"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "collected"
            assert "event_id" in data


class TestFeedbackCollector:
    """Test suite for feedback collector."""
    
    @pytest.fixture
    def collector(self):
        """Create feedback collector instance."""
        return FeedbackCollector()
    
    @pytest.fixture
    def sample_feedback_event(self):
        """Sample feedback event."""
        return FeedbackEvent(
            event_id="test_event_123",
            event_type=EventType.FEEDBACK_EXPLICIT,
            agent_id="test_agent",
            session_id="test_session",
            timestamp=datetime.utcnow(),
            context={"query": "test query"},
            explicit={"rating": 4.0},
            implicit={"response_time_ms": 200.0}
        )
    
    @pytest.mark.asyncio
    async def test_collect_feedback_success(self, collector, sample_feedback_event):
        """Test successful feedback collection."""
        with patch('services.event_bus.bus.get_default_event_bus') as mock_get_bus:
            mock_bus = AsyncMock()
            mock_bus.publish.return_value = True
            mock_get_bus.return_value = mock_bus
            
            result = await collector.collect_feedback(sample_feedback_event)
            assert result is True
            assert collector.stats["total_collected"] == 1
            assert collector.stats["collected_by_type"][EventType.FEEDBACK_EXPLICIT.value] == 1
    
    @pytest.mark.asyncio
    async def test_collect_feedback_validation_failure(self, collector):
        """Test feedback collection with validation failure."""
        invalid_event = FeedbackEvent(
            event_id="",  # Invalid empty event_id
            event_type=EventType.FEEDBACK_EXPLICIT,
            agent_id="test_agent",
            session_id="test_session",
            explicit={},
            implicit={}  # No feedback data
        )
        
        result = await collector.collect_feedback(invalid_event)
        assert result is False
        assert collector.stats["validation_errors"] == 1
    
    @pytest.mark.asyncio
    async def test_get_metrics(self, collector, sample_feedback_event):
        """Test metrics calculation."""
        # Add some sample data to recent_events
        collector.recent_events.append({
            "event": sample_feedback_event,
            "collected_at": datetime.utcnow()
        })
        
        metrics = await collector.get_metrics(24)
        assert metrics["total_events"] == 1
        assert "events_by_type" in metrics
        assert "events_by_agent" in metrics
    
    @pytest.mark.asyncio
    async def test_get_status(self, collector):
        """Test collector status retrieval."""
        with patch('services.event_bus.bus.get_default_event_bus') as mock_get_bus:
            mock_bus = AsyncMock()
            mock_bus.get_stats.return_value = {"events_published": 10}
            mock_get_bus.return_value = mock_bus
            
            status = await collector.get_status()
            assert status["status"] == "healthy"
            assert "uptime_seconds" in status
            assert "collection_stats" in status