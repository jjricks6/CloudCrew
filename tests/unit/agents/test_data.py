"""Tests for src/agents/data.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestDataAgent:
    """Verify Data agent configuration."""

    def test_system_prompt_defined(self) -> None:
        from src.agents.data import DATA_SYSTEM_PROMPT

        assert len(DATA_SYSTEM_PROMPT) > 100
        assert "Data Engineer" in DATA_SYSTEM_PROMPT

    @patch("src.agents.data.SONNET")
    @patch("src.agents.data.Agent")
    def test_create_data_agent(self, mock_agent_cls: MagicMock, mock_sonnet: MagicMock) -> None:
        from src.agents.data import DATA_SYSTEM_PROMPT, create_data_agent

        agent = create_data_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args
        assert call_kwargs.kwargs["name"] == "data"
        assert call_kwargs.kwargs["model"] is mock_sonnet
        assert call_kwargs.kwargs["system_prompt"] == DATA_SYSTEM_PROMPT
        # 9 tools: original 5 + create_board_task, update_board_task, add_task_comment, report_activity
        assert len(call_kwargs.kwargs["tools"]) == 9
        assert agent is mock_agent_cls.return_value

    def test_system_prompt_has_key_sections(self) -> None:
        from src.agents.data import DATA_SYSTEM_PROMPT

        required_sections = [
            "Your Role",
            "Data Standards",
            "Batch Writes",
            "Handoff Guidance",
            "Recovery Awareness",
        ]
        for section in required_sections:
            assert section in DATA_SYSTEM_PROMPT, f"Missing section: {section}"
