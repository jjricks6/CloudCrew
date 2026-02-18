"""Tests for src/state/ledger.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.models import (
    Blocker,
    Decision,
    Fact,
    Phase,
    TaskLedger,
)


@pytest.mark.unit
class TestReadLedger:
    """Verify read_ledger function."""

    @patch("src.state.ledger.boto3")
    def test_returns_empty_ledger_when_not_found(self, mock_boto3: MagicMock) -> None:
        from src.state.ledger import read_ledger

        mock_table = MagicMock()
        mock_table.get_item.return_value = {}
        mock_boto3.resource.return_value.Table.return_value = mock_table

        ledger = read_ledger("test-table", "proj-001")

        assert ledger.project_id == "proj-001"
        assert ledger.facts == []
        assert ledger.decisions == []

    @patch("src.state.ledger.boto3")
    def test_returns_populated_ledger(self, mock_boto3: MagicMock) -> None:
        from src.state.ledger import read_ledger

        mock_table = MagicMock()
        mock_table.get_item.return_value = {
            "Item": {
                "data": {
                    "project_id": "proj-001",
                    "project_name": "Test Project",
                    "current_phase": "ARCHITECTURE",
                    "phase_status": "IN_PROGRESS",
                    "facts": [{"description": "AWS account ready", "source": "customer", "timestamp": "2026-01-01"}],
                },
            },
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table

        ledger = read_ledger("test-table", "proj-001")

        assert ledger.project_name == "Test Project"
        assert ledger.current_phase == Phase.ARCHITECTURE
        assert len(ledger.facts) == 1
        assert ledger.facts[0].description == "AWS account ready"


@pytest.mark.unit
class TestWriteLedger:
    """Verify write_ledger function."""

    @patch("src.state.ledger.boto3")
    def test_writes_correct_key_structure(self, mock_boto3: MagicMock) -> None:
        from src.state.ledger import write_ledger

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        ledger = TaskLedger(project_id="proj-001", project_name="Test")
        write_ledger("test-table", "proj-001", ledger)

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "PROJECT#proj-001"
        assert item["SK"] == "LEDGER"
        assert item["data"]["project_id"] == "proj-001"


@pytest.mark.unit
class TestAppendToSection:
    """Verify append_to_section function."""

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    def test_appends_fact(self, mock_read: MagicMock, mock_write: MagicMock) -> None:
        from src.state.ledger import append_to_section

        mock_read.return_value = TaskLedger(project_id="proj-001")

        entry = {"description": "New fact", "source": "test", "timestamp": "2026-01-01"}
        result = append_to_section("test-table", "proj-001", "facts", entry)

        assert len(result.facts) == 1
        assert result.facts[0].description == "New fact"
        mock_write.assert_called_once()

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    def test_appends_decision(self, mock_read: MagicMock, _mock_write: MagicMock) -> None:
        from src.state.ledger import append_to_section

        mock_read.return_value = TaskLedger(project_id="proj-001")

        entry = {
            "description": "Use S3",
            "rationale": "Cost effective",
            "made_by": "sa",
            "timestamp": "2026-01-01",
        }
        result = append_to_section("test-table", "proj-001", "decisions", entry)

        assert len(result.decisions) == 1
        assert result.decisions[0].description == "Use S3"

    def test_invalid_section_raises(self) -> None:
        from src.state.ledger import append_to_section

        with pytest.raises(ValueError, match="Invalid section"):
            append_to_section("test-table", "proj-001", "invalid", {})


@pytest.mark.unit
class TestUpdateDeliverables:
    """Verify update_deliverables function."""

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    def test_updates_phase_deliverables(self, mock_read: MagicMock, _mock_write: MagicMock) -> None:
        from src.state.ledger import update_deliverables

        mock_read.return_value = TaskLedger(project_id="proj-001")

        items = [{"name": "ADR-001", "git_path": "docs/architecture/decisions/0001.md", "status": "COMPLETE"}]
        result = update_deliverables("test-table", "proj-001", "ARCHITECTURE", items)

        assert "ARCHITECTURE" in result.deliverables
        assert len(result.deliverables["ARCHITECTURE"]) == 1
        assert result.deliverables["ARCHITECTURE"][0].name == "ADR-001"


@pytest.mark.unit
class TestFormatLedger:
    """Verify format_ledger function."""

    def test_empty_ledger(self) -> None:
        from src.state.ledger import format_ledger

        ledger = TaskLedger(project_id="proj-001")
        result = format_ledger(ledger)

        assert "proj-001" in result
        assert "No entries yet" in result

    def test_populated_ledger(self) -> None:
        from src.state.ledger import format_ledger

        ledger = TaskLedger(
            project_id="proj-001",
            project_name="Test Project",
            facts=[Fact(description="Fact 1", source="customer", timestamp="2026-01-01")],
            decisions=[Decision(description="Use S3", rationale="Cost", made_by="sa", timestamp="2026-01-01")],
            blockers=[Blocker(description="No VPN", assigned_to="infra", status="OPEN", timestamp="2026-01-01")],
        )
        result = format_ledger(ledger)

        assert "Test Project" in result
        assert "Fact 1" in result
        assert "Use S3" in result
        assert "No VPN" in result
        assert "OPEN" in result
