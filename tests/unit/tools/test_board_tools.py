"""Tests for src/tools/board_tools.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestCreateBoardTask:
    """Verify create_board_task tool."""

    @patch("src.tools.board_tools.create_task")
    def test_creates_task_successfully(self, mock_create: MagicMock) -> None:
        from src.tools.board_tools import create_board_task

        mock_create.return_value = {"task_id": "t-001"}
        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "ARCHITECTURE",
        }

        result = create_board_task("Design VPC", "Create VPC module", "infra", mock_context)

        assert "t-001" in result
        assert "Design VPC" in result
        mock_create.assert_called_once_with(
            table_name="test-table",
            project_id="proj-001",
            title="Design VPC",
            description="Create VPC module",
            phase="ARCHITECTURE",
            assigned_to="infra",
        )

    def test_missing_project_id(self) -> None:
        from src.tools.board_tools import create_board_task

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = create_board_task("title", "desc", "pm", mock_context)

        assert "Error" in result
        assert "project_id" in result

    def test_missing_board_tasks_table(self) -> None:
        from src.tools.board_tools import create_board_task

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "phase": "DISCOVERY",
        }

        result = create_board_task("title", "desc", "pm", mock_context)

        assert "Error" in result
        assert "board_tasks_table" in result

    @patch("src.tools.board_tools.create_task")
    def test_handles_exception(self, mock_create: MagicMock) -> None:
        from src.tools.board_tools import create_board_task

        mock_create.side_effect = RuntimeError("DynamoDB error")
        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = create_board_task("title", "desc", "pm", mock_context)

        assert "Error creating task" in result


@pytest.mark.unit
class TestUpdateBoardTask:
    """Verify update_board_task tool."""

    @patch("src.tools.board_tools.update_task")
    def test_updates_task_successfully(self, mock_update: MagicMock) -> None:
        from src.tools.board_tools import update_board_task

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "ARCHITECTURE",
        }

        result = update_board_task("t-001", '{"status": "in_progress"}', mock_context)

        assert "Updated task t-001" in result
        mock_update.assert_called_once_with(
            table_name="test-table",
            project_id="proj-001",
            phase="ARCHITECTURE",
            task_id="t-001",
            updates={"status": "in_progress"},
        )

    def test_missing_project_id(self) -> None:
        from src.tools.board_tools import update_board_task

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = update_board_task("t-001", '{"status": "done"}', mock_context)

        assert "Error" in result

    def test_invalid_json(self) -> None:
        from src.tools.board_tools import update_board_task

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = update_board_task("t-001", "not valid json", mock_context)

        assert "Error" in result
        assert "Invalid JSON" in result

    def test_rejects_invalid_keys(self) -> None:
        from src.tools.board_tools import update_board_task

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = update_board_task("t-001", '{"bad_field": "value"}', mock_context)

        assert "Error" in result
        assert "Invalid update fields" in result

    def test_rejects_invalid_status(self) -> None:
        from src.tools.board_tools import update_board_task

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = update_board_task("t-001", '{"status": "invalid"}', mock_context)

        assert "Error" in result
        assert "Invalid status" in result

    @patch("src.tools.board_tools.update_task")
    def test_handles_exception(self, mock_update: MagicMock) -> None:
        from src.tools.board_tools import update_board_task

        mock_update.side_effect = RuntimeError("DynamoDB error")
        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = update_board_task("t-001", '{"status": "done"}', mock_context)

        assert "Error updating task" in result


@pytest.mark.unit
class TestAddTaskComment:
    """Verify add_task_comment tool."""

    @patch("src.tools.board_tools.add_comment")
    def test_adds_comment_successfully(self, mock_add: MagicMock) -> None:
        from src.tools.board_tools import add_task_comment

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "ARCHITECTURE",
        }

        result = add_task_comment("t-001", "sa", "Completed review.", mock_context)

        assert "Added comment to task t-001" in result
        mock_add.assert_called_once_with(
            table_name="test-table",
            project_id="proj-001",
            phase="ARCHITECTURE",
            task_id="t-001",
            author="sa",
            content="Completed review.",
        )

    def test_missing_project_id(self) -> None:
        from src.tools.board_tools import add_task_comment

        mock_context = MagicMock()
        mock_context.invocation_state = {
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = add_task_comment("t-001", "pm", "note", mock_context)

        assert "Error" in result

    @patch("src.tools.board_tools.add_comment")
    def test_handles_exception(self, mock_add: MagicMock) -> None:
        from src.tools.board_tools import add_task_comment

        mock_add.side_effect = RuntimeError("DynamoDB error")
        mock_context = MagicMock()
        mock_context.invocation_state = {
            "project_id": "proj-001",
            "board_tasks_table": "test-table",
            "phase": "DISCOVERY",
        }

        result = add_task_comment("t-001", "pm", "note", mock_context)

        assert "Error adding comment" in result
