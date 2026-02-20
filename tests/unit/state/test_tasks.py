"""Tests for src/state/tasks.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestCreateTask:
    """Verify create_task behavior."""

    @patch("src.state.tasks.broadcast_to_project")
    @patch("src.state.tasks._get_table")
    def test_creates_task(self, mock_get_table: MagicMock, mock_broadcast: MagicMock) -> None:
        from src.state.tasks import create_task

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        result = create_task(
            "test-table",
            "proj-1",
            title="Implement auth",
            description="Set up Cognito",
            phase="ARCHITECTURE",
            assigned_to="sa",
        )

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "PROJECT#proj-1"
        assert item["SK"].startswith("TASK#ARCHITECTURE#")
        assert item["title"] == "Implement auth"
        assert item["description"] == "Set up Cognito"
        assert item["status"] == "backlog"
        assert item["assigned_to"] == "sa"
        assert item["comments"] == []
        assert item["artifact_path"] == ""

        # Returns the created item with PK/SK stripped
        assert result["task_id"] == item["task_id"]
        assert result["title"] == "Implement auth"
        assert "PK" not in result
        assert "SK" not in result

        # Broadcasts task_created event
        mock_broadcast.assert_called_once()
        event = mock_broadcast.call_args[0][1]
        assert event["event"] == "task_created"
        assert event["project_id"] == "proj-1"
        assert event["phase"] == "ARCHITECTURE"
        assert event["title"] == "Implement auth"


@pytest.mark.unit
class TestUpdateTask:
    """Verify update_task behavior."""

    @patch("src.state.tasks.broadcast_to_project")
    @patch("src.state.tasks._get_table")
    def test_updates_allowed_fields(self, mock_get_table: MagicMock, mock_broadcast: MagicMock) -> None:
        from src.state.tasks import update_task

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        update_task(
            "test-table",
            "proj-1",
            "ARCHITECTURE",
            "task-001",
            {"status": "in_progress", "assigned_to": "dev"},
        )

        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args.kwargs
        assert call_kwargs["Key"]["PK"] == "PROJECT#proj-1"
        assert call_kwargs["Key"]["SK"] == "TASK#ARCHITECTURE#task-001"
        assert "SET" in call_kwargs["UpdateExpression"]

        # DynamoDB update includes updated_at
        names = call_kwargs["ExpressionAttributeNames"]
        assert "updated_at" in names.values()

        # Broadcasts task_updated event (without updated_at)
        mock_broadcast.assert_called_once()
        event = mock_broadcast.call_args[0][1]
        assert event["event"] == "task_updated"
        assert event["task_id"] == "task-001"
        assert "updated_at" not in event["updates"]
        assert event["updates"]["status"] == "in_progress"

    @patch("src.state.tasks.broadcast_to_project")
    @patch("src.state.tasks._get_table")
    def test_filters_disallowed_fields(self, mock_get_table: MagicMock, _mock_broadcast: MagicMock) -> None:
        from src.state.tasks import update_task

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        update_task(
            "test-table",
            "proj-1",
            "DISCOVERY",
            "task-001",
            {"status": "done", "PK": "evil", "task_id": "override"},
        )

        # PK and task_id are filtered out, only status passes
        call_kwargs = mock_table.update_item.call_args.kwargs
        names = call_kwargs["ExpressionAttributeNames"]
        assert "status" in names.values()
        assert "PK" not in names.values()
        assert "task_id" not in names.values()

    @patch("src.state.tasks.broadcast_to_project")
    @patch("src.state.tasks._get_table")
    def test_noop_when_no_allowed_fields(self, mock_get_table: MagicMock, mock_broadcast: MagicMock) -> None:
        from src.state.tasks import update_task

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        update_task("test-table", "proj-1", "DISCOVERY", "task-001", {"PK": "evil"})

        mock_table.update_item.assert_not_called()
        mock_broadcast.assert_not_called()


@pytest.mark.unit
class TestAddComment:
    """Verify add_comment behavior."""

    @patch("src.state.tasks.broadcast_to_project")
    @patch("src.state.tasks._get_table")
    def test_appends_comment(self, mock_get_table: MagicMock, mock_broadcast: MagicMock) -> None:
        from src.state.tasks import add_comment

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        add_comment(
            "test-table",
            "proj-1",
            "ARCHITECTURE",
            "task-001",
            author="sa",
            content="Reviewed auth options",
        )

        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args.kwargs
        assert call_kwargs["Key"]["PK"] == "PROJECT#proj-1"
        assert call_kwargs["Key"]["SK"] == "TASK#ARCHITECTURE#task-001"
        assert "list_append" in call_kwargs["UpdateExpression"]

        comment = call_kwargs["ExpressionAttributeValues"][":c"][0]
        assert comment["author"] == "sa"
        assert comment["content"] == "Reviewed auth options"

        # Broadcasts task_updated event with comment
        mock_broadcast.assert_called_once()
        event = mock_broadcast.call_args[0][1]
        assert event["event"] == "task_updated"
        assert "comment_added" in event["updates"]


@pytest.mark.unit
class TestListTasks:
    """Verify list_tasks behavior."""

    @patch("src.state.tasks._get_table")
    def test_returns_sorted_tasks(self, mock_get_table: MagicMock) -> None:
        from src.state.tasks import list_tasks

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        mock_table.query.return_value = {
            "Items": [
                {"PK": "PROJECT#proj-1", "SK": "TASK#ARCH#b", "task_id": "b", "created_at": "2025-01-02"},
                {"PK": "PROJECT#proj-1", "SK": "TASK#ARCH#a", "task_id": "a", "created_at": "2025-01-01"},
            ],
        }

        result = list_tasks("test-table", "proj-1")

        mock_table.query.assert_called_once()
        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs["ExpressionAttributeValues"][":pk"] == "PROJECT#proj-1"
        assert call_kwargs["ExpressionAttributeValues"][":prefix"] == "TASK#"

        # Sorted by created_at ascending
        assert result[0]["task_id"] == "a"
        assert result[1]["task_id"] == "b"

        # PK/SK stripped from results
        assert "PK" not in result[0]
        assert "SK" not in result[0]

    @patch("src.state.tasks._get_table")
    def test_returns_empty_list(self, mock_get_table: MagicMock) -> None:
        from src.state.tasks import list_tasks

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}

        result = list_tasks("test-table", "proj-1")
        assert result == []

    @patch("src.state.tasks._get_table")
    def test_filters_by_phase(self, mock_get_table: MagicMock) -> None:
        from src.state.tasks import list_tasks

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        mock_table.query.return_value = {"Items": []}

        list_tasks("test-table", "proj-1", phase="ARCHITECTURE")

        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs["ExpressionAttributeValues"][":prefix"] == "TASK#ARCHITECTURE#"


@pytest.mark.unit
class TestGetTask:
    """Verify get_task behavior."""

    @patch("src.state.tasks._get_table")
    def test_returns_task(self, mock_get_table: MagicMock) -> None:
        from src.state.tasks import get_task

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {"PK": "PROJECT#proj-1", "SK": "TASK#ARCH#001", "task_id": "task-001", "title": "Implement auth"},
        }

        result = get_task("test-table", "proj-1", "ARCHITECTURE", "task-001")

        assert result is not None
        assert result["task_id"] == "task-001"
        assert "PK" not in result
        assert "SK" not in result
        call_kwargs = mock_table.get_item.call_args.kwargs
        assert call_kwargs["Key"]["PK"] == "PROJECT#proj-1"
        assert call_kwargs["Key"]["SK"] == "TASK#ARCHITECTURE#task-001"

    @patch("src.state.tasks._get_table")
    def test_returns_none_when_not_found(self, mock_get_table: MagicMock) -> None:
        from src.state.tasks import get_task

        mock_table = MagicMock()
        mock_get_table.return_value = mock_table
        mock_table.get_item.return_value = {}

        result = get_task("test-table", "proj-1", "DISCOVERY", "missing")
        assert result is None
