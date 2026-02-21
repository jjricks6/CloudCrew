"""Tests for src/agents/security.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestSecurityAgent:
    """Verify Security agent configuration."""

    def test_system_prompt_defined(self) -> None:
        from src.agents.security import SECURITY_SYSTEM_PROMPT

        assert len(SECURITY_SYSTEM_PROMPT) > 100
        assert "Security Engineer" in SECURITY_SYSTEM_PROMPT

    @patch("src.agents.security.OPUS")
    @patch("src.agents.security.Agent")
    def test_create_security_agent(self, mock_agent_cls: MagicMock, mock_opus: MagicMock) -> None:
        from src.agents.security import SECURITY_SYSTEM_PROMPT, create_security_agent

        agent = create_security_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args
        assert call_kwargs.kwargs["name"] == "security"
        assert call_kwargs.kwargs["model"] is mock_opus
        assert call_kwargs.kwargs["system_prompt"] == SECURITY_SYSTEM_PROMPT
        # 10 tools: git_read, git_list, git_write_security, checkov_scan, write_security_review,
        # read_task_ledger, create_board_task, update_board_task, add_task_comment, report_activity
        assert len(call_kwargs.kwargs["tools"]) == 10
        assert agent is mock_agent_cls.return_value

    def test_system_prompt_has_key_sections(self) -> None:
        from src.agents.security import SECURITY_SYSTEM_PROMPT

        required_sections = [
            "Your Role",
            "Security Standards",
            "Severity Classification",
            "Review Process",
            "Handoff Guidance",
            "Approval Criteria",
            "Recovery Awareness",
        ]
        for section in required_sections:
            assert section in SECURITY_SYSTEM_PROMPT, f"Missing section: {section}"
