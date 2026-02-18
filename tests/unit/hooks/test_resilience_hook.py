"""Tests for src/hooks/resilience_hook.py."""

import logging
from unittest.mock import MagicMock

import pytest
from src.hooks.resilience_hook import ResilienceHook


@pytest.mark.unit
class TestResilienceHookRegister:
    """Verify hook registration."""

    def test_registers_three_callbacks(self) -> None:
        hook = ResilienceHook()
        registry = MagicMock()
        hook.register_hooks(registry)
        assert registry.add_callback.call_count == 3


@pytest.mark.unit
class TestOnNodeStart:
    """Verify node start logging."""

    def test_logs_node_start(self, caplog: pytest.LogCaptureFixture) -> None:
        hook = ResilienceHook()
        event = MagicMock()
        event.node_id = "sa"
        event.source = MagicMock()
        event.source.id = "discovery-swarm"

        with caplog.at_level(logging.INFO, logger="src.hooks.resilience_hook"):
            hook._on_node_start(event)

        assert "node_start" in caplog.text
        assert "sa" in caplog.text
        assert "discovery-swarm" in caplog.text


@pytest.mark.unit
class TestOnNodeComplete:
    """Verify node completion logging."""

    def test_logs_success(self, caplog: pytest.LogCaptureFixture) -> None:
        hook = ResilienceHook()
        event = MagicMock()
        event.node_id = "pm"
        event.source.id = "discovery-swarm"

        # Mock successful NodeResult
        node_result = MagicMock()
        node_result.status.value = "completed"
        node_result.execution_time = 5000
        node_result.result = "some result"  # Not an exception
        event.source.state.results = {"pm": node_result}

        with caplog.at_level(logging.INFO, logger="src.hooks.resilience_hook"):
            hook._on_node_complete(event)

        assert "node_complete" in caplog.text
        assert "completed" in caplog.text
        assert "pm" in caplog.text

    def test_logs_failure_with_error(self, caplog: pytest.LogCaptureFixture) -> None:
        hook = ResilienceHook()
        event = MagicMock()
        event.node_id = "sa"
        event.source.id = "discovery-swarm"

        # Mock failed NodeResult with exception
        node_result = MagicMock()
        node_result.status.value = "failed"
        node_result.execution_time = 300000
        node_result.result = Exception("Node 'sa' execution timed out after 300.0s")
        event.source.state.results = {"sa": node_result}

        with caplog.at_level(logging.WARNING, logger="src.hooks.resilience_hook"):
            hook._on_node_complete(event)

        assert "node_complete" in caplog.text
        assert "failed" in caplog.text
        assert "timed out" in caplog.text

    def test_handles_missing_result(self, caplog: pytest.LogCaptureFixture) -> None:
        hook = ResilienceHook()
        event = MagicMock()
        event.node_id = "missing"
        event.source.id = "test-swarm"
        event.source.state.results = {}

        with caplog.at_level(logging.INFO, logger="src.hooks.resilience_hook"):
            hook._on_node_complete(event)

        assert "unknown" in caplog.text


@pytest.mark.unit
class TestOnSwarmComplete:
    """Verify swarm completion logging."""

    def test_logs_swarm_status(self, caplog: pytest.LogCaptureFixture) -> None:
        hook = ResilienceHook()
        event = MagicMock()
        event.source.id = "discovery-swarm"
        event.source.state.completion_status.value = "completed"
        event.source.state.node_history = [MagicMock(), MagicMock()]
        event.source.state.execution_time = 120000

        with caplog.at_level(logging.INFO, logger="src.hooks.resilience_hook"):
            hook._on_swarm_complete(event)

        assert "swarm_complete" in caplog.text
        assert "completed" in caplog.text
        assert "nodes=2" in caplog.text
