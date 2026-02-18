"""Tests for src/state/memory.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestMemoryClient:
    """Verify MemoryClient operations."""

    @patch("src.state.memory.boto3")
    def test_save_events(self, mock_boto3: MagicMock) -> None:
        from src.state.memory import MemoryClient

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        client = MemoryClient(memory_id="mem-001")
        client.save_events(
            session_id="sess-001",
            events=[{"content": "Hello"}, {"content": "World"}],
        )

        mock_client.batch_create_memory_records.assert_called_once()
        call_kwargs = mock_client.batch_create_memory_records.call_args.kwargs
        assert call_kwargs["memoryId"] == "mem-001"
        assert len(call_kwargs["records"]) == 2

    @patch("src.state.memory.boto3")
    def test_save_events_skips_empty(self, mock_boto3: MagicMock) -> None:
        from src.state.memory import MemoryClient

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        client = MemoryClient(memory_id="mem-001")
        client.save_events(session_id="sess-001", events=[])

        mock_client.batch_create_memory_records.assert_not_called()

    @patch("src.state.memory.boto3")
    def test_save_events_filters_empty_content(self, mock_boto3: MagicMock) -> None:
        from src.state.memory import MemoryClient

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        client = MemoryClient(memory_id="mem-001")
        client.save_events(
            session_id="sess-001",
            events=[{"content": "Valid"}, {"content": ""}, {"other": "no content"}],
        )

        mock_client.batch_create_memory_records.assert_called_once()
        records = mock_client.batch_create_memory_records.call_args.kwargs["records"]
        assert len(records) == 1

    @patch("src.state.memory.boto3")
    def test_retrieve(self, mock_boto3: MagicMock) -> None:
        from src.state.memory import MemoryClient

        mock_client = MagicMock()
        mock_client.retrieve_memory_records.return_value = {
            "records": [{"content": {"text": "Decision: Use DynamoDB"}}],
        }
        mock_boto3.client.return_value = mock_client

        client = MemoryClient(memory_id="mem-001")
        records = client.retrieve(query="decisions", namespace="/decisions/")

        assert len(records) == 1
        mock_client.retrieve_memory_records.assert_called_once()
        call_kwargs = mock_client.retrieve_memory_records.call_args.kwargs
        assert call_kwargs["memoryId"] == "mem-001"
        assert call_kwargs["query"] == {"text": "decisions"}

    @patch("src.state.memory.boto3")
    def test_retrieve_empty(self, mock_boto3: MagicMock) -> None:
        from src.state.memory import MemoryClient

        mock_client = MagicMock()
        mock_client.retrieve_memory_records.return_value = {}
        mock_boto3.client.return_value = mock_client

        client = MemoryClient(memory_id="mem-001")
        records = client.retrieve(query="test")

        assert records == []

    @patch("src.state.memory.boto3")
    def test_start_extraction(self, mock_boto3: MagicMock) -> None:
        from src.state.memory import MemoryClient

        mock_client = MagicMock()
        mock_client.start_memory_extraction_job.return_value = {"jobId": "job-123"}
        mock_boto3.client.return_value = mock_client

        client = MemoryClient(memory_id="mem-001")
        job_id = client.start_extraction(session_id="sess-001")

        assert job_id == "job-123"
        mock_client.start_memory_extraction_job.assert_called_once()
