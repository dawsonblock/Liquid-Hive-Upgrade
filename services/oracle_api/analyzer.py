"""Feedback analysis engine for pattern detection and insights."""

import statistics
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import structlog

from services.shared.schemas import (
    FeedbackEvent, EventType, AnalysisFindings, 
    SystemHealthMetric, EventEnvelope
)

logger = structlog.get_logger(__name__)


class PatternDetector:
    """Detects patterns and anomalies in feedback data."""
    
    @staticmethod
    def detect_performance_degradation(events: List[FeedbackEvent]) -> List[Dict[str, Any]]:
        """Detect performance degradation patterns.
        
        Args:
            events: List of feedback events to analyze
            
        Returns:
            List of detected degradation patterns
        """
        patterns = []
        
        # Group events by agent and time windows
        agent_metrics = defaultdict(list)
        
        for event in events:
            if event.implicit.get("response_time_ms"):
                agent_metrics[event.agent_id].append({
                    "timestamp": event.timestamp,
                    "response_time": event.implicit["response_time_ms"],
                    "success_rate": event.implicit.get("success_rate", 1.0)
                })
        
        # Analyze each agent for degradation
        for agent_id, metrics in agent_metrics.items():
            if len(metrics) < 5:  # Need minimum data points
                continue
            
            # Sort by timestamp
            metrics.sort(key=lambda x: x["timestamp"])
            
            # Split into recent and baseline periods
            split_point = len(metrics) // 2
            baseline_metrics = metrics[:split_point]
            recent_metrics = metrics[split_point:]
            
            # Calculate averages
            baseline_response_time = statistics.mean(m["response_time"] for m in baseline_metrics)
            recent_response_time = statistics.mean(m["response_time"] for m in recent_metrics)
            
            baseline_success_rate = statistics.mean(m["success_rate"] for m in baseline_metrics)
            recent_success_rate = statistics.mean(m["success_rate"] for m in recent_metrics)
            
            # Check for significant degradation
            response_time_increase = (recent_response_time - baseline_response_time) / baseline_response_time
            success_rate_decrease = (baseline_success_rate - recent_success_rate) / baseline_success_rate
            
            if response_time_increase > 0.2 or success_rate_decrease > 0.1:  # 20% slower or 10% less successful
                patterns.append({
                    "type": "performance_degradation",
                    "agent_id": agent_id,
                    "severity": "high" if response_time_increase > 0.5 or success_rate_decrease > 0.2 else "medium",
                    "metrics": {
                        "response_time_increase_percent": response_time_increase * 100,
                        "success_rate_decrease_percent": success_rate_decrease * 100,
                        "baseline_response_time_ms": baseline_response_time,
                        "recent_response_time_ms": recent_response_time,
                        "baseline_success_rate": baseline_success_rate,
                        "recent_success_rate": recent_success_rate
                    },
                    "sample_size": len(metrics),
                    "confidence": min(len(metrics) / 20, 1.0)  # Higher confidence with more data
                })
        
        return patterns
    
    @staticmethod
    def detect_user_dissatisfaction(events: List[FeedbackEvent]) -> List[Dict[str, Any]]:
        """Detect user dissatisfaction patterns from explicit feedback.
        
        Args:
            events: List of feedback events to analyze
            
        Returns:
            List of detected dissatisfaction patterns
        """
        patterns = []
        
        # Group explicit feedback by agent
        agent_ratings = defaultdict(list)
        agent_complaints = defaultdict(list)
        
        for event in events:
            if event.event_type == EventType.FEEDBACK_EXPLICIT:
                # Collect ratings
                if "rating" in event.explicit:
                    try:
                        rating = float(event.explicit["rating"])
                        agent_ratings[event.agent_id].append({
                            "rating": rating,
                            "timestamp": event.timestamp,
                            "context": event.context
                        })
                    except (ValueError, TypeError):
                        pass
                
                # Collect complaints or corrections
                if "complaint" in event.explicit or "correction" in event.explicit:
                    agent_complaints[event.agent_id].append({
                        "feedback": event.explicit,
                        "timestamp": event.timestamp,
                        "context": event.context
                    })
        
        # Analyze ratings for each agent
        for agent_id, ratings in agent_ratings.items():
            if len(ratings) < 3:  # Need minimum feedback
                continue
            
            rating_values = [r["rating"] for r in ratings]
            avg_rating = statistics.mean(rating_values)
            recent_ratings = rating_values[-5:]  # Last 5 ratings
            recent_avg = statistics.mean(recent_ratings)
            
            # Check for low ratings or declining trend
            if avg_rating < 3.0 or (len(recent_ratings) >= 3 and recent_avg < avg_rating - 0.5):
                patterns.append({
                    "type": "user_dissatisfaction",
                    "agent_id": agent_id,
                    "severity": "high" if avg_rating < 2.0 else "medium",
                    "metrics": {
                        "average_rating": avg_rating,
                        "recent_average_rating": recent_avg,
                        "rating_trend": recent_avg - avg_rating,
                        "total_ratings": len(ratings),
                        "low_ratings_count": sum(1 for r in rating_values if r <= 2.0)
                    },
                    "sample_size": len(ratings),
                    "confidence": min(len(ratings) / 10, 1.0)
                })
        
        # Analyze complaints
        for agent_id, complaints in agent_complaints.items():
            if len(complaints) >= 3:  # Multiple complaints
                patterns.append({
                    "type": "user_complaints",
                    "agent_id": agent_id,
                    "severity": "high" if len(complaints) >= 5 else "medium",
                    "metrics": {
                        "complaint_count": len(complaints),
                        "complaint_rate": len(complaints) / max(len(agent_ratings.get(agent_id, [1])), 1)
                    },
                    "sample_complaints": [c["feedback"] for c in complaints[:3]],
                    "confidence": min(len(complaints) / 5, 1.0)
                })
        
        return patterns
    
    @staticmethod
    def detect_usage_patterns(events: List[FeedbackEvent]) -> List[Dict[str, Any]]:
        """Detect interesting usage patterns and trends.
        
        Args:
            events: List of feedback events to analyze
            
        Returns:
            List of detected usage patterns
        """
        patterns = []
        
        # Analyze temporal patterns
        hourly_usage = defaultdict(int)
        agent_usage = defaultdict(int)
        session_lengths = defaultdict(list)
        
        for event in events:
            # Hour-of-day usage
            hour = event.timestamp.hour
            hourly_usage[hour] += 1
            
            # Agent popularity
            agent_usage[event.agent_id] += 1
            
            # Session analysis (simplified - would need more sophisticated tracking)
            if "session_duration_minutes" in event.implicit:
                session_lengths[event.agent_id].append(event.implicit["session_duration_minutes"])
        
        # Find peak usage hours
        if hourly_usage:
            peak_hour = max(hourly_usage.items(), key=lambda x: x[1])
            avg_usage = statistics.mean(hourly_usage.values())
            
            if peak_hour[1] > avg_usage * 2:  # Peak is 2x average
                patterns.append({
                    "type": "peak_usage_hour",
                    "peak_hour": peak_hour[0],
                    "peak_count": peak_hour[1],
                    "average_hourly_count": avg_usage,
                    "peak_multiplier": peak_hour[1] / avg_usage,
                    "confidence": 0.8
                })
        
        # Find most/least popular agents
        if agent_usage:
            total_usage = sum(agent_usage.values())
            most_popular = max(agent_usage.items(), key=lambda x: x[1])
            least_popular = min(agent_usage.items(), key=lambda x: x[1])
            
            if most_popular[1] > total_usage * 0.4:  # One agent gets >40% of usage
                patterns.append({
                    "type": "agent_dominance",
                    "dominant_agent": most_popular[0],
                    "usage_percentage": (most_popular[1] / total_usage) * 100,
                    "usage_count": most_popular[1],
                    "confidence": 0.9
                })
            
            if least_popular[1] < total_usage * 0.05:  # Agent gets <5% of usage
                patterns.append({
                    "type": "underutilized_agent",
                    "agent_id": least_popular[0],
                    "usage_percentage": (least_popular[1] / total_usage) * 100,
                    "usage_count": least_popular[1],
                    "confidence": 0.7
                })
        
        return patterns


