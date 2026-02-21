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
class TestModelSingletons:
    """Verify model definitions exist."""

    @patch("src.agents.base.BedrockModel", new_callable=lambda: MagicMock)
    def test_opus_and_sonnet_defined(self, _mock_bedrock: MagicMock) -> None:
        import importlib

        import src.agents.base

        importlib.reload(src.agents.base)
        # Models are module-level singletons, should be non-None
        assert src.agents.base.OPUS is not None
        assert src.agents.base.SONNET is not None
