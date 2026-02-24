"""Tests for src/phases/poc.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.resilience_hook import ResilienceHook


@pytest.mark.unit
class TestPOCSwarm:
    """Verify POC Swarm assembly."""

    @patch("src.phases.poc.Swarm")
    @patch("src.phases.poc.create_qa_agent")
    @patch("src.phases.poc.create_sa_agent")
    @patch("src.phases.poc.create_security_agent")
    @patch("src.phases.poc.create_data_agent")
    @patch("src.phases.poc.create_infra_agent")
    @patch("src.phases.poc.create_dev_agent")
    def test_create_poc_swarm(
        self,
        mock_create_dev: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_data: MagicMock,
        mock_create_security: MagicMock,
        mock_create_sa: MagicMock,
        mock_create_qa: MagicMock,
        mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.poc import create_poc_swarm

        mock_dev = MagicMock(name="dev")
        mock_infra = MagicMock(name="infra")
        mock_data = MagicMock(name="data")
        mock_security = MagicMock(name="security")
        mock_sa = MagicMock(name="sa")
        mock_qa = MagicMock(name="qa")
        mock_create_dev.return_value = mock_dev
        mock_create_infra.return_value = mock_infra
        mock_create_data.return_value = mock_data
        mock_create_security.return_value = mock_security
        mock_create_sa.return_value = mock_sa
        mock_create_qa.return_value = mock_qa

        swarm = create_poc_swarm()

        mock_swarm_cls.assert_called_once()
        call_kwargs = mock_swarm_cls.call_args

        # Verify all 6 specialist agents are nodes
        assert call_kwargs.kwargs["nodes"] == [
            mock_dev,
            mock_infra,
            mock_data,
            mock_security,
            mock_sa,
            mock_qa,
        ]

        # Verify entry point is Dev
        assert call_kwargs.kwargs["entry_point"] is mock_dev

        # Verify Swarm configuration
        assert call_kwargs.kwargs["max_handoffs"] == 25
        assert call_kwargs.kwargs["max_iterations"] == 25
        assert call_kwargs.kwargs["execution_timeout"] == 2400.0
        assert call_kwargs.kwargs["node_timeout"] == 1800.0
        assert call_kwargs.kwargs["repetitive_handoff_detection_window"] == 8
        assert call_kwargs.kwargs["repetitive_handoff_min_unique_agents"] == 3
        assert call_kwargs.kwargs["id"] == "poc-swarm"

        # ResilienceHook + MaxTokensRecoveryHook + ActivityHook always attached
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        assert len(hooks) == 3
        assert isinstance(hooks[0], ResilienceHook)
        assert isinstance(hooks[1], MaxTokensRecoveryHook)
        assert isinstance(hooks[2], ActivityHook)

        assert swarm is mock_swarm_cls.return_value

    @patch("src.phases.poc.Swarm")
    @patch("src.phases.poc.create_qa_agent")
    @patch("src.phases.poc.create_sa_agent")
    @patch("src.phases.poc.create_security_agent")
    @patch("src.phases.poc.create_data_agent")
    @patch("src.phases.poc.create_infra_agent")
    @patch("src.phases.poc.create_dev_agent")
    def test_all_agent_factories_called(
        self,
        mock_create_dev: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_data: MagicMock,
        mock_create_security: MagicMock,
        mock_create_sa: MagicMock,
        mock_create_qa: MagicMock,
        _mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.poc import create_poc_swarm

        create_poc_swarm()

        mock_create_dev.assert_called_once()
        mock_create_infra.assert_called_once()
        mock_create_data.assert_called_once()
        mock_create_security.assert_called_once()
        mock_create_sa.assert_called_once()
        mock_create_qa.assert_called_once()
