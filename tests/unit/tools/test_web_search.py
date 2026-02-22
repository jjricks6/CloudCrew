"""Tests for src/tools/web_search.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestWebSearch:
    """Verify web search tool behavior."""

    @patch("src.tools.web_search.TAVILY_API_KEY", "")
    def test_returns_not_configured_when_no_api_key(self) -> None:
        from src.tools.web_search import web_search

        result = web_search(query="AWS Lambda best practices")
        assert "not configured" in result.lower()

    @patch("src.tools.web_search.TAVILY_API_KEY", "tvly-test-key")
    @patch("src.tools.web_search.httpx")
    def test_search_returns_formatted_results(self, mock_httpx: MagicMock) -> None:
        from src.tools.web_search import web_search

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "answer": "Lambda supports up to 15 minutes execution.",
            "results": [
                {
                    "title": "AWS Lambda Limits",
                    "url": "https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html",
                    "content": "The maximum execution time for a Lambda function is 900 seconds.",
                },
            ],
        }
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        result = web_search(query="AWS Lambda timeout limits")
        assert "Lambda Limits" in result
        assert "900 seconds" in result
        assert "docs.aws.amazon.com" in result
        assert "Lambda supports up to 15 minutes" in result

    @patch("src.tools.web_search.TAVILY_API_KEY", "tvly-test-key")
    @patch("src.tools.web_search.httpx")
    def test_search_no_results(self, mock_httpx: MagicMock) -> None:
        from src.tools.web_search import web_search

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        result = web_search(query="extremely obscure nonexistent thing")
        assert "No results found" in result

    @patch("src.tools.web_search.TAVILY_API_KEY", "tvly-test-key")
    @patch("src.tools.web_search.httpx")
    def test_search_handles_timeout(self, mock_httpx: MagicMock) -> None:
        import httpx as real_httpx
        from src.tools.web_search import web_search

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = real_httpx.TimeoutException("timeout")
        mock_httpx.Client.return_value = mock_client
        mock_httpx.TimeoutException = real_httpx.TimeoutException

        result = web_search(query="test query")
        assert "timed out" in result.lower()

    @patch("src.tools.web_search.TAVILY_API_KEY", "tvly-test-key")
    @patch("src.tools.web_search.httpx")
    def test_search_handles_exception(self, mock_httpx: MagicMock) -> None:
        from src.tools.web_search import web_search

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.side_effect = RuntimeError("Connection failed")
        mock_httpx.Client.return_value = mock_client
        mock_httpx.TimeoutException = type("TimeoutException", (Exception,), {})

        result = web_search(query="test query")
        assert "failed" in result.lower()

    @patch("src.tools.web_search.TAVILY_API_KEY", "tvly-test-key")
    @patch("src.tools.web_search.httpx")
    def test_max_results_clamped(self, mock_httpx: MagicMock) -> None:
        from src.tools.web_search import web_search

        mock_response = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        web_search(query="test", max_results=50)

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        assert payload["max_results"] == 10


@pytest.mark.unit
class TestFormatResults:
    """Verify result formatting."""

    def test_format_with_answer_and_results(self) -> None:
        from src.tools.web_search import _format_results

        data = {
            "answer": "DynamoDB is a NoSQL database.",
            "results": [
                {
                    "title": "DynamoDB Docs",
                    "url": "https://docs.aws.amazon.com/dynamodb",
                    "content": "Amazon DynamoDB is a fully managed NoSQL database service.",
                },
            ],
        }
        result = _format_results("DynamoDB", data)
        assert "DynamoDB is a NoSQL database" in result
        assert "DynamoDB Docs" in result
        assert "docs.aws.amazon.com" in result

    def test_format_truncates_long_content(self) -> None:
        from src.tools.web_search import _format_results

        data = {
            "results": [
                {
                    "title": "Long Result",
                    "url": "https://test.com",
                    "content": "x" * 600,
                },
            ],
        }
        result = _format_results("test", data)
        assert result.count("x") == 497
        assert "..." in result

    def test_format_empty_results(self) -> None:
        from src.tools.web_search import _format_results

        result = _format_results("test", {"results": []})
        assert "No results found" in result
