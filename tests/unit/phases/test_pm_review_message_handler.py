"""Tests for src/phases/pm_review_message_handler.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.models import TaskLedger


@pytest.mark.unit
class TestFetchPhaseSummary:
    """Verify _fetch_phase_summary S3 integration."""

    @patch("src.phases.pm_review_message_handler.SOW_BUCKET", "my-bucket")
    @patch("src.phases.pm_review_message_handler.boto3")
    def test_fetches_summary_from_s3(self, mock_boto3: MagicMock) -> None:
        from src.phases.pm_review_message_handler import _fetch_phase_summary

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_body = MagicMock()
        mock_body.read.return_value = b"# Architecture Summary\nAll good."
        mock_s3.get_object.return_value = {"Body": mock_body}

        result = _fetch_phase_summary("proj-1", "ARCHITECTURE")

        assert result == "# Architecture Summary\nAll good."
        mock_s3.get_object.assert_called_once_with(
            Bucket="my-bucket",
            Key="projects/proj-1/artifacts/docs/phase-summaries/architecture.md",
        )

    @patch("src.phases.pm_review_message_handler.SOW_BUCKET", "")
    def test_returns_empty_when_bucket_not_configured(self) -> None:
        from src.phases.pm_review_message_handler import _fetch_phase_summary

        result = _fetch_phase_summary("proj-1", "ARCHITECTURE")
        assert result == ""

    @patch("src.phases.pm_review_message_handler.SOW_BUCKET", "my-bucket")
    @patch("src.phases.pm_review_message_handler.boto3")
    def test_returns_empty_on_no_such_key(self, mock_boto3: MagicMock) -> None:
        from botocore.exceptions import ClientError
        from src.phases.pm_review_message_handler import _fetch_phase_summary

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        result = _fetch_phase_summary("proj-1", "POC")
        assert result == ""

    @patch("src.phases.pm_review_message_handler.SOW_BUCKET", "my-bucket")
    @patch("src.phases.pm_review_message_handler.boto3")
    def test_returns_empty_on_other_s3_error(self, mock_boto3: MagicMock) -> None:
        from botocore.exceptions import ClientError
        from src.phases.pm_review_message_handler import _fetch_phase_summary

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Forbidden"}},
            "GetObject",
        )

        result = _fetch_phase_summary("proj-1", "POC")
        assert result == ""


@pytest.mark.unit
class TestPersistReviewMessage:
    """Verify _persist_review_message ledger writes."""

    @patch("src.phases.pm_review_message_handler.write_ledger")
    @patch("src.phases.pm_review_message_handler.read_ledger")
    def test_persists_opening_message(
        self,
        mock_read: MagicMock,
        mock_write: MagicMock,
    ) -> None:
        from src.phases.pm_review_message_handler import _persist_review_message

        ledger = TaskLedger(project_id="proj-1")
        mock_read.return_value = ledger

        _persist_review_message("proj-1", "opening", "Welcome to the review!")

        assert ledger.review_opening_message == "Welcome to the review!"
        mock_write.assert_called_once()

    @patch("src.phases.pm_review_message_handler.write_ledger")
    @patch("src.phases.pm_review_message_handler.read_ledger")
    def test_persists_closing_message(
        self,
        mock_read: MagicMock,
        mock_write: MagicMock,
    ) -> None:
        from src.phases.pm_review_message_handler import _persist_review_message

        ledger = TaskLedger(project_id="proj-1")
        mock_read.return_value = ledger

        _persist_review_message("proj-1", "closing", "Thank you!")

        assert ledger.review_closing_message == "Thank you!"
        mock_write.assert_called_once()

    @patch("src.phases.pm_review_message_handler.write_ledger")
    @patch("src.phases.pm_review_message_handler.read_ledger")
    def test_handles_write_failure_gracefully(
        self,
        mock_read: MagicMock,
        mock_write: MagicMock,
    ) -> None:
        from src.phases.pm_review_message_handler import _persist_review_message

        mock_read.return_value = TaskLedger(project_id="proj-1")
        mock_write.side_effect = RuntimeError("DynamoDB error")

        # Should not raise — logs and returns
        _persist_review_message("proj-1", "opening", "Welcome!")


@pytest.mark.unit
class TestPMReviewMessageHandler:
    """Verify PM review message generation end-to-end."""

    @patch("src.phases.pm_review_message_handler.write_ledger")
    @patch("src.phases.pm_review_message_handler._fetch_phase_summary")
    @patch("src.phases.pm_review_message_handler.create_pm_agent")
    @patch("src.phases.pm_review_message_handler.read_ledger")
    @patch("src.phases.pm_review_message_handler.broadcast_to_project")
    def test_handler_generates_opening_message(
        self,
        _mock_broadcast: MagicMock,
        mock_read_ledger: MagicMock,
        mock_create_pm_agent: MagicMock,
        mock_fetch_summary: MagicMock,
        mock_write_ledger: MagicMock,
    ) -> None:
        """Test opening message generation with S3 summary and ledger persistence."""
        from src.phases.pm_review_message_handler import handler

        mock_pm = MagicMock()
        mock_pm.return_value = "Welcome to the review!"
        mock_create_pm_agent.return_value = mock_pm
        mock_read_ledger.return_value = TaskLedger(project_id="p1")
        mock_fetch_summary.return_value = "# Architecture complete"

        result = handler(
            {"project_id": "p1", "phase": "ARCHITECTURE", "message_type": "opening"},
            None,
        )

        assert result["status"] == "success"
        assert result["message_type"] == "opening"
        mock_create_pm_agent.assert_called_once()
        mock_fetch_summary.assert_called_once_with("p1", "ARCHITECTURE")

        # Verify the prompt included phase summary (via the PM agent call)
        pm_call_args = mock_pm.call_args[0][0]
        assert "Architecture complete" in pm_call_args

        # Verify ledger persistence
        mock_write_ledger.assert_called_once()

    @patch("src.phases.pm_review_message_handler.write_ledger")
    @patch("src.phases.pm_review_message_handler._fetch_phase_summary")
    @patch("src.phases.pm_review_message_handler.create_pm_agent")
    @patch("src.phases.pm_review_message_handler.read_ledger")
    @patch("src.phases.pm_review_message_handler.broadcast_to_project")
    def test_handler_generates_closing_message(
        self,
        _mock_broadcast: MagicMock,
        mock_read_ledger: MagicMock,
        mock_create_pm_agent: MagicMock,
        mock_fetch_summary: MagicMock,
        mock_write_ledger: MagicMock,
    ) -> None:
        """Test closing message generation."""
        from src.phases.pm_review_message_handler import handler

        mock_pm = MagicMock()
        mock_pm.return_value = "Thank you for approving!"
        mock_create_pm_agent.return_value = mock_pm
        mock_read_ledger.return_value = TaskLedger(project_id="p1")
        mock_fetch_summary.return_value = ""

        result = handler(
            {"project_id": "p1", "phase": "ARCHITECTURE", "message_type": "closing"},
            None,
        )

        assert result["status"] == "success"
        assert result["message_type"] == "closing"
        mock_write_ledger.assert_called_once()

    @patch("src.phases.pm_review_message_handler.write_ledger")
    @patch("src.phases.pm_review_message_handler._fetch_phase_summary")
    @patch("src.phases.pm_review_message_handler.create_pm_agent")
    @patch("src.phases.pm_review_message_handler.read_ledger")
    @patch("src.phases.pm_review_message_handler.broadcast_to_project")
    def test_handler_handles_pm_exception(
        self,
        mock_broadcast: MagicMock,
        mock_read_ledger: MagicMock,
        mock_create_pm_agent: MagicMock,
        mock_fetch_summary: MagicMock,
        mock_write_ledger: MagicMock,
    ) -> None:
        """Test error handling when PM agent fails — still persists error message."""
        from src.phases.pm_review_message_handler import handler

        mock_pm = MagicMock()
        mock_pm.side_effect = RuntimeError("PM agent error")
        mock_create_pm_agent.return_value = mock_pm
        mock_read_ledger.return_value = TaskLedger(project_id="p1")
        mock_fetch_summary.return_value = "Summary text"

        result = handler(
            {"project_id": "p1", "phase": "ARCHITECTURE", "message_type": "opening"},
            None,
        )

        # Handler doesn't crash — broadcasts error + persists it
        assert result["status"] == "success"
        mock_broadcast.assert_called()
        mock_write_ledger.assert_called_once()

    @patch("src.phases.pm_review_message_handler.write_ledger")
    @patch("src.phases.pm_review_message_handler._fetch_phase_summary")
    @patch("src.phases.pm_review_message_handler.create_pm_agent")
    @patch("src.phases.pm_review_message_handler.read_ledger")
    @patch("src.phases.pm_review_message_handler.broadcast_to_project")
    def test_handler_works_without_phase_summary(
        self,
        _mock_broadcast: MagicMock,
        mock_read_ledger: MagicMock,
        mock_create_pm_agent: MagicMock,
        mock_fetch_summary: MagicMock,
        mock_write_ledger: MagicMock,
    ) -> None:
        """Test handler works gracefully when phase summary is missing."""
        from src.phases.pm_review_message_handler import handler

        mock_pm = MagicMock()
        mock_pm.return_value = "Welcome!"
        mock_create_pm_agent.return_value = mock_pm
        mock_read_ledger.return_value = TaskLedger(project_id="p1")
        mock_fetch_summary.return_value = ""  # No summary available

        result = handler(
            {"project_id": "p1", "phase": "ARCHITECTURE", "message_type": "opening"},
            None,
        )

        assert result["status"] == "success"
        pm_call_args = mock_pm.call_args[0][0]
        assert "Phase summary not yet available" in pm_call_args
        mock_write_ledger.assert_called_once()
