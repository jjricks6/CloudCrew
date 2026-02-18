"""Tests for src/tools/ledger_tools.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.models import TaskLedger


@pytest.mark.unit
class TestReadTaskLedger:
    """Verify read_task_ledger tool."""

    @patch("src.tools.ledger_tools.format_ledger")
    @patch("src.tools.ledger_tools.read_ledger")
    def test_reads_successfully(self, mock_read: MagicMock, mock_format: MagicMock) -> None:
        from src.tools.ledger_tools import read_task_ledger

        mock_read.return_value = TaskLedger(project_id="proj-001")
        mock_format.return_value = "# Task Ledger: proj-001"
        mock_context = MagicMock()
        mock_context.invocation_state = {"project_id": "proj-001", "task_ledger_table": "test-table"}

        result = read_task_ledger(mock_context)

        assert "Task Ledger" in result
        mock_read.assert_called_once_with("test-table", "proj-001")

    def test_missing_project_id(self) -> None:
        from src.tools.ledger_tools import read_task_ledger

        mock_context = MagicMock()
        mock_context.invocation_state = {"task_ledger_table": "test-table"}

        result = read_task_ledger(mock_context)

        assert "Error" in result

    def test_missing_table_name(self) -> None:
        from src.tools.ledger_tools import read_task_ledger

        mock_context = MagicMock()
        mock_context.invocation_state = {"project_id": "proj-001"}

        result = read_task_ledger(mock_context)

        assert "Error" in result


@pytest.mark.unit
class TestUpdateTaskLedger:
    """Verify update_task_ledger tool."""

    @patch("src.tools.ledger_tools.append_to_section")
    def test_appends_fact(self, mock_append: MagicMock) -> None:
        from src.tools.ledger_tools import update_task_ledger

        mock_context = MagicMock()
        mock_context.invocation_state = {"project_id": "proj-001", "task_ledger_table": "test-table"}

        result = update_task_ledger(
            "facts",
            '{"description": "New fact", "source": "test", "timestamp": "2026-01-01"}',
            mock_context,
        )

        assert "Added entry to facts" in result
        mock_append.assert_called_once()

    def test_invalid_section(self) -> None:
        from src.tools.ledger_tools import update_task_ledger

        mock_context = MagicMock()
        mock_context.invocation_state = {"project_id": "proj-001", "task_ledger_table": "test-table"}

        result = update_task_ledger("invalid_section", "{}", mock_context)

        assert "Error" in result
        assert "Invalid section" in result

    def test_invalid_json(self) -> None:
        from src.tools.ledger_tools import update_task_ledger

        mock_context = MagicMock()
        mock_context.invocation_state = {"project_id": "proj-001", "task_ledger_table": "test-table"}

        result = update_task_ledger("facts", "not valid json", mock_context)

        assert "Error" in result
        assert "Invalid JSON" in result

    @patch("src.tools.ledger_tools.update_deliverables")
    def test_updates_deliverables(self, mock_update: MagicMock) -> None:
        from src.tools.ledger_tools import update_task_ledger

        mock_context = MagicMock()
        mock_context.invocation_state = {"project_id": "proj-001", "task_ledger_table": "test-table"}

        result = update_task_ledger(
            "deliverables",
            '{"phase": "DISCOVERY", "items": [{"name": "Plan", "git_path": "docs/plan.md", "status": "COMPLETE"}]}',
            mock_context,
        )

        assert "Updated deliverables" in result
        mock_update.assert_called_once()

    def test_deliverables_missing_phase(self) -> None:
        from src.tools.ledger_tools import update_task_ledger

        mock_context = MagicMock()
        mock_context.invocation_state = {"project_id": "proj-001", "task_ledger_table": "test-table"}

        result = update_task_ledger("deliverables", '{"items": []}', mock_context)

        assert "Error" in result
        assert "phase" in result
