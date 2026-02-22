"""Tests for src/agents/qa.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestQAAgent:
    """Verify QA agent configuration."""

    def test_system_prompt_defined(self) -> None:
        from src.agents.qa import QA_SYSTEM_PROMPT

        assert len(QA_SYSTEM_PROMPT) > 100
        assert "Quality Assurance" in QA_SYSTEM_PROMPT

    @patch("src.agents.qa.SONNET")
    @patch("src.agents.qa.Agent")
    def test_create_qa_agent(self, mock_agent_cls: MagicMock, mock_sonnet: MagicMock) -> None:
        from src.agents.qa import QA_SYSTEM_PROMPT, create_qa_agent

        agent = create_qa_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args
        assert call_kwargs.kwargs["name"] == "qa"
        assert call_kwargs.kwargs["model"] is mock_sonnet
        assert call_kwargs.kwargs["system_prompt"] == QA_SYSTEM_PROMPT
        # 10 tools: original 5 + create_board_task, update_board_task, add_task_comment, report_activity, web_search
        assert len(call_kwargs.kwargs["tools"]) == 10
        assert agent is mock_agent_cls.return_value

    def test_system_prompt_has_key_sections(self) -> None:
        from src.agents.qa import QA_SYSTEM_PROMPT

        required_sections = [
            "Your Role",
            "Testing Standards",
            "Batch Writes",
            "Quality Gates",
            "Handoff Guidance",
            "Recovery Awareness",
        ]
        for section in required_sections:
            assert section in QA_SYSTEM_PROMPT, f"Missing section: {section}"
