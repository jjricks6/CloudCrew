"""Tests for src/state/activity.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.activity import get_recent_activity, store_activity_event


@pytest.mark.unit
class TestStoreActivityEvent:
    """Verify storing activity events to DynamoDB."""

    @patch("src.state.activity._get_table")
    def test_stores_event_with_correct_keys(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        result = store_activity_event(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="agent_active",
            agent_name="pm",
            phase="DISCOVERY",
            detail="Agent pm started working",
        )

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]

        assert item["PK"] == "PROJECT#proj-1"
        assert item["SK"].startswith("EVENT#")
        assert item["event_type"] == "agent_active"
        assert item["agent_name"] == "pm"
        assert item["phase"] == "DISCOVERY"
        assert item["detail"] == "Agent pm started working"
        assert "ttl" in item
        assert "event_id" in result
        assert "timestamp" in result

    @patch("src.state.activity._get_table")
    def test_returns_event_id_and_timestamp(self, mock_get_table: MagicMock) -> None:
        mock_get_table.return_value = MagicMock()

        result = store_activity_event(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="handoff",
            agent_name="sa",
            phase="DISCOVERY",
        )

        assert isinstance(result["event_id"], str)
        assert len(result["event_id"]) > 0
        assert isinstance(result["timestamp"], str)

    @patch("src.state.activity._get_table")
    def test_ttl_is_approximately_24h_from_now(self, mock_get_table: MagicMock) -> None:
        import time

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        store_activity_event(
            table_name="cloudcrew-activity",
            project_id="proj-1",
            event_type="agent_idle",
            agent_name="pm",
            phase="DISCOVERY",
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        ttl = item["ttl"]
        now = int(time.time())
        # TTL should be between 23h and 25h from now
        assert now + 82800 < ttl < now + 90000


@pytest.mark.unit
class TestGetRecentActivity:
    """Verify querying recent activity events."""

    @patch("src.state.activity._get_table")
    def test_returns_formatted_events(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {
                    "event_id": "evt-1",
                    "event_type": "agent_active",
                    "agent_name": "pm",
                    "phase": "DISCOVERY",
                    "detail": "Agent pm started",
                    "timestamp": "2026-01-01T00:00:00",
                },
            ],
        }
        mock_get_table.return_value = mock_table

        events = get_recent_activity("cloudcrew-activity", "proj-1")

        assert len(events) == 1
        assert events[0]["event_id"] == "evt-1"
        assert events[0]["event_type"] == "agent_active"
        assert events[0]["agent_name"] == "pm"

    @patch("src.state.activity._get_table")
    def test_returns_empty_list_when_no_events(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_get_table.return_value = mock_table

        events = get_recent_activity("cloudcrew-activity", "proj-1")

        assert events == []

    @patch("src.state.activity._get_table")
    def test_passes_limit_to_query(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_get_table.return_value = mock_table

        get_recent_activity("cloudcrew-activity", "proj-1", limit=10)

        query_kwargs = mock_table.query.call_args.kwargs
        assert query_kwargs["Limit"] == 10
        assert query_kwargs["ScanIndexForward"] is False
