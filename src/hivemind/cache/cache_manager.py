"""Cache Management for LIQUID-HIVE
===============================

Cache management utilities for monitoring, warming, and optimizing
the semantic cache system.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any

from .semantic_cache import CacheStrategy, SemanticCache

log = logging.getLogger(__name__)


class CacheManager:
    """Manager for semantic cache operations and optimization."""

    def __init__(self, cache: SemanticCache):
        self.cache = cache
        self.logger = logging.getLogger(__name__)

        # Warming configuration
        self.warming_queries = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "Explain neural networks",
            "What is deep learning?",
            "Python programming basics",
            "How to use APIs?",
            "Best practices for software development",
            "What is cloud computing?",
            "Database design principles",
            "How to optimize performance?",
        ]

    async def warm_cache(self, queries_and_responses: list[dict[str, Any]]) -> dict[str, Any]:
        """Warm the cache with common query-response pairs.

        Args:
            queries_and_responses: List of dicts with 'query' and 'response' keys

        Returns:
            Warming results and statistics
        """
        results = {
            "total_queries": len(queries_and_responses),
            "cached_successfully": 0,
            "cache_failures": 0,
            "warming_time": 0,
            "errors": [],
        }

        start_time = time.time()

        try:
            for item in queries_and_responses:
                query = item.get("query", "")
                response = item.get("response", {})

                if not query or not response:
                    results["cache_failures"] += 1
                    continue

                success = await self.cache.set(query, response)

                if success:
                    results["cached_successfully"] += 1
                else:
                    results["cache_failures"] += 1

            results["warming_time"] = time.time() - start_time

            self.logger.info(
                f"Cache warming completed: {results['cached_successfully']}/{results['total_queries']} cached in {results['warming_time']:.2f}s"
            )

        except Exception as e:
            error_msg = f"Cache warming failed: {e!s}"
            results["errors"].append(error_msg)
            self.logger.error(error_msg)

        return results

    async def analyze_cache_performance(self, hours: int = 24) -> dict[str, Any]:
        """Analyze cache performance over a time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            Performance analysis results
        """
        try:
            analytics = await self.cache.get_analytics()

            analysis = {
                "timeframe_hours": hours,
                "cache_effectiveness": {
                    "hit_rate": analytics.get("hit_rate", 0),
                    "total_queries": analytics.get("total_queries", 0),
                    "cache_hits": analytics.get("cache_hits", 0),
                    "cache_misses": analytics.get("cache_misses", 0),
                },
                "semantic_matching": {
                    "average_similarity": analytics.get("average_similarity", 0),
                    "similarity_threshold": analytics.get("similarity_threshold", 0),
                },
                "resource_usage": {
                    "current_cache_size": analytics.get("current_size", 0),
                    "max_cache_size": analytics.get("max_size", 0),
                    "memory_usage_mb": analytics.get("memory_usage_mb", 0),
                    "cache_utilization": analytics.get("current_size", 0)
                    / max(analytics.get("max_size", 1), 1),
                },
                "recommendations": [],
            }

            # Generate performance recommendations
            analysis["recommendations"] = self._generate_recommendations(analysis)

            return analysis

        except Exception as e:
            return {"error": f"Performance analysis failed: {e!s}"}

    def _generate_recommendations(self, analysis: dict[str, Any]) -> list[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        hit_rate = analysis["cache_effectiveness"]["hit_rate"]
        similarity = analysis["semantic_matching"]["average_similarity"]
        utilization = analysis["resource_usage"]["cache_utilization"]

        # Hit rate recommendations
        if hit_rate < 0.1:
            recommendations.append(
                "Very low cache hit rate - consider adjusting similarity threshold or caching strategy"
            )
        elif hit_rate < 0.3:
            recommendations.append(
                "Low cache hit rate - consider lowering similarity threshold or expanding cache warming"
            )
        elif hit_rate > 0.8:
            recommendations.append("Excellent cache hit rate - current configuration is optimal")

        # Similarity threshold recommendations
        if similarity > 0.98:
            recommendations.append(
                "Very high average similarity - consider slightly lowering threshold for better coverage"
            )
        elif similarity < 0.85:
            recommendations.append(
                "Low average similarity - consider raising threshold for better precision"
            )

        # Cache utilization recommendations
        if utilization > 0.9:
            recommendations.append(
                "Cache near capacity - consider increasing max cache size or reducing TTL"
            )
        elif utilization < 0.3:
            recommendations.append(
                "Low cache utilization - consider more aggressive caching strategy"
            )

        # Strategy recommendations
        if hit_rate < 0.2 and utilization < 0.5:
            recommendations.append("Consider switching to AGGRESSIVE caching strategy")
        elif hit_rate > 0.7 and utilization > 0.8:
            recommendations.append("Consider switching to SELECTIVE caching strategy")

        return recommendations

    async def optimize_cache_settings(self, target_hit_rate: float = 0.5) -> dict[str, Any]:
        """Automatically optimize cache settings based on performance.

        Args:
            target_hit_rate: Target cache hit rate to optimize for

        Returns:
            Optimization results
        """
        results = {
            "original_settings": {},
            "optimized_settings": {},
            "changes_made": [],
            "expected_improvement": 0,
        }

        try:
            # Get current performance
            analysis = await self.analyze_cache_performance()
            current_hit_rate = analysis["cache_effectiveness"]["hit_rate"]
            current_similarity = analysis["semantic_matching"]["average_similarity"]

            results["original_settings"] = {
                "similarity_threshold": self.cache.similarity_threshold,
                "strategy": self.cache.strategy.value,
                "ttl": self.cache.default_ttl,
            }

            # Optimize similarity threshold
            if current_hit_rate < target_hit_rate and current_similarity > 0.95:
                new_threshold = max(0.85, self.cache.similarity_threshold - 0.05)
                self.cache.similarity_threshold = new_threshold
                results["changes_made"].append(f"Lowered similarity threshold to {new_threshold}")

            elif current_hit_rate > target_hit_rate * 1.2 and current_similarity < 0.9:
                new_threshold = min(0.98, self.cache.similarity_threshold + 0.02)
                self.cache.similarity_threshold = new_threshold
                results["changes_made"].append(f"Raised similarity threshold to {new_threshold}")

            # Optimize caching strategy
            if current_hit_rate < target_hit_rate * 0.5:
                if self.cache.strategy != CacheStrategy.AGGRESSIVE:
                    self.cache.strategy = CacheStrategy.AGGRESSIVE
                    results["changes_made"].append("Switched to AGGRESSIVE caching strategy")

            elif current_hit_rate > target_hit_rate * 1.5:
                if self.cache.strategy != CacheStrategy.SELECTIVE:
                    self.cache.strategy = CacheStrategy.SELECTIVE
                    results["changes_made"].append("Switched to SELECTIVE caching strategy")

            # Optimize TTL based on hit patterns
            utilization = analysis["resource_usage"]["cache_utilization"]
            if utilization > 0.9 and current_hit_rate > target_hit_rate:
                new_ttl = max(1800, self.cache.default_ttl - 600)  # Reduce TTL
                self.cache.default_ttl = new_ttl
                results["changes_made"].append(f"Reduced TTL to {new_ttl} seconds")

            results["optimized_settings"] = {
                "similarity_threshold": self.cache.similarity_threshold,
                "strategy": self.cache.strategy.value,
                "ttl": self.cache.default_ttl,
            }

            # Estimate expected improvement
            if results["changes_made"]:
                results["expected_improvement"] = min(
                    0.2, max(0.05, target_hit_rate - current_hit_rate)
                )

            self.logger.info(
                f"Cache optimization completed: {len(results['changes_made'])} changes made"
            )

        except Exception as e:
            results["error"] = f"Optimization failed: {e!s}"

        return results

    async def export_cache_data(self, format: str = "json") -> dict[str, Any]:
        """Export cache data for backup or analysis."""
        try:
            # Get all cache entries (be careful with large caches)
            pattern = f"{self.cache.metadata_key_prefix}:*"
            keys = await self.cache.redis_client.keys(pattern)

            entries = []
            for key in keys[:1000]:  # Limit to prevent memory issues
                try:
                    entry_data = await self.cache.redis_client.get(key)
                    if entry_data:
                        entry_dict = json.loads(entry_data)
                        entries.append(entry_dict)
                except Exception:
                    continue

            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "cache_size": len(entries),
                "cache_settings": {
                    "similarity_threshold": self.cache.similarity_threshold,
                    "strategy": self.cache.strategy.value,
                    "default_ttl": self.cache.default_ttl,
                },
                "analytics": await self.cache.get_analytics(),
                "entries": entries if format == "json" else len(entries),
            }

            return export_data

        except Exception as e:
            return {"error": f"Export failed: {e!s}"}

    async def import_cache_data(self, import_data: dict[str, Any]) -> dict[str, Any]:
        """Import cache data from backup."""
        results = {"imported_entries": 0, "failed_entries": 0, "errors": []}

        try:
            entries = import_data.get("entries", [])

            for entry_dict in entries:
                try:
                    # Recreate cache entry
                    query = entry_dict.get("query", "")
                    response = entry_dict.get("response", {})
                    ttl = entry_dict.get("ttl_seconds", self.cache.default_ttl)

                    if query and response:
                        success = await self.cache.set(query, response, ttl=ttl)
                        if success:
                            results["imported_entries"] += 1
                        else:
                            results["failed_entries"] += 1

                except Exception as e:
                    results["failed_entries"] += 1
                    results["errors"].append(str(e))
                    continue

            self.logger.info(
                f"Cache import completed: {results['imported_entries']} entries imported"
            )

        except Exception as e:
            results["errors"].append(f"Import failed: {e!s}")

        return results

    async def cache_statistics_report(self) -> str:
        """Generate a detailed cache statistics report."""
        try:
            analytics = await self.cache.get_analytics()
            analysis = await self.analyze_cache_performance()

            report = f"""
