"""Tests for src/tools/sow_generator.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestGenerateSOW:
    """Verify generate_sow tool."""

    @patch("src.tools.sow_generator.boto3")
    def test_generates_sow_successfully(self, mock_boto3: MagicMock) -> None:
        from src.tools.sow_generator import generate_sow

        # Mock the Bedrock response
        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client

        mock_response = {
            "output": {
                "message": {
                    "content": [
                        {"text": "# Statement of Work: Test Project\n\n## Executive Summary\nThis is a test SOW."}
                    ]
                }
            }
        }
        mock_client.converse.return_value = mock_response

        # Mock tool_context
        mock_context = MagicMock()

        result = generate_sow(
            customer_requirements="Build a web app",
            project_name="Test Project",
            tool_context=mock_context,
        )

        assert "Statement of Work" in result
        assert "Executive Summary" in result
        mock_client.converse.assert_called_once()

    def test_returns_error_on_empty_requirements(self) -> None:
        from src.tools.sow_generator import generate_sow

        mock_context = MagicMock()
        result = generate_sow(
            customer_requirements="",
            project_name="Test",
            tool_context=mock_context,
        )

        assert "Error" in result
        assert "Empty customer requirements" in result

    def test_returns_error_on_empty_project_name(self) -> None:
        from src.tools.sow_generator import generate_sow

        mock_context = MagicMock()
        result = generate_sow(
            customer_requirements="Build a web app",
            project_name="",
            tool_context=mock_context,
        )

        assert "Error" in result
        assert "Empty project name" in result

    @patch("src.tools.sow_generator.boto3")
    def test_returns_error_on_empty_response(self, mock_boto3: MagicMock) -> None:
        from src.tools.sow_generator import generate_sow

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_response = {"output": {"message": {"content": []}}}
        mock_client.converse.return_value = mock_response

        mock_context = MagicMock()
        result = generate_sow(
            customer_requirements="Build a web app",
            project_name="Test",
            tool_context=mock_context,
        )

        assert "Error" in result
        assert "No text" in result

    @patch("src.tools.sow_generator.boto3")
    def test_handles_bedrock_exception(self, mock_boto3: MagicMock) -> None:
        from src.tools.sow_generator import generate_sow

        mock_client = MagicMock()
        mock_boto3.client.return_value = mock_client
        mock_client.converse.side_effect = Exception("Bedrock error")

        mock_context = MagicMock()
        result = generate_sow(
            customer_requirements="Build a web app",
            project_name="Test",
            tool_context=mock_context,
        )

        assert "Error generating SOW" in result
