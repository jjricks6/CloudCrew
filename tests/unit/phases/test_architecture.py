"""Tests for src/phases/architecture.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestArchitectureSwarm:
    """Verify Architecture Swarm assembly."""

    @patch("src.phases.architecture.Swarm")
    @patch("src.phases.architecture.create_security_agent")
    @patch("src.phases.architecture.create_infra_agent")
    @patch("src.phases.architecture.create_sa_agent")
    def test_create_architecture_swarm(
        self,
        mock_create_sa: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_security: MagicMock,
        mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.architecture import create_architecture_swarm

        mock_sa = MagicMock(name="sa")
        mock_infra = MagicMock(name="infra")
        mock_security = MagicMock(name="security")
        mock_create_sa.return_value = mock_sa
        mock_create_infra.return_value = mock_infra
        mock_create_security.return_value = mock_security

        swarm = create_architecture_swarm()

        mock_swarm_cls.assert_called_once()
        call_kwargs = mock_swarm_cls.call_args

        # Verify nodes
        assert call_kwargs.kwargs["nodes"] == [mock_sa, mock_infra, mock_security]

        # Verify entry point
        assert call_kwargs.kwargs["entry_point"] is mock_sa

        # Verify Swarm configuration
        assert call_kwargs.kwargs["max_handoffs"] == 15
        assert call_kwargs.kwargs["max_iterations"] == 15
        assert call_kwargs.kwargs["execution_timeout"] == 1200.0
        assert call_kwargs.kwargs["node_timeout"] == 300.0
        assert call_kwargs.kwargs["repetitive_handoff_detection_window"] == 8
        assert call_kwargs.kwargs["repetitive_handoff_min_unique_agents"] == 3
        assert call_kwargs.kwargs["id"] == "architecture-swarm"

        assert swarm is mock_swarm_cls.return_value

    @patch("src.phases.architecture.Swarm")
    @patch("src.phases.architecture.create_security_agent")
    @patch("src.phases.architecture.create_infra_agent")
    @patch("src.phases.architecture.create_sa_agent")
    def test_all_agent_factories_called(
        self,
        mock_create_sa: MagicMock,
        mock_create_infra: MagicMock,
        mock_create_security: MagicMock,
        _mock_swarm_cls: MagicMock,
    ) -> None:
        from src.phases.architecture import create_architecture_swarm

        create_architecture_swarm()

        mock_create_sa.assert_called_once()
        mock_create_infra.assert_called_once()
        mock_create_security.assert_called_once()
