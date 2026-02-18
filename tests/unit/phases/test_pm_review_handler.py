"""Tests for src/phases/pm_review_handler.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.models import TaskLedger


@pytest.mark.unit
class TestPMReviewHandler:
    """Verify PM review handler behavior."""

    @patch("src.phases.pm_review_handler.read_ledger")
    @patch("src.phases.pm_review_handler.create_pm_agent")
    @patch("src.phases.pm_review_handler.build_invocation_state")
    def test_handler_invokes_pm_agent(
        self,
        mock_build_state: MagicMock,
        mock_create_pm: MagicMock,
        mock_read_ledger: MagicMock,
    ) -> None:
        from src.phases.pm_review_handler import handler

        mock_ledger = TaskLedger(project_id="proj-1", project_name="Test")
        mock_read_ledger.return_value = mock_ledger
        mock_build_state.return_value = {"project_id": "proj-1"}

        mock_pm = MagicMock()
        mock_pm.return_value = "REVIEW: PASSED — all deliverables meet criteria"
        mock_create_pm.return_value = mock_pm

        event = {"project_id": "proj-1", "phase": "DISCOVERY", "phase_result": {}}

        result = handler(event, None)

        mock_create_pm.assert_called_once()
        mock_pm.assert_called_once()
        assert result["project_id"] == "proj-1"
        assert result["phase"] == "DISCOVERY"
        assert result["review_passed"] is True

    @patch("src.phases.pm_review_handler.read_ledger")
    @patch("src.phases.pm_review_handler.create_pm_agent")
    @patch("src.phases.pm_review_handler.build_invocation_state")
    def test_handler_detects_failed_review(
        self,
        mock_build_state: MagicMock,
        mock_create_pm: MagicMock,
        mock_read_ledger: MagicMock,
    ) -> None:
        from src.phases.pm_review_handler import handler

        mock_ledger = TaskLedger(project_id="proj-1")
        mock_read_ledger.return_value = mock_ledger
        mock_build_state.return_value = {"project_id": "proj-1"}

        mock_pm = MagicMock()
        mock_pm.return_value = "REVIEW: FAILED — missing security review"
        mock_create_pm.return_value = mock_pm

        event = {"project_id": "proj-1", "phase": "ARCHITECTURE", "phase_result": {}}

        result = handler(event, None)

        assert result["review_passed"] is False

    @patch("src.phases.pm_review_handler.read_ledger")
    @patch("src.phases.pm_review_handler.create_pm_agent")
    @patch("src.phases.pm_review_handler.build_invocation_state")
    def test_handler_returns_deliverable_package(
        self,
        mock_build_state: MagicMock,
        mock_create_pm: MagicMock,
        mock_read_ledger: MagicMock,
    ) -> None:
        from src.phases.pm_review_handler import handler
        from src.state.models import DeliverableItem

        mock_ledger = TaskLedger(
            project_id="proj-1",
            deliverables={
                "DISCOVERY": [
                    DeliverableItem(name="SOW Analysis", git_path="docs/sow.md", status="COMPLETE"),
                ],
            },
        )
        mock_read_ledger.return_value = mock_ledger
        mock_build_state.return_value = {"project_id": "proj-1"}

        mock_pm = MagicMock()
        mock_pm.return_value = "REVIEW: PASSED"
        mock_create_pm.return_value = mock_pm

        event = {"project_id": "proj-1", "phase": "DISCOVERY", "phase_result": {}}

        result = handler(event, None)

        assert "DISCOVERY" in result["deliverable_package"]
        assert len(result["deliverable_package"]["DISCOVERY"]) == 1
