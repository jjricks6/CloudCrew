"""Tests for src/phases/__main__.py."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestGetSwarmFactory:
    """Verify get_swarm_factory resolution."""

    def test_valid_phases(self) -> None:
        from src.phases.__main__ import get_swarm_factory

        for phase in ["DISCOVERY", "ARCHITECTURE", "POC", "PRODUCTION", "HANDOFF"]:
            factory = get_swarm_factory(phase)
            assert callable(factory)

    def test_case_insensitive(self) -> None:
        from src.phases.__main__ import get_swarm_factory

        factory = get_swarm_factory("discovery")
        assert callable(factory)

    def test_unknown_phase_raises(self) -> None:
        from src.phases.__main__ import get_swarm_factory

        with pytest.raises(ValueError, match="Unknown phase"):
            get_swarm_factory("NONEXISTENT")


@pytest.mark.unit
class TestTempGitRepo:
    """Verify temp git repo creation when PROJECT_REPO_PATH is unset."""

    @patch("src.phases.__main__._generate_phase_summary_with_retry")
    @patch("src.phases.__main__._send_task_success")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    @patch("src.phases.__main__.PROJECT_REPO_PATH", "")
    def test_creates_temp_repo_when_path_empty(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        _mock_send_success: MagicMock,
        _mock_summary: MagicMock,
    ) -> None:
        from src.phases.__main__ import execute_phase
        from strands.multiagent.base import Status

        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED

        mock_swarm = MagicMock(return_value=mock_result)
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}

        original_path = os.environ.get("PROJECT_REPO_PATH", "")
        try:
            os.environ.pop("PROJECT_REPO_PATH", None)
            execute_phase("p1", "ARCHITECTURE", "token-123")

            # Verify a temp repo was created and set in env
            repo_path = os.environ.get("PROJECT_REPO_PATH", "")
            assert repo_path != ""
            assert Path(repo_path).exists()
            assert (Path(repo_path) / ".git").exists()
        finally:
            # Restore original env
            if original_path:
                os.environ["PROJECT_REPO_PATH"] = original_path
            else:
                os.environ.pop("PROJECT_REPO_PATH", None)


@pytest.mark.unit
class TestExecutePhase:
    """Verify execute_phase orchestration."""

    @patch("src.phases.__main__.PROJECT_REPO_PATH", "/tmp/fake-repo")
    @patch("src.phases.__main__._generate_phase_summary_with_retry")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.__main__._send_task_success")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    def test_happy_path_completes(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        mock_send_success: MagicMock,
        mock_read_ledger: MagicMock,
        _mock_summary: MagicMock,
    ) -> None:
        from src.phases.__main__ import execute_phase
        from src.state.models import TaskLedger
        from strands.multiagent.base import Status

        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED

        mock_swarm = MagicMock(return_value=mock_result)
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}
        mock_read_ledger.return_value = TaskLedger(project_id="p1")

        # Use ARCHITECTURE (not DISCOVERY) to avoid Discovery SOW validation
        execute_phase("p1", "ARCHITECTURE", "token-123")

        mock_send_success.assert_called_once()
        call_args = mock_send_success.call_args[0]
        assert call_args[0] == "token-123"
        assert call_args[1]["status"] == "COMPLETED"

    @patch("src.phases.__main__.PROJECT_REPO_PATH", "/tmp/fake-repo")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.__main__._send_task_failure")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    @patch("src.phases.__main__.PHASE_MAX_RETRIES", 0)
    @patch("src.phases.__main__.PHASE_RETRY_DELAY", 0)
    def test_failure_sends_task_failure(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        mock_send_failure: MagicMock,
        mock_read_ledger: MagicMock,
    ) -> None:
        from src.phases.__main__ import execute_phase
        from src.state.models import TaskLedger

        mock_swarm = MagicMock(side_effect=RuntimeError("boom"))
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}
        mock_read_ledger.return_value = TaskLedger(project_id="p1")

        # Use ARCHITECTURE to avoid Discovery SOW validation
        execute_phase("p1", "ARCHITECTURE", "token-123")

        mock_send_failure.assert_called_once()
        call_args = mock_send_failure.call_args[0]
        assert call_args[0] == "token-123"
        assert call_args[1] == "PhaseExecutionFailed"

    @patch("src.phases.__main__.PROJECT_REPO_PATH", "/tmp/fake-repo")
    @patch("src.phases.__main__._generate_phase_summary_with_retry")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.__main__._send_task_success")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    def test_customer_feedback_included_in_task(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        _mock_send_success: MagicMock,
        mock_read_ledger: MagicMock,
        _mock_summary: MagicMock,
    ) -> None:
        from src.phases.__main__ import execute_phase
        from src.state.models import TaskLedger
        from strands.multiagent.base import Status

        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED

        mock_swarm = MagicMock(return_value=mock_result)
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}
        mock_read_ledger.return_value = TaskLedger(project_id="p1")

        # Use ARCHITECTURE to avoid Discovery SOW validation
        execute_phase("p1", "ARCHITECTURE", "token-123", customer_feedback="Needs more detail")

        task_arg = mock_swarm.call_args[0][0]
        assert "Needs more detail" in task_arg


@pytest.mark.unit
class TestDiscoverySowValidation:
    """Verify _discovery_sow_validated gate."""

    @patch("src.state.ledger.read_ledger")
    def test_returns_true_when_facts_exist(self, mock_read: MagicMock) -> None:
        from src.phases.__main__ import _discovery_sow_validated
        from src.state.models import Fact, TaskLedger

        mock_read.return_value = TaskLedger(
            project_id="p1",
            facts=[Fact(description="SOW approved", source="pm", timestamp="2026-01-01T00:00:00")],
        )

        assert _discovery_sow_validated("p1") is True

    @patch("src.state.ledger.read_ledger")
    def test_returns_false_when_no_facts(self, mock_read: MagicMock) -> None:
        from src.phases.__main__ import _discovery_sow_validated
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", facts=[])

        assert _discovery_sow_validated("p1") is False

    @patch("src.phases.__main__.PROJECT_REPO_PATH", "/tmp/fake-repo")
    @patch("src.phases.__main__._generate_phase_summary_with_retry")
    @patch("src.phases.__main__._discovery_sow_validated")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.__main__._send_task_success")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    def test_discovery_completes_when_sow_validated(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        mock_send_success: MagicMock,
        mock_read_ledger: MagicMock,
        mock_validated: MagicMock,
        _mock_summary: MagicMock,
    ) -> None:
        """Discovery reports success when SOW validation passes."""
        from src.phases.__main__ import execute_phase
        from src.state.models import TaskLedger
        from strands.multiagent.base import Status

        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED
        mock_swarm = MagicMock(return_value=mock_result)
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}
        mock_read_ledger.return_value = TaskLedger(project_id="p1")
        mock_validated.return_value = True

        execute_phase("p1", "DISCOVERY", "token-123")

        mock_send_success.assert_called_once()

    @patch("src.phases.__main__.PROJECT_REPO_PATH", "/tmp/fake-repo")
    @patch("src.phases.__main__._discovery_sow_validated")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.__main__._send_task_failure")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    @patch("src.phases.__main__.PHASE_MAX_RETRIES", 0)
    @patch("src.phases.__main__.PHASE_RETRY_DELAY", 0)
    def test_discovery_retries_when_sow_not_validated(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        mock_send_failure: MagicMock,
        mock_read_ledger: MagicMock,
        mock_validated: MagicMock,
    ) -> None:
        """Discovery triggers recovery when SOW validation fails."""
        from src.phases.__main__ import execute_phase
        from src.state.models import TaskLedger
        from strands.multiagent.base import Status

        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED
        mock_swarm = MagicMock(return_value=mock_result)
        mock_factory = MagicMock(return_value=mock_swarm)
        mock_get_factory.return_value = mock_factory
        mock_build_state.return_value = {"project_id": "p1"}
        mock_read_ledger.return_value = TaskLedger(project_id="p1")
        # SOW never validated — recovery is attempted but also completes
        # without validation, eventually exhausting retries
        mock_validated.return_value = False

        execute_phase("p1", "DISCOVERY", "token-123")

        # The factory should be called multiple times (initial + recovery)
        assert mock_factory.call_count >= 2
        # Eventually fails because SOW validation never passes
        mock_send_failure.assert_called_once()


@pytest.mark.unit
class TestSendTaskSuccess:
    """Verify _send_task_success."""

    @patch("src.phases.__main__.boto3")
    def test_sends_success(self, mock_boto3: MagicMock) -> None:
        from src.phases.__main__ import _send_task_success

        mock_sfn = MagicMock()
        mock_boto3.client.return_value = mock_sfn

        _send_task_success("token-abc", {"status": "COMPLETED"})

        mock_sfn.send_task_success.assert_called_once()
        call_kwargs = mock_sfn.send_task_success.call_args.kwargs
        assert call_kwargs["taskToken"] == "token-abc"


@pytest.mark.unit
class TestSendTaskFailure:
    """Verify _send_task_failure."""

    @patch("src.phases.__main__.boto3")
    def test_sends_failure(self, mock_boto3: MagicMock) -> None:
        from src.phases.__main__ import _send_task_failure

        mock_sfn = MagicMock()
        mock_boto3.client.return_value = mock_sfn

        _send_task_failure("token-abc", "Error", "Something broke")

        mock_sfn.send_task_failure.assert_called_once()
        call_kwargs = mock_sfn.send_task_failure.call_args.kwargs
        assert call_kwargs["taskToken"] == "token-abc"
        assert call_kwargs["error"] == "Error"


@pytest.mark.unit
class TestPollForInterruptResponses:
    """Verify _poll_for_interrupt_responses."""

    @patch("src.phases.__main__.INTERRUPT_POLL_INTERVAL", 0)
    @patch("src.phases.__main__.INTERRUPT_POLL_TIMEOUT", 1.0)
    @patch("src.phases.__main__.get_interrupt_response")
    def test_polls_until_all_answered(self, mock_get: MagicMock) -> None:
        from src.phases.__main__ import _poll_for_interrupt_responses

        # First call: no response. Second call: response available.
        mock_get.side_effect = ["", "Blue"]

        result = _poll_for_interrupt_responses("proj-1", ["int-001"])
        assert result == {"int-001": "Blue"}

    @patch("src.phases.__main__.INTERRUPT_POLL_INTERVAL", 0)
    @patch("src.phases.__main__.INTERRUPT_POLL_TIMEOUT", 0.01)
    @patch("src.phases.__main__.get_interrupt_response")
    def test_timeout_raises(self, mock_get: MagicMock) -> None:
        from src.phases.__main__ import _poll_for_interrupt_responses

        mock_get.return_value = ""  # Never answers

        with pytest.raises(TimeoutError, match="timed out"):
            _poll_for_interrupt_responses("proj-1", ["int-001"])


@pytest.mark.unit
class TestMain:
    """Verify main() entry point."""

    @patch("src.phases.__main__.execute_phase")
    @patch("src.phases.__main__.ECS_PROJECT_ID", "p1")
    @patch("src.phases.__main__.ECS_PHASE", "DISCOVERY")
    @patch("src.phases.__main__.ECS_TASK_TOKEN", "tok")
    @patch("src.phases.__main__.ECS_CUSTOMER_FEEDBACK", "")
    def test_main_calls_execute_phase(self, mock_execute: MagicMock) -> None:
        from src.phases.__main__ import main

        main()
        mock_execute.assert_called_once_with("p1", "DISCOVERY", "tok", "")

    @patch("sys.exit", side_effect=SystemExit(1))
    @patch("src.phases.__main__.ECS_PROJECT_ID", "")
    @patch("src.phases.__main__.ECS_PHASE", "")
    @patch("src.phases.__main__.ECS_TASK_TOKEN", "")
    def test_main_exits_on_missing_env(self, mock_exit: MagicMock) -> None:
        from src.phases.__main__ import main

        with pytest.raises(SystemExit):
            main()
        mock_exit.assert_called_once_with(1)
