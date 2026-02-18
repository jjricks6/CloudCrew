"""AgentCore Memory client for STM and LTM operations.

Wraps the boto3 bedrock-agentcore client for memory read/write.
This module imports from config — NEVER from agents/ or tools/.
"""

import logging
from typing import Any

import boto3

from src.config import AWS_REGION

logger = logging.getLogger(__name__)


class MemoryClient:
    """Client for AgentCore Memory operations (STM and LTM).

    Provides methods to save conversation events, retrieve relevant
    memory records, and trigger LTM extraction from STM sessions.

    Args:
        memory_id: The AgentCore Memory resource ID.
    """

    def __init__(self, memory_id: str) -> None:
        self.memory_id = memory_id
        self._client: Any = boto3.client("bedrock-agentcore", region_name=AWS_REGION)

    def save_events(
        self,
        session_id: str,
        events: list[dict[str, str]],
        namespace: str = "/",
    ) -> None:
        """Save memory events (conversation messages) to memory.

        Args:
            session_id: The session identifier for grouping events.
            events: List of dicts with 'content' key containing text.
            namespace: Memory namespace for organizing records.
        """
        if not events:
            return

        records = [
            {
                "content": {"text": e["content"]},
                "namespace": namespace,
            }
            for e in events
            if e.get("content")
        ]

        if not records:
            return

        self._client.batch_create_memory_records(
            memoryId=self.memory_id,
            records=records,
        )
        logger.info(
            "Saved %d events to memory %s (session: %s)",
            len(records),
            self.memory_id,
            session_id,
        )

    def retrieve(
        self,
        query: str,
        namespace: str = "/",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant memory records.

        Args:
            query: Natural language query for semantic search.
            namespace: Memory namespace to search within.
            max_results: Maximum number of records to return.

        Returns:
            List of memory record dicts.
        """
        response = self._client.retrieve_memory_records(
            memoryId=self.memory_id,
            query={"text": query},
            namespace=namespace,
            maxResults=max_results,
        )
        records: list[dict[str, Any]] = response.get("records", [])
        logger.info(
            "Retrieved %d records from memory %s (query: %s)",
            len(records),
            self.memory_id,
            query[:50],
        )
        return records

    def start_extraction(self, session_id: str) -> str:
        """Start a memory extraction job (LTM learning from STM).

        Triggers the AgentCore Memory extraction pipeline that analyzes
        STM session data and extracts durable knowledge into LTM.

        Args:
            session_id: The STM session to extract from.

        Returns:
            The extraction job ID, or empty string on failure.
        """
        response = self._client.start_memory_extraction_job(
            memoryId=self.memory_id,
            sourceMemorySessionId=session_id,
        )
        job_id: str = response.get("jobId", "")
        logger.info(
            "Started extraction job %s for memory %s (session: %s)",
            job_id,
            self.memory_id,
            session_id,
        )
        return job_id