🧠 LIQUID-HIVE Semantic Cache Report
{"=" * 50}

📊 Cache Performance:
  • Hit Rate: {analytics["hit_rate"]:.1%} ({analytics["cache_hits"]}/{analytics["total_queries"]} queries)
  • Cache Size: {analytics["current_size"]}/{analytics["max_size"]} entries ({analytics["current_size"] / analytics["max_size"]:.1%} full)
  • Memory Usage: {analytics["memory_usage_mb"]:.1f} MB
  • Average Similarity: {analytics["average_similarity"]:.3f}

⚙️ Configuration:
  • Strategy: {analytics["strategy"].upper()}
  • Similarity Threshold: {analytics["similarity_threshold"]:.3f}
  • Default TTL: {analytics["ttl_seconds"]} seconds

🎯 Performance Analysis:
"""

            recommendations = analysis.get("recommendations", [])
            if recommendations:
                report += "  • Recommendations:\n"
                for rec in recommendations:
                    report += f"    - {rec}\n"
            else:
                report += "  • No specific recommendations - performance is good!\n"

            report += f"\n📅 Last Updated: {analytics.get('last_cleanup', 'Unknown')}\n"

            return report

        except Exception as e:
            return f"Failed to generate report: {e!s}"


async def create_cache_manager(redis_url: str = "redis://localhost:6379") -> CacheManager | None:
    """Create cache manager with semantic cache."""
    try:
        from .semantic_cache import get_semantic_cache

        cache = await get_semantic_cache(redis_url=redis_url)
        if cache and cache.is_ready:
            return CacheManager(cache)
        return None

    except Exception as e:
        log.error(f"Failed to create cache manager: {e}")
        return None
