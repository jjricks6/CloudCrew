"""Tests for src/tools/kb_search.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestKnowledgeBaseSearch:
    """Verify KB search tool behavior."""

    def test_returns_not_configured_when_no_kb_id(self) -> None:
        from src.tools.kb_search import knowledge_base_search

        mock_context = MagicMock()
        mock_context.invocation_state = {}

        result = knowledge_base_search(
            query="test query",
            tool_context=mock_context,
        )
        assert "not configured" in result.lower()

    def test_returns_not_configured_when_kb_id_empty(self) -> None:
        from src.tools.kb_search import knowledge_base_search

        mock_context = MagicMock()
        mock_context.invocation_state = {"knowledge_base_id": ""}

        result = knowledge_base_search(
            query="test query",
            tool_context=mock_context,
        )
        assert "not configured" in result.lower()

    @patch("src.tools.kb_search.boto3")
    def test_search_returns_formatted_results(self, mock_boto3: MagicMock) -> None:
        from src.tools.kb_search import knowledge_base_search

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.retrieve.return_value = {
            "retrievalResults": [
                {
                    "content": {"text": "Test content here"},
                    "location": {
                        "s3Location": {"uri": "s3://bucket/docs/test.md"},
                    },
                    "score": 0.95,
                },
            ],
        }

        mock_context = MagicMock()
        mock_context.invocation_state = {"knowledge_base_id": "kb-12345"}

        result = knowledge_base_search(
            query="test query",
            tool_context=mock_context,
        )
        assert "Test content here" in result
        assert "s3://bucket/docs/test.md" in result
        assert "0.95" in result

    @patch("src.tools.kb_search.boto3")
    def test_search_no_results(self, mock_boto3: MagicMock) -> None:
        from src.tools.kb_search import knowledge_base_search

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.retrieve.return_value = {"retrievalResults": []}

        mock_context = MagicMock()
        mock_context.invocation_state = {"knowledge_base_id": "kb-12345"}

        result = knowledge_base_search(
            query="obscure query",
            tool_context=mock_context,
        )
        assert "No results found" in result

    @patch("src.tools.kb_search.boto3")
    def test_search_handles_exception(self, mock_boto3: MagicMock) -> None:
        from src.tools.kb_search import knowledge_base_search

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.retrieve.side_effect = RuntimeError("API error")

        mock_context = MagicMock()
        mock_context.invocation_state = {"knowledge_base_id": "kb-12345"}

        result = knowledge_base_search(
            query="test query",
            tool_context=mock_context,
        )
        assert "failed" in result.lower()


@pytest.mark.unit
class TestExtractSource:
    """Verify source extraction from KB result locations."""

    def test_extract_s3_uri(self) -> None:
        from src.tools.kb_search import _extract_source

        location = {"s3Location": {"uri": "s3://bucket/path/file.md"}}
        assert _extract_source(location) == "s3://bucket/path/file.md"

    def test_extract_unknown_when_no_s3(self) -> None:
        from src.tools.kb_search import _extract_source

        assert _extract_source({}) == "unknown"
        assert _extract_source({"s3Location": {}}) == "unknown"
