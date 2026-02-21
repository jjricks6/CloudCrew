"""Tests for src/tools/activity_tools.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestReportActivity:
    """Verify report_activity tool behavior."""

    @patch("src.tools.activity_tools.broadcast_to_project")
    @patch("src.tools.activity_tools.store_activity_event")
    def test_stores_event_with_display_name(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "activity_table": "cloudcrew-activity",
        }

        result = report_activity("sa", "Designing API Gateway integration", ctx)

        mock_store.assert_called_once_with(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="agent_active",
            agent_name="Solutions Architect",
            phase="ARCHITECTURE",
            detail="Designing API Gateway integration",
        )
        assert "Activity reported" in result

    @patch("src.tools.activity_tools.broadcast_to_project")
    @patch("src.tools.activity_tools.store_activity_event")
    def test_broadcasts_event_with_display_name(self, _mock_store: MagicMock, mock_broadcast: MagicMock) -> None:
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "activity_table": "cloudcrew-activity",
        }

        report_activity("infra", "Provisioning VPC subnets", ctx)

        mock_broadcast.assert_called_once_with(
            "proj-1",
            {
                "event": "agent_active",
                "project_id": "proj-1",
                "agent_name": "Infrastructure",
                "phase": "ARCHITECTURE",
                "detail": "Provisioning VPC subnets",
            },
        )

    @patch("src.tools.activity_tools.broadcast_to_project")
    @patch("src.tools.activity_tools.store_activity_event")
    def test_unknown_agent_uses_raw_name(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "activity_table": "cloudcrew-activity",
        }

        report_activity("custom_agent", "Doing something", ctx)

        assert mock_store.call_args.kwargs["agent_name"] == "custom_agent"

    @patch("src.tools.activity_tools.broadcast_to_project")
    @patch("src.tools.activity_tools.store_activity_event")
    def test_graceful_when_no_activity_table(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "activity_table": "",
        }

        result = report_activity("sa", "Working", ctx)

        mock_store.assert_not_called()
        assert "not configured" in result

    @patch("src.tools.activity_tools.broadcast_to_project")
    @patch("src.tools.activity_tools.store_activity_event")
    def test_error_when_no_project_id(self, mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "",
            "phase": "ARCHITECTURE",
            "activity_table": "cloudcrew-activity",
        }

        result = report_activity("sa", "Working", ctx)

        mock_store.assert_not_called()
        assert "Error" in result

    @patch("src.tools.activity_tools.broadcast_to_project")
    @patch("src.tools.activity_tools.store_activity_event", side_effect=RuntimeError("DDB error"))
    def test_store_failure_returns_error(self, _mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "activity_table": "cloudcrew-activity",
        }

        result = report_activity("sa", "Working", ctx)

        assert "Error storing" in result

    @patch("src.tools.activity_tools.broadcast_to_project", side_effect=RuntimeError("WS error"))
    @patch("src.tools.activity_tools.store_activity_event")
    def test_broadcast_failure_still_succeeds(self, _mock_store: MagicMock, _mock_broadcast: MagicMock) -> None:
        """Broadcast failure is non-fatal — store succeeded."""
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "activity_table": "cloudcrew-activity",
        }

        result = report_activity("sa", "Working", ctx)

        # Should return success since store worked
        assert "Activity reported" in result

    @patch("src.tools.activity_tools.broadcast_to_project")
    @patch("src.tools.activity_tools.store_activity_event")
    def test_truncates_long_detail(self, mock_store: MagicMock, mock_broadcast: MagicMock) -> None:
        from src.tools.activity_tools import report_activity

        ctx = MagicMock()
        ctx.invocation_state = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "activity_table": "cloudcrew-activity",
        }

        long_detail = "x" * 1000
        report_activity("sa", long_detail, ctx)

        stored_detail = mock_store.call_args.kwargs["detail"]
        assert len(stored_detail) == 500

        broadcast_detail = mock_broadcast.call_args.args[1]["detail"]
        assert len(broadcast_detail) == 500
