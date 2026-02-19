"""Tests for src/hooks/activity_hook.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.activity_hook import ActivityHook


@pytest.mark.unit
class TestRegister:
    """Verify hook registration."""

    def test_registers_two_callbacks(self) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")
        registry = MagicMock()
        hook.register_hooks(registry)
        assert registry.add_callback.call_count == 2


@pytest.mark.unit
@patch("src.hooks.activity_hook.broadcast_to_project")
class TestActivityHookEvents:
    """Verify activity event emission."""

    def _make_before_event(self, node_id: str = "pm") -> MagicMock:
        event = MagicMock()
        event.node_id = node_id
        return event

    def _make_after_event(self, node_id: str = "pm") -> MagicMock:
        event = MagicMock()
        event.node_id = node_id
        event.source = MagicMock()
        event.source.state = MagicMock()
        event.source.state.results = {}
        return event

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_emits_agent_active_on_node_start(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")
        event = self._make_before_event(node_id="sa")

        hook._on_node_start(event)

        mock_store.assert_called_once_with(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="agent_active",
            agent_name="sa",
            phase="DISCOVERY",
            detail="Agent sa started working",
        )

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_emits_handoff_when_different_node(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        # First node starts
        hook._on_node_start(self._make_before_event(node_id="pm"))
        mock_store.reset_mock()

        # Different node starts — handoff
        hook._on_node_start(self._make_before_event(node_id="sa"))

        # Should have two calls: handoff + agent_active
        assert mock_store.call_count == 2
        handoff_call = mock_store.call_args_list[0]
        assert handoff_call.kwargs["event_type"] == "handoff"
        assert "pm" in handoff_call.kwargs["detail"]
        assert "sa" in handoff_call.kwargs["detail"]

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_no_handoff_when_same_node(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        hook._on_node_start(self._make_before_event(node_id="pm"))
        mock_store.reset_mock()

        # Same node starts again — no handoff
        hook._on_node_start(self._make_before_event(node_id="pm"))

        assert mock_store.call_count == 1
        assert mock_store.call_args.kwargs["event_type"] == "agent_active"

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_emits_agent_idle_on_node_complete(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")
        event = self._make_after_event(node_id="pm")

        hook._on_node_complete(event)

        mock_store.assert_called_once_with(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="agent_idle",
            agent_name="pm",
            phase="DISCOVERY",
            detail="Agent pm finished",
        )

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_noop_when_activity_table_empty(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        hook._on_node_start(self._make_before_event())
        hook._on_node_complete(self._make_after_event())

        mock_store.assert_not_called()

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_broadcasts_event_on_node_start(self, _mock_store: MagicMock, mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")
        hook._on_node_start(self._make_before_event(node_id="sa"))

        mock_broadcast.assert_called_once_with(
            "proj-1",
            {
                "event": "agent_active",
                "project_id": "proj-1",
                "agent_name": "sa",
                "phase": "DISCOVERY",
                "detail": "Agent sa started working",
            },
        )

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event", side_effect=RuntimeError("DDB error"))
    def test_store_exception_is_logged_not_raised(self, _mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        # Should not raise — store exception is caught and logged
        hook._on_node_start(self._make_before_event())

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_broadcast_exception_is_logged_not_raised(self, _mock_store: MagicMock, mock_broadcast: MagicMock) -> None:
        mock_broadcast.side_effect = RuntimeError("WS error")
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        # Should not raise — broadcast exception is caught and logged
        hook._on_node_start(self._make_before_event())
