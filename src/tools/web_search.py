"""Web search tool for agents to research documentation, technologies, and solutions.

Uses the Tavily Search API for high-quality, AI-optimized search results.
Falls back gracefully when the API key is not configured.

This module imports from config — NEVER from agents/ or phases/.
"""

import logging
from typing import Any

import httpx
from strands import tool

from src.config import TAVILY_API_KEY

logger = logging.getLogger(__name__)

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_DEFAULT_MAX_RESULTS = 5
_REQUEST_TIMEOUT = 15.0


@tool
def web_search(query: str, max_results: int = _DEFAULT_MAX_RESULTS) -> str:
    """Search the web for information relevant to the current task.

    Use this tool to research AWS services, best practices, documentation,
    debugging solutions, library APIs, or any technical information needed
    to make informed decisions.

    Args:
        query: Natural language search query. Be specific for better results.
        max_results: Maximum number of results to return (1-10, default 5).

    Returns:
        Formatted search results with titles, URLs, and content snippets,
        or a message if search is unavailable.
    """
    if not TAVILY_API_KEY:
        return (
            "Web search is not configured (TAVILY_API_KEY not set). "
            "Use knowledge_base_search to search project artifacts, "
            "or proceed with your existing knowledge."
        )

    max_results = max(1, min(10, max_results))

    try:
        payload: dict[str, Any] = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_answer": True,
        }

        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            response = client.post(_TAVILY_SEARCH_URL, json=payload)
            response.raise_for_status()

        data = response.json()
        return _format_results(query, data)

    except httpx.TimeoutException:
        logger.warning("Web search timed out for query: %s", query[:80])
        return f"Web search timed out for query: {query}. Try a more specific query or proceed with existing knowledge."

    except Exception:
        logger.exception("Web search failed for query: %s", query[:80])
        return f"Web search failed for query: {query}. Proceed with existing knowledge."


def _format_results(query: str, data: dict[str, Any]) -> str:
    """Format Tavily API response into readable markdown.

    Args:
        query: The original search query.
        data: Raw JSON response from the Tavily API.

    Returns:
        Formatted markdown string with search results.
    """
    sections: list[str] = []

    # Include the AI-generated answer summary if available
    answer = data.get("answer")
    if answer:
        sections.append(f"**Summary:** {answer}")

    results = data.get("results", [])
    if not results:
        return f"No results found for: {query}"

    for i, result in enumerate(results, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        content = result.get("content", "")
        # Truncate long content to keep context window manageable
        if len(content) > 500:
            content = content[:497] + "..."
        sections.append(f"### {i}. {title}\n**URL:** {url}\n\n{content}")

    logger.info("Web search returned %d results for query: %s", len(results), query[:50])
    return "\n\n---\n\n".join(sections)
