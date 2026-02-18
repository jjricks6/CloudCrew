"""Tests for src/phases/production.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.resilience_hook import ResilienceHook


@pytest.mark.unit
class TestProductionSwarm:
    """Verify Production Swarm assembly."""

    @patch("src.phases.production.Swarm")
    @patch("src.phases.production.create_qa_agent")
    @patch("src.phases.production.create_security_agent")
    @patch("src.phases.production.create_data_agent")
    @patch("src.phases.production.create_infra_agent")
    @patch("src.phases.production.create_dev_agent")
    def test_create_production_swarm(
        self,
        mock_create_dev: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_data: MagicMock,
        mock_create_security: MagicMock,
        mock_create_qa: MagicMock,
        mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.production import create_production_swarm

        mock_dev = MagicMock(name="dev")
        mock_infra = MagicMock(name="infra")
        mock_data = MagicMock(name="data")
        mock_security = MagicMock(name="security")
        mock_qa = MagicMock(name="qa")
        mock_create_dev.return_value = mock_dev
        mock_create_infra.return_value = mock_infra
        mock_create_data.return_value = mock_data
        mock_create_security.return_value = mock_security
        mock_create_qa.return_value = mock_qa

        swarm = create_production_swarm()

        mock_swarm_cls.assert_called_once()
        call_kwargs = mock_swarm_cls.call_args

        # Verify nodes
        assert call_kwargs.kwargs["nodes"] == [mock_dev, mock_infra, mock_data, mock_security, mock_qa]

        # Verify entry point is Dev
        assert call_kwargs.kwargs["entry_point"] is mock_dev

        # Verify Swarm configuration
        assert call_kwargs.kwargs["max_handoffs"] == 25
        assert call_kwargs.kwargs["max_iterations"] == 25
        assert call_kwargs.kwargs["execution_timeout"] == 3600.0
        assert call_kwargs.kwargs["node_timeout"] == 600.0
        assert call_kwargs.kwargs["repetitive_handoff_detection_window"] == 8
        assert call_kwargs.kwargs["repetitive_handoff_min_unique_agents"] == 3
        assert call_kwargs.kwargs["id"] == "production-swarm"

        # ResilienceHook always attached
        hooks = call_kwargs.kwargs["hooks"]
        assert hooks is not None
        assert len(hooks) == 1
        assert isinstance(hooks[0], ResilienceHook)

        assert swarm is mock_swarm_cls.return_value

    @patch("src.phases.production.Swarm")
    @patch("src.phases.production.create_qa_agent")
    @patch("src.phases.production.create_security_agent")
    @patch("src.phases.production.create_data_agent")
    @patch("src.phases.production.create_infra_agent")
    @patch("src.phases.production.create_dev_agent")
    def test_all_agent_factories_called(
        self,
        mock_create_dev: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_data: MagicMock,
        mock_create_security: MagicMock,
        mock_create_qa: MagicMock,
        _mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.production import create_production_swarm

        create_production_swarm()

        mock_create_dev.assert_called_once()
        mock_create_infra.assert_called_once()
        mock_create_data.assert_called_once()
        mock_create_security.assert_called_once()
        mock_create_qa.assert_called_once()