class FeedbackAnalyzer:
    """Main feedback analysis engine that coordinates pattern detection and insights."""
    
    def __init__(self):
        """Initialize the feedback analyzer."""
        self.pattern_detector = PatternDetector()
        logger.info("FeedbackAnalyzer initialized")
    
    async def analyze_feedback_batch(
        self, 
        events: List[EventEnvelope],
        time_window_hours: int = 24
    ) -> AnalysisFindings:
        """Analyze a batch of feedback events for patterns and insights.
        
        Args:
            events: List of event envelopes containing feedback data
            time_window_hours: Time window for analysis
            
        Returns:
            AnalysisFindings with detected patterns and recommendations
        """
        try:
            # Convert envelopes to feedback events
            feedback_events = []
            for envelope in events:
                try:
                    # Extract FeedbackEvent from payload
                    if envelope.event_type.startswith("feedback.") or envelope.event_type == "system.metric":
                        event_data = envelope.payload
                        feedback_event = FeedbackEvent(**event_data)
                        feedback_events.append(feedback_event)
                except Exception as e:
                    logger.warning("Failed to parse event", envelope_id=envelope.envelope_id, error=str(e))
                    continue
            
            if not feedback_events:
                return AnalysisFindings(
                    analysis_id=f"analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    event_count=0,
                    time_window_hours=time_window_hours,
                    patterns=[],
                    performance_metrics={},
                    issues=[],
                    recommendations=[]
                )
            
            logger.info(
                "Starting feedback analysis",
                event_count=len(feedback_events),
                time_window_hours=time_window_hours
            )
            
            # Detect various patterns
            all_patterns = []
            
            # Performance degradation patterns
            perf_patterns = self.pattern_detector.detect_performance_degradation(feedback_events)
            all_patterns.extend(perf_patterns)
            
            # User dissatisfaction patterns  
            satisfaction_patterns = self.pattern_detector.detect_user_dissatisfaction(feedback_events)
            all_patterns.extend(satisfaction_patterns)
            
            # Usage patterns
            usage_patterns = self.pattern_detector.detect_usage_patterns(feedback_events)
            all_patterns.extend(usage_patterns)
            
            # Calculate performance metrics
            performance_metrics = self._calculate_performance_metrics(feedback_events)
            
            # Identify issues from patterns
            issues = self._identify_issues(all_patterns)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(all_patterns, performance_metrics)
            
            # Calculate confidence intervals (simplified)
            confidence_intervals = self._calculate_confidence_intervals(feedback_events)
            
            findings = AnalysisFindings(
                analysis_id=f"analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                analyzed_at=datetime.utcnow(),
                event_count=len(feedback_events),
                time_window_hours=time_window_hours,
                patterns=all_patterns,
                performance_metrics=performance_metrics,
                issues=issues,
                recommendations=recommendations,
                confidence_intervals=confidence_intervals
            )
            
            logger.info(
                "Feedback analysis completed",
                analysis_id=findings.analysis_id,
                patterns_found=len(all_patterns),
                issues_identified=len(issues),
                recommendations_generated=len(recommendations)
            )
            
            return findings
            
        except Exception as e:
            logger.error("Error in feedback analysis", error=str(e))
            # Return minimal findings with error
            return AnalysisFindings(
                analysis_id=f"error_analysis_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                event_count=len(events),
                time_window_hours=time_window_hours,
                patterns=[],
                performance_metrics={},
                issues=[{"type": "analysis_error", "description": str(e)}],
                recommendations=["Fix analysis pipeline error"]
            )
    
    def _calculate_performance_metrics(self, events: List[FeedbackEvent]) -> Dict[str, float]:
        """Calculate overall performance metrics from events.
        
        Args:
            events: List of feedback events
            
        Returns:
            Dictionary of performance metrics
        """
        metrics = {}
        
        try:
            # Response times
            response_times = [
                event.implicit["response_time_ms"] 
                for event in events 
                if "response_time_ms" in event.implicit
            ]
            
            if response_times:
                metrics["avg_response_time_ms"] = statistics.mean(response_times)
                metrics["median_response_time_ms"] = statistics.median(response_times)
                metrics["p95_response_time_ms"] = sorted(response_times)[int(len(response_times) * 0.95)]
            
            # Success rates
            success_rates = [
                event.implicit["success_rate"] 
                for event in events 
                if "success_rate" in event.implicit
            ]
            
            if success_rates:
                metrics["avg_success_rate"] = statistics.mean(success_rates)
                metrics["min_success_rate"] = min(success_rates)
                
            # User ratings
            ratings = [
                float(event.explicit["rating"]) 
                for event in events 
                if event.explicit.get("rating")
            ]
            
            if ratings:
                metrics["avg_user_rating"] = statistics.mean(ratings)
                metrics["user_satisfaction_rate"] = sum(1 for r in ratings if r >= 4) / len(ratings)
            
            # Event distribution
            metrics["total_events"] = len(events)
            metrics["explicit_feedback_ratio"] = sum(
                1 for event in events if event.event_type == EventType.FEEDBACK_EXPLICIT
            ) / len(events) if events else 0
            
        except Exception as e:
            logger.error("Error calculating performance metrics", error=str(e))
        
        return metrics
    
    def _identify_issues(self, patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify issues from detected patterns.
        
        Args:
            patterns: List of detected patterns
            
        Returns:
            List of identified issues
        """
        issues = []
        
        for pattern in patterns:
            if pattern["type"] == "performance_degradation" and pattern["severity"] == "high":
                issues.append({
                    "type": "critical_performance_issue",
                    "description": f"Agent {pattern['agent_id']} showing significant performance degradation",
                    "agent_id": pattern["agent_id"],
                    "severity": "critical",
                    "metrics": pattern["metrics"]
                })
            
            elif pattern["type"] == "user_dissatisfaction" and pattern["severity"] == "high":
                issues.append({
                    "type": "user_satisfaction_issue",
                    "description": f"Agent {pattern['agent_id']} receiving consistently low user ratings",
                    "agent_id": pattern["agent_id"],
                    "severity": "high",
                    "metrics": pattern["metrics"]
                })
            
            elif pattern["type"] == "user_complaints":
                issues.append({
                    "type": "user_complaint_issue", 
                    "description": f"Multiple user complaints received for agent {pattern['agent_id']}",
                    "agent_id": pattern["agent_id"],
                    "severity": pattern["severity"],
                    "complaint_count": pattern["metrics"]["complaint_count"]
                })
        
        return issues
    
    def _generate_recommendations(
        self, 
        patterns: List[Dict[str, Any]], 
        performance_metrics: Dict[str, float]
    ) -> List[str]:
        """Generate recommendations based on analysis results.
        
        Args:
            patterns: Detected patterns
            performance_metrics: Calculated performance metrics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Performance-based recommendations
        if performance_metrics.get("avg_response_time_ms", 0) > 2000:
            recommendations.append(
                "Consider optimizing agent response times - average exceeds 2 seconds"
            )
        
        if performance_metrics.get("avg_success_rate", 1.0) < 0.8:
            recommendations.append(
                "Success rate below 80% - investigate and improve error handling"
            )
        
        if performance_metrics.get("avg_user_rating", 5.0) < 3.5:
            recommendations.append(
                "User satisfaction is low - consider prompt improvements or additional training"
            )
        
        # Pattern-based recommendations
        for pattern in patterns:
            if pattern["type"] == "performance_degradation":
                recommendations.append(
                    f"Apply performance optimization to agent {pattern['agent_id']} "
                    f"- {pattern['metrics']['response_time_increase_percent']:.1f}% slower"
                )
            
            elif pattern["type"] == "user_dissatisfaction":
                recommendations.append(
                    f"Review and improve prompts for agent {pattern['agent_id']} "
                    f"- average rating: {pattern['metrics']['average_rating']:.1f}"
                )
            
            elif pattern["type"] == "underutilized_agent":
                recommendations.append(
                    f"Consider promoting or improving agent {pattern['agent_id']} "
                    f"- only {pattern['usage_percentage']:.1f}% of usage"
                )
            
            elif pattern["type"] == "agent_dominance":
                recommendations.append(
                    f"Consider load balancing - agent {pattern['dominant_agent']} "
                    f"handles {pattern['usage_percentage']:.1f}% of requests"
                )
        
        # Remove duplicates and limit
        recommendations = list(dict.fromkeys(recommendations))
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _calculate_confidence_intervals(
        self, 
        events: List[FeedbackEvent]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate statistical confidence intervals for key metrics.
        
        Args:
            events: List of feedback events
            
        Returns:
            Dictionary of confidence intervals
        """
        confidence_intervals = {}
        
        try:
            # Response time confidence interval
            response_times = [
                event.implicit["response_time_ms"] 
                for event in events 
                if "response_time_ms" in event.implicit
            ]
            
            if len(response_times) > 3:
                mean_rt = statistics.mean(response_times)
                stdev_rt = statistics.stdev(response_times)
                margin = 1.96 * stdev_rt / (len(response_times) ** 0.5)  # 95% CI
                
                confidence_intervals["response_time_ms"] = {
                    "mean": mean_rt,
                    "lower_bound": mean_rt - margin,
                    "upper_bound": mean_rt + margin,
                    "confidence_level": 0.95
                }
            
            # Success rate confidence interval
            success_rates = [
                event.implicit["success_rate"] 
                for event in events 
                if "success_rate" in event.implicit
            ]
            
            if len(success_rates) > 3:
                mean_sr = statistics.mean(success_rates)
                stdev_sr = statistics.stdev(success_rates)
                margin = 1.96 * stdev_sr / (len(success_rates) ** 0.5)  # 95% CI
                
                confidence_intervals["success_rate"] = {
                    "mean": mean_sr,
                    "lower_bound": max(0, mean_sr - margin),
                    "upper_bound": min(1, mean_sr + margin),
                    "confidence_level": 0.95
                }
                
        except Exception as e:
            logger.error("Error calculating confidence intervals", error=str(e))
        
        return confidence_intervals