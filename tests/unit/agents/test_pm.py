"""Tests for src/agents/pm.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestPMAgent:
    """Verify PM agent configuration."""

    def test_system_prompt_defined(self) -> None:
        from src.agents.pm import PM_SYSTEM_PROMPT

        assert len(PM_SYSTEM_PROMPT) > 100
        assert "Project Manager" in PM_SYSTEM_PROMPT

    @patch("src.agents.pm.OPUS")
    @patch("src.agents.pm.Agent")
    def test_create_pm_agent(self, mock_agent_cls: MagicMock, mock_opus: MagicMock) -> None:
        from src.agents.pm import PM_SYSTEM_PROMPT, create_pm_agent

        agent = create_pm_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args
        assert call_kwargs.kwargs["name"] == "pm"
        assert call_kwargs.kwargs["model"] is mock_opus
        assert call_kwargs.kwargs["system_prompt"] == PM_SYSTEM_PROMPT
        assert len(call_kwargs.kwargs["tools"]) == 11
        assert agent is mock_agent_cls.return_value

    def test_system_prompt_has_key_sections(self) -> None:
        from src.agents.pm import PM_SYSTEM_PROMPT

        required_sections = [
            "Your Role",
            "Task Ledger",
            "Decision Framework",
            "Communication Style",
            "Handoff Guidance",
            "Standalone Mode",
            "Recovery Awareness",
        ]
        for section in required_sections:
            assert section in PM_SYSTEM_PROMPT, f"Missing section: {section}"
