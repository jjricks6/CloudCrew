"""Tests for src/agents/base.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBuildInvocationState:
    """Verify build_invocation_state function."""

    @patch("src.agents.base.BedrockModel", new_callable=lambda: MagicMock)
    def test_returns_dict_with_all_fields(self, _mock_bedrock: MagicMock) -> None:
        from src.agents.base import build_invocation_state

        result = build_invocation_state(project_id="proj-001", phase="architecture")
        assert isinstance(result, dict)
        assert result["project_id"] == "proj-001"
        assert result["phase"] == "architecture"
        assert result["session_id"] == "proj-001-architecture"
        assert "task_ledger_table" in result
        assert "git_repo_url" in result
        assert "knowledge_base_id" in result
        assert "patterns_bucket" in result
        assert "activity_table" in result
        assert "stm_memory_id" in result
        assert "ltm_memory_id" in result

    @patch("src.agents.base.BedrockModel", new_callable=lambda: MagicMock)
    def test_custom_session_id(self, _mock_bedrock: MagicMock) -> None:
        from src.agents.base import build_invocation_state

        result = build_invocation_state(
            project_id="proj-001",
            phase="discovery",
            session_id="custom-session",
        )
        assert result["session_id"] == "custom-session"

    @patch("src.agents.base.BedrockModel", new_callable=lambda: MagicMock)
    def test_default_session_id_format(self, _mock_bedrock: MagicMock) -> None:
        from src.agents.base import build_invocation_state

        result = build_invocation_state(project_id="abc", phase="poc")
        assert result["session_id"] == "abc-poc"


@pytest.mark.unit
class TestGetBedrockSession:
    """Verify Bedrock session creation with API key support."""

    @patch("src.agents.base.get_bedrock_api_key")
    @patch("src.agents.base.boto3.Session")
    def test_session_with_api_key(self, mock_session_class: MagicMock, mock_get_key: MagicMock) -> None:
        """Session sets AWS_BEARER_TOKEN_BEDROCK env var when API key available."""
        import os

        mock_get_key.return_value = "test-api-key-123"
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        from src.agents.base import _get_bedrock_session

        result = _get_bedrock_session()

        assert result == mock_session
        assert os.environ.get("AWS_BEARER_TOKEN_BEDROCK") == "test-api-key-123"
        mock_session_class.assert_called_once_with(region_name="us-east-1")

        # Clean up env var
        os.environ.pop("AWS_BEARER_TOKEN_BEDROCK", None)

    @patch("src.agents.base.get_bedrock_api_key")
    @patch("src.agents.base.boto3.Session")
    def test_session_without_api_key(self, mock_session_class: MagicMock, mock_get_key: MagicMock) -> None:
        """Session uses IAM role when API key is not available."""
        mock_get_key.return_value = ""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        from src.agents.base import _get_bedrock_session

        result = _get_bedrock_session()

        assert result == mock_session
        mock_session_class.assert_called_once_with(region_name="us-east-1")


@pytest.mark.unit
class TestModelSingletons:
    """Verify model definitions exist."""

    @patch("src.agents.base.BedrockModel", new_callable=lambda: MagicMock)
    @patch("src.agents.base.get_bedrock_api_key")
    def test_opus_and_sonnet_defined(self, _mock_get_key: MagicMock, _mock_bedrock: MagicMock) -> None:
        import importlib

        import src.agents.base

        importlib.reload(src.agents.base)
        # Models are module-level singletons, should be non-None
        assert src.agents.base.OPUS is not None
        assert src.agents.base.SONNET is not None
