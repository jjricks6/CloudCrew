"""Tests for src/phases/__main__.py."""

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
class TestExecutePhase:
    """Verify execute_phase orchestration."""

    @patch("src.phases.__main__._send_task_success")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    def test_happy_path_completes(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        mock_send_success: MagicMock,
    ) -> None:
        from src.phases.__main__ import execute_phase
        from strands.multiagent.base import Status

        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED

        mock_swarm = MagicMock(return_value=mock_result)
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}

        execute_phase("p1", "DISCOVERY", "token-123")

        mock_send_success.assert_called_once()
        call_args = mock_send_success.call_args[0]
        assert call_args[0] == "token-123"
        assert call_args[1]["status"] == "COMPLETED"

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
    ) -> None:
        from src.phases.__main__ import execute_phase

        mock_swarm = MagicMock(side_effect=RuntimeError("boom"))
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}

        execute_phase("p1", "DISCOVERY", "token-123")

        mock_send_failure.assert_called_once()
        call_args = mock_send_failure.call_args[0]
        assert call_args[0] == "token-123"
        assert call_args[1] == "PhaseExecutionFailed"

    @patch("src.phases.__main__._send_task_success")
    @patch("src.phases.__main__._build_invocation_state")
    @patch("src.phases.__main__.get_swarm_factory")
    def test_customer_feedback_included_in_task(
        self,
        mock_get_factory: MagicMock,
        mock_build_state: MagicMock,
        _mock_send_success: MagicMock,
    ) -> None:
        from src.phases.__main__ import execute_phase
        from strands.multiagent.base import Status

        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED

        mock_swarm = MagicMock(return_value=mock_result)
        mock_get_factory.return_value = MagicMock(return_value=mock_swarm)
        mock_build_state.return_value = {"project_id": "p1"}

        execute_phase("p1", "DISCOVERY", "token-123", customer_feedback="Needs more detail")

        task_arg = mock_swarm.call_args[0][0]
        assert "Needs more detail" in task_arg


@pytest.mark.unit
class TestExtractInterrupts:
    """Verify interrupt extraction from SwarmResult."""

    def test_no_interrupts(self) -> None:
        from src.phases.__main__ import _extract_interrupts

        mock_result = MagicMock(spec=[])
        assert _extract_interrupts(mock_result) == []

    def test_with_interrupt_data(self) -> None:
        from src.phases.__main__ import _extract_interrupts

        mock_interrupt = MagicMock()
        mock_interrupt.query = "What color?"
        mock_result = MagicMock()
        mock_result.interrupts = [mock_interrupt]

        result = _extract_interrupts(mock_result)
        assert result == ["What color?"]


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
    @patch.dict("os.environ", {"PROJECT_ID": "p1", "PHASE": "DISCOVERY", "TASK_TOKEN": "tok"})
    def test_main_calls_execute_phase(self, mock_execute: MagicMock) -> None:
        from src.phases.__main__ import main

        main()
        mock_execute.assert_called_once_with("p1", "DISCOVERY", "tok", "")

    @patch("sys.exit", side_effect=SystemExit(1))
    @patch.dict("os.environ", {"PROJECT_ID": "", "PHASE": "", "TASK_TOKEN": ""})
    def test_main_exits_on_missing_env(self, mock_exit: MagicMock) -> None:
        from src.phases.__main__ import main

        with pytest.raises(SystemExit):
            main()
        mock_exit.assert_called_once_with(1)
