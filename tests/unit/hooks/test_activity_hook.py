"""Tests for src/hooks/activity_hook.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.activity_hook import ActivityHook, _display_name
from src.state.models import AGENT_DISPLAY_NAMES


@pytest.mark.unit
class TestDisplayName:
    """Verify display name translation."""

    def test_known_agent(self) -> None:
        assert _display_name("sa") == "Solutions Architect"
        assert _display_name("infra") == "Infrastructure"
        assert _display_name("security") == "Security Engineer"

    def test_unknown_agent_returns_raw(self) -> None:
        assert _display_name("unknown_agent") == "unknown_agent"

    def test_all_agents_have_display_names(self) -> None:
        expected = {"pm", "sa", "dev", "infra", "data", "security", "qa"}
        assert set(AGENT_DISPLAY_NAMES.keys()) == expected


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
    def test_no_agent_active_on_node_start(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        """Hook no longer emits agent_active — that comes from report_activity tool."""
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")
        hook._on_node_start(self._make_before_event(node_id="sa"))

        # No store call — agent_active is not emitted by the hook
        mock_store.assert_not_called()

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_emits_handoff_with_display_names(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="ARCHITECTURE")

        # First node starts
        hook._on_node_start(self._make_before_event(node_id="sa"))

        # Different node starts — handoff
        hook._on_node_start(self._make_before_event(node_id="infra"))

        mock_store.assert_called_once_with(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="handoff",
            agent_name="Infrastructure",
            phase="ARCHITECTURE",
            detail="Handoff from Solutions Architect to Infrastructure",
        )

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_no_handoff_when_same_node(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        hook._on_node_start(self._make_before_event(node_id="pm"))
        hook._on_node_start(self._make_before_event(node_id="pm"))

        # No events — same node, no handoff, no agent_active
        mock_store.assert_not_called()

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_emits_agent_idle_with_display_name(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")
        event = self._make_after_event(node_id="pm")

        hook._on_node_complete(event)

        mock_store.assert_called_once_with(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="agent_idle",
            agent_name="Project Manager",
            phase="DISCOVERY",
            detail="Project Manager finished",
        )

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_agent_idle_error_uses_display_name(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="ARCHITECTURE")
        event = self._make_after_event(node_id="infra")
        # Simulate an error result
        result_mock = MagicMock()
        result_mock.result = RuntimeError("Terraform failed")
        event.source.state.results = {"infra": result_mock}

        hook._on_node_complete(event)

        call_kwargs = mock_store.call_args.kwargs
        assert call_kwargs["agent_name"] == "Infrastructure"
        assert "Infrastructure encountered an error" in call_kwargs["detail"]
        assert "Terraform failed" in call_kwargs["detail"]

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_noop_when_activity_table_empty(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        hook._on_node_start(self._make_before_event())
        hook._on_node_complete(self._make_after_event())

        mock_store.assert_not_called()

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_broadcasts_handoff_with_display_names(self, _mock_store: MagicMock, mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="ARCHITECTURE")

        hook._on_node_start(self._make_before_event(node_id="sa"))
        hook._on_node_start(self._make_before_event(node_id="infra"))

        mock_broadcast.assert_called_once_with(
            "proj-1",
            {
                "event": "handoff",
                "project_id": "proj-1",
                "agent_name": "Infrastructure",
                "phase": "ARCHITECTURE",
                "detail": "Handoff from Solutions Architect to Infrastructure",
            },
        )

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event", side_effect=RuntimeError("DDB error"))
    def test_store_exception_is_logged_not_raised(self, _mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        # Should not raise — store exception is caught and logged
        hook._on_node_complete(self._make_after_event())

    @patch("src.hooks.activity_hook.ACTIVITY_TABLE", "cloudcrew-activity")
    @patch("src.hooks.activity_hook.store_activity_event")
    def test_broadcast_exception_is_logged_not_raised(self, _mock_store: MagicMock, mock_broadcast: MagicMock) -> None:
        mock_broadcast.side_effect = RuntimeError("WS error")
        hook = ActivityHook(project_id="proj-1", phase="DISCOVERY")

        # Should not raise — broadcast exception is caught and logged
        hook._on_node_complete(self._make_after_event())
