"""Tests for src/agents/sa.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestSAAgent:
    """Verify SA agent configuration."""

    def test_system_prompt_defined(self) -> None:
        from src.agents.sa import SA_SYSTEM_PROMPT

        assert len(SA_SYSTEM_PROMPT) > 100
        assert "Solutions Architect" in SA_SYSTEM_PROMPT
        assert "Well-Architected" in SA_SYSTEM_PROMPT
        assert "ADR" in SA_SYSTEM_PROMPT

    @patch("src.agents.sa.OPUS")
    @patch("src.agents.sa.Agent")
    def test_create_sa_agent(self, mock_agent_cls: MagicMock, mock_opus: MagicMock) -> None:
        from src.agents.sa import SA_SYSTEM_PROMPT, create_sa_agent

        agent = create_sa_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args
        assert call_kwargs.kwargs["name"] == "sa"
        assert call_kwargs.kwargs["model"] is mock_opus
        assert call_kwargs.kwargs["system_prompt"] == SA_SYSTEM_PROMPT
        # 8 tools: git_read, git_list, git_write_architecture, write_adr, read_task_ledger,
        # create_board_task, update_board_task, add_task_comment
        assert len(call_kwargs.kwargs["tools"]) == 8
        assert agent is mock_agent_cls.return_value

    def test_system_prompt_has_key_sections(self) -> None:
        from src.agents.sa import SA_SYSTEM_PROMPT

        required_sections = [
            "Your Role",
            "Architecture Principles",
            "ADR Format",
            "Decision Framework",
            "Handoff Guidance",
            "Review Triggers",
            "Recovery Awareness",
        ]
        for section in required_sections:
            assert section in SA_SYSTEM_PROMPT, f"Missing section: {section}"
