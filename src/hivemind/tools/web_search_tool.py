"""
Web Search Tool for LIQUID-HIVE
==============================

A web search tool that can perform internet searches and return results.
This tool requires approval due to external network access.
"""

import asyncio
import json
from typing import Any, Dict, List

import aiohttp

from .base_tool import BaseTool, ToolParameter, ToolParameterType, ToolResult


class WebSearchTool(BaseTool):
    """Web search tool using DuckDuckGo API."""

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Search the web for information using DuckDuckGo search engine"

    @property
    def parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="Search query to execute",
                required=True,
            ),
            ToolParameter(
                name="max_results",
                type=ToolParameterType.INTEGER,
                description="Maximum number of search results to return",
                required=False,
                default=5,
                min_value=1,
                max_value=20,
            ),
            ToolParameter(
                name="region",
                type=ToolParameterType.STRING,
                description="Region for search (e.g., 'us-en', 'uk-en', 'de-de')",
                required=False,
                default="us-en",
            ),
            ToolParameter(
                name="safe_search",
                type=ToolParameterType.STRING,
                description="Safe search setting",
                required=False,
                default="moderate",
                choices=["strict", "moderate", "off"],
            ),
        ]

    @property
    def category(self) -> str:
        return "information"

    @property
    def requires_approval(self) -> bool:
        return True  # Web access requires approval

    @property
    def risk_level(self) -> str:
        return "medium"  # Network access has moderate risk

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        """Execute web search."""
        query = parameters["query"]
        max_results = parameters.get("max_results", 5)
        region = parameters.get("region", "us-en")
        safe_search = parameters.get("safe_search", "moderate")

        try:
            # Use DuckDuckGo Instant Answer API (no API key required)
            results = await self._duckduckgo_search(
                query, max_results, region, safe_search
            )

            if not results:
                return ToolResult(
                    success=True,
                    data=[],
                    metadata={
                        "query": query,
                        "message": "No results found",
                        "source": "duckduckgo",
                    },
                )

            return ToolResult(
                success=True,
                data=results,
                metadata={
                    "query": query,
                    "count": len(results),
                    "region": region,
                    "safe_search": safe_search,
                    "source": "duckduckgo",
                },
            )

        except aiohttp.ClientError as e:
            return ToolResult(
                success=False, error=f"Network error during search: {str(e)}"
            )
        except asyncio.TimeoutError:
            return ToolResult(success=False, error="Search request timed out")
        except Exception as e:
            return ToolResult(success=False, error=f"Search failed: {str(e)}")

    async def _duckduckgo_search(
        self, query: str, max_results: int, region: str, safe_search: str
    ) -> List[Dict[str, Any]]:
        """Perform DuckDuckGo search."""
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # DuckDuckGo Instant Answer API
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
                "skip_disambig": "1",
                "no_redirect": "1",
                "safe_search": safe_search,
            }

            url = "https://api.duckduckgo.com/"

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise aiohttp.ClientError(f"HTTP {response.status}")

                data = await response.json()
                results = []

                # Extract abstract if available
                if data.get("Abstract"):
                    results.append(
                        {
                            "title": data.get("Heading", "Abstract"),
                            "snippet": data.get("Abstract"),
                            "url": data.get("AbstractURL", ""),
                            "source": data.get("AbstractSource", "DuckDuckGo"),
                            "type": "abstract",
                        }
                    )

                # Extract related topics
                for topic in data.get("RelatedTopics", [])[
                    : max_results - len(results)
                ]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append(
                            {
                                "title": (
                                    topic.get("Text", "").split(" - ")[0]
                                    if " - " in topic.get("Text", "")
                                    else "Related Topic"
                                ),
                                "snippet": topic.get("Text", ""),
                                "url": topic.get("FirstURL", ""),
                                "source": "DuckDuckGo",
                                "type": "related_topic",
                            }
                        )

                # If we still don't have enough results, try the web results API
                if len(results) < max_results:
                    web_results = await self._duckduckgo_web_search(
                        session, query, max_results - len(results)
                    )
                    results.extend(web_results)

                return results[:max_results]

    async def _duckduckgo_web_search(
        self, session: aiohttp.ClientSession, query: str, max_results: int
    ) -> List[Dict[str, Any]]:
        """Attempt to get web search results (may not always work due to rate limiting)."""
        try:
            # This is a simplified approach - DuckDuckGo's web search API is more complex
            # In a production system, you might want to use a dedicated search API
            params = {
                "q": query,
                "format": "json",
                "no_html": "1",
            }

            # Note: This is a fallback and may not always return web results
            # Consider integrating with other search APIs if needed

            return []  # Placeholder - implement proper web search if needed

        except Exception:
            return []
