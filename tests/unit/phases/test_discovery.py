"""Tests for src/phases/discovery.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.resilience_hook import ResilienceHook


@pytest.mark.unit
class TestDiscoverySwarm:
    """Verify Discovery Swarm assembly."""

    @patch("src.phases.discovery.Swarm")
    @patch("src.phases.discovery.create_qa_agent")
    @patch("src.phases.discovery.create_security_agent")
    @patch("src.phases.discovery.create_data_agent")
    @patch("src.phases.discovery.create_infra_agent")
    @patch("src.phases.discovery.create_dev_agent")
    @patch("src.phases.discovery.create_sa_agent")
    @patch("src.phases.discovery.create_pm_agent")
    def test_create_discovery_swarm(
        self,
        mock_create_pm: MagicMock,
        mock_create_sa: MagicMock,
        mock_create_dev: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_data: MagicMock,
        mock_create_security: MagicMock,
        mock_create_qa: MagicMock,
        mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.discovery import create_discovery_swarm

        mock_pm = MagicMock(name="pm")
        mock_sa = MagicMock(name="sa")
        mock_dev = MagicMock(name="dev")
        mock_infra = MagicMock(name="infra")
        mock_data = MagicMock(name="data")
        mock_security = MagicMock(name="security")
        mock_qa = MagicMock(name="qa")
        mock_create_pm.return_value = mock_pm
        mock_create_sa.return_value = mock_sa
        mock_create_dev.return_value = mock_dev
        mock_create_infra.return_value = mock_infra
        mock_create_data.return_value = mock_data
        mock_create_security.return_value = mock_security
        mock_create_qa.return_value = mock_qa

        swarm = create_discovery_swarm()

        mock_swarm_cls.assert_called_once()
        call_kwargs = mock_swarm_cls.call_args

        # Verify all 7 agents are nodes
        assert call_kwargs.kwargs["nodes"] == [
            mock_pm,
            mock_sa,
            mock_dev,
            mock_infra,
            mock_data,
            mock_security,
            mock_qa,
        ]

        # Verify entry point is PM
        assert call_kwargs.kwargs["entry_point"] is mock_pm

        # Verify Swarm configuration
        assert call_kwargs.kwargs["max_handoffs"] == 15
        assert call_kwargs.kwargs["max_iterations"] == 15
        assert call_kwargs.kwargs["execution_timeout"] == 1800.0
        assert call_kwargs.kwargs["node_timeout"] == 1800.0
        assert call_kwargs.kwargs["repetitive_handoff_detection_window"] == 8
        assert call_kwargs.kwargs["repetitive_handoff_min_unique_agents"] == 3
        assert call_kwargs.kwargs["id"] == "discovery-swarm"

        # ResilienceHook always attached (even without memory)
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        assert any(isinstance(h, ResilienceHook) for h in hooks)

        assert swarm is mock_swarm_cls.return_value

    @patch("src.phases.discovery.Swarm")
    @patch("src.phases.discovery.create_qa_agent")
    @patch("src.phases.discovery.create_security_agent")
    @patch("src.phases.discovery.create_data_agent")
    @patch("src.phases.discovery.create_infra_agent")
    @patch("src.phases.discovery.create_dev_agent")
    @patch("src.phases.discovery.create_sa_agent")
    @patch("src.phases.discovery.create_pm_agent")
    def test_all_agent_factories_called(
        self,
        mock_create_pm: MagicMock,
        mock_create_sa: MagicMock,
        mock_create_dev: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_data: MagicMock,
        mock_create_security: MagicMock,
        mock_create_qa: MagicMock,
        _mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.discovery import create_discovery_swarm

        create_discovery_swarm()

        mock_create_pm.assert_called_once()
        mock_create_sa.assert_called_once()
        mock_create_dev.assert_called_once()
        mock_create_infra.assert_called_once()
        mock_create_data.assert_called_once()
        mock_create_security.assert_called_once()
        mock_create_qa.assert_called_once()

    @patch("src.phases.discovery.MemoryHook")
    @patch("src.phases.discovery.Swarm")
    @patch("src.phases.discovery.create_qa_agent")
    @patch("src.phases.discovery.create_security_agent")
    @patch("src.phases.discovery.create_data_agent")
    @patch("src.phases.discovery.create_infra_agent")
    @patch("src.phases.discovery.create_dev_agent")
    @patch("src.phases.discovery.create_sa_agent")
    @patch("src.phases.discovery.create_pm_agent")
    def test_hooks_attached_when_memory_ids_provided(
        self,
        _mock_create_pm: MagicMock,
        _mock_create_sa: MagicMock,
        _mock_create_dev: MagicMock,
        _mock_create_infra: MagicMock,
        _mock_create_data: MagicMock,
        _mock_create_security: MagicMock,
        _mock_create_qa: MagicMock,
        mock_swarm_cls: MagicMock,
        mock_hook_cls: MagicMock,
    ) -> None:
        from src.phases.discovery import create_discovery_swarm

        create_discovery_swarm(stm_memory_id="stm-001", ltm_memory_id="ltm-001")

        mock_hook_cls.assert_called_once_with(
            stm_memory_id="stm-001",
            ltm_memory_id="ltm-001",
        )
        call_kwargs = mock_swarm_cls.call_args
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        # ResilienceHook + MaxTokensRecoveryHook + ActivityHook + MemoryHook
        assert len(hooks) == 4

    @patch("src.phases.discovery.Swarm")
    @patch("src.phases.discovery.create_qa_agent")
    @patch("src.phases.discovery.create_security_agent")
    @patch("src.phases.discovery.create_data_agent")
    @patch("src.phases.discovery.create_infra_agent")
    @patch("src.phases.discovery.create_dev_agent")
    @patch("src.phases.discovery.create_sa_agent")
    @patch("src.phases.discovery.create_pm_agent")
    def test_resilience_hook_always_attached(
        self,
        _mock_create_pm: MagicMock,
        _mock_create_sa: MagicMock,
        _mock_create_dev: MagicMock,
        _mock_create_infra: MagicMock,
        _mock_create_data: MagicMock,
        _mock_create_security: MagicMock,
        _mock_create_qa: MagicMock,
        mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.discovery import create_discovery_swarm

        create_discovery_swarm()

        call_kwargs = mock_swarm_cls.call_args
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        assert len(hooks) == 3
        assert isinstance(hooks[0], ResilienceHook)
        assert isinstance(hooks[1], MaxTokensRecoveryHook)
        assert isinstance(hooks[2], ActivityHook)
