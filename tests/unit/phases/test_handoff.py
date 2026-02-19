"""Tests for src/phases/handoff.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.resilience_hook import ResilienceHook


@pytest.mark.unit
class TestHandoffSwarm:
    """Verify Handoff Swarm assembly."""

    @patch("src.phases.handoff.Swarm")
    @patch("src.phases.handoff.create_sa_agent")
    @patch("src.phases.handoff.create_pm_agent")
    def test_create_handoff_swarm(
        self,
        mock_create_pm: MagicMock,
        mock_create_sa: MagicMock,
        mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.handoff import create_handoff_swarm

        mock_pm = MagicMock(name="pm")
        mock_sa = MagicMock(name="sa")
        mock_create_pm.return_value = mock_pm
        mock_create_sa.return_value = mock_sa

        swarm = create_handoff_swarm()

        mock_swarm_cls.assert_called_once()
        call_kwargs = mock_swarm_cls.call_args

        # Verify nodes
        assert call_kwargs.kwargs["nodes"] == [mock_pm, mock_sa]

        # Verify entry point is PM
        assert call_kwargs.kwargs["entry_point"] is mock_pm

        # Verify Swarm configuration
        assert call_kwargs.kwargs["max_handoffs"] == 10
        assert call_kwargs.kwargs["max_iterations"] == 10
        assert call_kwargs.kwargs["execution_timeout"] == 1800.0
        assert call_kwargs.kwargs["node_timeout"] == 1800.0
        assert call_kwargs.kwargs["repetitive_handoff_detection_window"] == 6
        assert call_kwargs.kwargs["repetitive_handoff_min_unique_agents"] == 2
        assert call_kwargs.kwargs["id"] == "handoff-swarm"

        # ResilienceHook always attached (even without memory)
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        assert any(isinstance(h, ResilienceHook) for h in hooks)

        assert swarm is mock_swarm_cls.return_value

    @patch("src.phases.handoff.Swarm")
    @patch("src.phases.handoff.create_sa_agent")
    @patch("src.phases.handoff.create_pm_agent")
    def test_all_agent_factories_called(
        self,
        mock_create_pm: MagicMock,
        mock_create_sa: MagicMock,
        _mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.handoff import create_handoff_swarm

        create_handoff_swarm()

        mock_create_pm.assert_called_once()
        mock_create_sa.assert_called_once()

    @patch("src.phases.handoff.MemoryHook")
    @patch("src.phases.handoff.Swarm")
    @patch("src.phases.handoff.create_sa_agent")
    @patch("src.phases.handoff.create_pm_agent")
    def test_hooks_attached_when_memory_ids_provided(
        self,
        _mock_create_pm: MagicMock,
        _mock_create_sa: MagicMock,
        mock_swarm_cls: MagicMock,
        mock_hook_cls: MagicMock,
    ) -> None:
        from src.phases.handoff import create_handoff_swarm

        create_handoff_swarm(stm_memory_id="stm-001", ltm_memory_id="ltm-001")

        mock_hook_cls.assert_called_once_with(
            stm_memory_id="stm-001",
            ltm_memory_id="ltm-001",
        )
        call_kwargs = mock_swarm_cls.call_args
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        # ResilienceHook + MaxTokensRecoveryHook + MemoryHook
        assert len(hooks) == 3

    @patch("src.phases.handoff.Swarm")
    @patch("src.phases.handoff.create_sa_agent")
    @patch("src.phases.handoff.create_pm_agent")
    def test_resilience_hook_always_attached(
        self,
        _mock_create_pm: MagicMock,
        _mock_create_sa: MagicMock,
        mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.handoff import create_handoff_swarm

        create_handoff_swarm()

        call_kwargs = mock_swarm_cls.call_args
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        assert len(hooks) == 2
        assert isinstance(hooks[0], ResilienceHook)
        assert isinstance(hooks[1], MaxTokensRecoveryHook)
