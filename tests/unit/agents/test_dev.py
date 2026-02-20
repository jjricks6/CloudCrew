"""Tests for src/agents/dev.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestDevAgent:
    """Verify Dev agent configuration."""

    def test_system_prompt_defined(self) -> None:
        from src.agents.dev import DEV_SYSTEM_PROMPT

        assert len(DEV_SYSTEM_PROMPT) > 100
        assert "Application Developer" in DEV_SYSTEM_PROMPT

    @patch("src.agents.dev.SONNET")
    @patch("src.agents.dev.Agent")
    def test_create_dev_agent(self, mock_agent_cls: MagicMock, mock_sonnet: MagicMock) -> None:
        from src.agents.dev import DEV_SYSTEM_PROMPT, create_dev_agent

        agent = create_dev_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args
        assert call_kwargs.kwargs["name"] == "dev"
        assert call_kwargs.kwargs["model"] is mock_sonnet
        assert call_kwargs.kwargs["system_prompt"] == DEV_SYSTEM_PROMPT
        # 8 tools: original 5 + create_board_task, update_board_task, add_task_comment
        assert len(call_kwargs.kwargs["tools"]) == 8
        assert agent is mock_agent_cls.return_value

    def test_system_prompt_has_key_sections(self) -> None:
        from src.agents.dev import DEV_SYSTEM_PROMPT

        required_sections = [
            "Your Role",
            "Code Standards",
            "Batch Writes",
            "Self-Validation Workflow",
            "Handoff Guidance",
            "Recovery Awareness",
        ]
        for section in required_sections:
            assert section in DEV_SYSTEM_PROMPT, f"Missing section: {section}"
