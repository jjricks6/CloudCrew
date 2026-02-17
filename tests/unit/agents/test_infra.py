"""Tests for src/agents/infra.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestInfraAgent:
    """Verify Infra agent configuration."""

    def test_system_prompt_defined(self) -> None:
        from src.agents.infra import INFRA_SYSTEM_PROMPT

        assert len(INFRA_SYSTEM_PROMPT) > 100
        assert "Infrastructure Engineer" in INFRA_SYSTEM_PROMPT
        assert "Terraform" in INFRA_SYSTEM_PROMPT

    @patch("src.agents.infra.SONNET")
    @patch("src.agents.infra.Agent")
    def test_create_infra_agent(self, mock_agent_cls: MagicMock, mock_sonnet: MagicMock) -> None:
        from src.agents.infra import INFRA_SYSTEM_PROMPT, create_infra_agent

        agent = create_infra_agent()
        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args
        assert call_kwargs.kwargs["name"] == "infra"
        assert call_kwargs.kwargs["model"] is mock_sonnet
        assert call_kwargs.kwargs["system_prompt"] == INFRA_SYSTEM_PROMPT
        assert len(call_kwargs.kwargs["tools"]) == 5
        assert agent is mock_agent_cls.return_value

    def test_system_prompt_has_key_sections(self) -> None:
        from src.agents.infra import INFRA_SYSTEM_PROMPT

        required_sections = [
            "Your Role",
            "Terraform Standards",
            "Security Requirements",
            "Self-Validation Workflow",
            "Handoff Guidance",
            "Review Triggers",
        ]
        for section in required_sections:
            assert section in INFRA_SYSTEM_PROMPT, f"Missing section: {section}"
