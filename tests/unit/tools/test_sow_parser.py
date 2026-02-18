"""Tests for src/tools/sow_parser.py."""

import json
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBuildExtractionPrompt:
    """Verify prompt construction."""

    def test_includes_document_content(self) -> None:
        from src.tools.sow_parser import _build_extraction_prompt

        prompt = _build_extraction_prompt("Build a website")
        assert "Build a website" in prompt
        assert "objectives" in prompt


@pytest.mark.unit
class TestExtractJsonFromResponse:
    """Verify JSON extraction from model responses."""

    def test_plain_json(self) -> None:
        from src.tools.sow_parser import _extract_json_from_response

        result = _extract_json_from_response('{"objectives": ["Build app"]}')
        assert result["objectives"] == ["Build app"]

    def test_json_in_code_block(self) -> None:
        from src.tools.sow_parser import _extract_json_from_response

        text = '```json\n{"objectives": ["Build app"]}\n```'
        result = _extract_json_from_response(text)
        assert result["objectives"] == ["Build app"]

    def test_invalid_json_raises(self) -> None:
        from src.tools.sow_parser import _extract_json_from_response

        with pytest.raises(json.JSONDecodeError):
            _extract_json_from_response("not json")


@pytest.mark.unit
class TestParseSow:
    """Verify parse_sow tool."""

    @patch("src.tools.sow_parser.boto3")
    def test_successful_parse(self, mock_boto3: MagicMock) -> None:
        from src.tools.sow_parser import parse_sow

        sow_result = {
            "objectives": ["Build S3 website"],
            "requirements": ["HTTPS support"],
            "constraints": ["Budget: $5k/month"],
            "deliverables": ["Static website"],
            "acceptance_criteria": ["Loads in <2s"],
            "timeline": "4 weeks",
        }
        mock_client = MagicMock()
        mock_client.converse.return_value = {
            "output": {
                "message": {
                    "content": [{"text": json.dumps(sow_result)}],
                },
            },
        }
        mock_boto3.client.return_value = mock_client

        mock_context = MagicMock()
        mock_context.invocation_state = {}

        result = parse_sow("Build a static website on AWS", mock_context)
        parsed = json.loads(result)

        assert parsed["objectives"] == ["Build S3 website"]
        assert parsed["timeline"] == "4 weeks"

    def test_empty_content(self) -> None:
        from src.tools.sow_parser import parse_sow

        mock_context = MagicMock()
        mock_context.invocation_state = {}

        result = parse_sow("", mock_context)

        assert "Error" in result
        assert "Empty" in result

    @patch("src.tools.sow_parser.boto3")
    def test_model_error(self, mock_boto3: MagicMock) -> None:
        from src.tools.sow_parser import parse_sow

        mock_client = MagicMock()
        mock_client.converse.side_effect = Exception("Model unavailable")
        mock_boto3.client.return_value = mock_client

        mock_context = MagicMock()
        mock_context.invocation_state = {}

        result = parse_sow("Some SOW content", mock_context)

        assert "Error" in result

    @patch("src.tools.sow_parser.boto3")
    def test_empty_model_response(self, mock_boto3: MagicMock) -> None:
        from src.tools.sow_parser import parse_sow

        mock_client = MagicMock()
        mock_client.converse.return_value = {"output": {"message": {"content": []}}}
        mock_boto3.client.return_value = mock_client

        mock_context = MagicMock()
        mock_context.invocation_state = {}

        result = parse_sow("Some SOW content", mock_context)

        assert "Error" in result
        assert "No text" in result
