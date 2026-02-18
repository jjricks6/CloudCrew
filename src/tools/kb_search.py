"""Knowledge Base search tool for semantic search across project artifacts.

Wraps the Bedrock Agent Runtime retrieve API for searching project artifacts
indexed in a Bedrock Knowledge Base.

This module imports from config — NEVER from agents/ or phases/.
"""

import logging
from typing import Any

import boto3
from strands import tool
from strands.types.tools import ToolContext

from src.config import AWS_REGION

logger = logging.getLogger(__name__)


@tool(context=True)
def knowledge_base_search(query: str, tool_context: ToolContext) -> str:
    """Search the project Knowledge Base for relevant artifacts.

    Performs semantic search across all indexed project artifacts (architecture
    docs, ADRs, IaC, code, security reviews) using a Bedrock Knowledge Base.

    Args:
        query: Natural language search query describing what to find.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Formatted search results with source references, or an error message
        if the Knowledge Base is not configured.
    """
    kb_id = tool_context.invocation_state.get("knowledge_base_id", "")
    if not kb_id:
        return "Knowledge Base not configured. Use git_read and git_list to access project artifacts directly."

    try:
        client: Any = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)
        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={"text": query},
            retrievalConfiguration={
                "vectorSearchConfiguration": {
                    "numberOfResults": 5,
                },
            },
        )

        results = response.get("retrievalResults", [])
        if not results:
            return f"No results found for query: {query}"

        formatted: list[str] = []
        for i, result in enumerate(results, 1):
            content = result.get("content", {}).get("text", "")
            location = result.get("location", {})
            source = _extract_source(location)
            score = result.get("score", 0.0)
            formatted.append(f"### Result {i} (score: {score:.2f})\n**Source:** {source}\n\n{content}")

        logger.info("KB search returned %d results for query: %s", len(results), query[:50])
        return "\n\n---\n\n".join(formatted)

    except Exception:
        logger.exception("Knowledge Base search failed for query: %s", query[:50])
        return "Knowledge Base search failed. Use git_read and git_list to access project artifacts directly."


def _extract_source(location: dict[str, Any]) -> str:
    """Extract a human-readable source reference from a KB result location.

    Args:
        location: The location dict from a Bedrock KB retrieval result.

    Returns:
        A source string (S3 URI or "unknown").
    """
    s3_location = location.get("s3Location", {})
    uri: str = s3_location.get("uri", "")
    if uri:
        return uri
    return "unknown"
