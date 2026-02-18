"""Tests for src/phases/runner.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.phases.runner import RECOVERY_PREFIX, PhaseResult, run_phase
from strands.multiagent.base import Status


@pytest.mark.unit
class TestRunPhaseSuccess:
    """Verify successful phase execution."""

    def test_succeeds_first_attempt(self) -> None:
        mock_result = MagicMock()
        mock_result.status = Status.COMPLETED

        mock_swarm = MagicMock()
        mock_swarm.return_value = mock_result
        factory = MagicMock(return_value=mock_swarm)

        phase_result = run_phase(factory, "do stuff", {"project_id": "p1"}, max_retries=2, retry_delay=0)

        assert phase_result.attempts == 1
        assert phase_result.result is mock_result
        assert len(phase_result.retry_history) == 1
        assert phase_result.retry_history[0]["error"] is None
        factory.assert_called_once()

    def test_factory_called_per_attempt(self) -> None:
        failed_result = MagicMock()
        failed_result.status = Status.FAILED
        success_result = MagicMock()
        success_result.status = Status.COMPLETED

        swarm1 = MagicMock(return_value=failed_result)
        swarm2 = MagicMock(return_value=success_result)
        factory = MagicMock(side_effect=[swarm1, swarm2])

        phase_result = run_phase(factory, "task", {}, max_retries=2, retry_delay=0)

        assert factory.call_count == 2
        assert phase_result.attempts == 2
        assert phase_result.result is success_result


@pytest.mark.unit
class TestRunPhaseRetry:
    """Verify retry behavior on failure."""

    def test_retries_on_exception(self) -> None:
        success_result = MagicMock()
        success_result.status = Status.COMPLETED

        failing_swarm = MagicMock(side_effect=RuntimeError("timeout"))
        success_swarm = MagicMock(return_value=success_result)
        factory = MagicMock(side_effect=[failing_swarm, success_swarm])

        phase_result = run_phase(factory, "task", {}, max_retries=2, retry_delay=0)

        assert phase_result.attempts == 2
        assert phase_result.result is success_result
        assert phase_result.retry_history[0]["error"] == "timeout"
        assert phase_result.retry_history[1]["error"] is None

    def test_retries_on_failed_status(self) -> None:
        failed_result = MagicMock()
        failed_result.status = Status.FAILED
        success_result = MagicMock()
        success_result.status = Status.COMPLETED

        swarm1 = MagicMock(return_value=failed_result)
        swarm2 = MagicMock(return_value=success_result)
        factory = MagicMock(side_effect=[swarm1, swarm2])

        phase_result = run_phase(factory, "task", {}, max_retries=2, retry_delay=0)

        assert phase_result.attempts == 2
        assert phase_result.result is success_result

    def test_recovery_prefix_prepended_on_retry(self) -> None:
        failed_result = MagicMock()
        failed_result.status = Status.FAILED
        success_result = MagicMock()
        success_result.status = Status.COMPLETED

        swarm1 = MagicMock(return_value=failed_result)
        swarm2 = MagicMock(return_value=success_result)
        factory = MagicMock(side_effect=[swarm1, swarm2])

        original_task = "do the work"
        run_phase(factory, original_task, {"p": "1"}, max_retries=1, retry_delay=0)

        # First call: original task
        first_call_task = swarm1.call_args[0][0]
        assert first_call_task == original_task

        # Second call: recovery prefix + original task
        second_call_task = swarm2.call_args[0][0]
        assert second_call_task.startswith(RECOVERY_PREFIX)
        assert original_task in second_call_task


@pytest.mark.unit
class TestRunPhaseExhausted:
    """Verify behavior when all retries exhausted."""

    def test_exhausts_retries_raises_last_exception(self) -> None:
        swarm1 = MagicMock(side_effect=RuntimeError("err1"))
        swarm2 = MagicMock(side_effect=RuntimeError("err2"))
        factory = MagicMock(side_effect=[swarm1, swarm2])

        with pytest.raises(RuntimeError, match="err2"):
            run_phase(factory, "task", {}, max_retries=1, retry_delay=0)

    def test_exhausts_retries_returns_failed_result(self) -> None:
        failed1 = MagicMock()
        failed1.status = Status.FAILED
        failed2 = MagicMock()
        failed2.status = Status.FAILED

        swarm1 = MagicMock(return_value=failed1)
        swarm2 = MagicMock(return_value=failed2)
        factory = MagicMock(side_effect=[swarm1, swarm2])

        phase_result = run_phase(factory, "task", {}, max_retries=1, retry_delay=0)

        assert phase_result.attempts == 2
        assert phase_result.result is failed2

    def test_respects_max_retries_zero(self) -> None:
        failed_result = MagicMock()
        failed_result.status = Status.FAILED

        swarm = MagicMock(return_value=failed_result)
        factory = MagicMock(return_value=swarm)

        phase_result = run_phase(factory, "task", {}, max_retries=0, retry_delay=0)

        assert phase_result.attempts == 1
        factory.assert_called_once()


@pytest.mark.unit
class TestRunPhaseRetryHistory:
    """Verify retry history tracking."""

    def test_retry_history_populated(self) -> None:
        failed_result = MagicMock()
        failed_result.status = Status.FAILED
        success_result = MagicMock()
        success_result.status = Status.COMPLETED

        swarm1 = MagicMock(return_value=failed_result)
        swarm2 = MagicMock(side_effect=RuntimeError("boom"))
        swarm3 = MagicMock(return_value=success_result)
        factory = MagicMock(side_effect=[swarm1, swarm2, swarm3])

        phase_result = run_phase(factory, "task", {}, max_retries=2, retry_delay=0)

        assert len(phase_result.retry_history) == 3
        # Attempt 1 — failed status, no error
        assert phase_result.retry_history[0]["attempt"] == 1
        assert phase_result.retry_history[0]["error"] is None
        # Attempt 2 — exception
        assert phase_result.retry_history[1]["attempt"] == 2
        assert phase_result.retry_history[1]["error"] == "boom"
        # Attempt 3 — success
        assert phase_result.retry_history[2]["attempt"] == 3
        assert phase_result.retry_history[2]["error"] is None

    @patch("src.phases.runner.PHASE_MAX_RETRIES", 1)
    @patch("src.phases.runner.PHASE_RETRY_DELAY", 0)
    def test_uses_config_defaults(self) -> None:
        failed_result = MagicMock()
        failed_result.status = Status.FAILED
        success_result = MagicMock()
        success_result.status = Status.COMPLETED

        swarm1 = MagicMock(return_value=failed_result)
        swarm2 = MagicMock(return_value=success_result)
        factory = MagicMock(side_effect=[swarm1, swarm2])

        # Don't pass max_retries — should use config default (1)
        phase_result = run_phase(factory, "task", {})

        assert phase_result.attempts == 2


@pytest.mark.unit
class TestPhaseResult:
    """Verify PhaseResult dataclass."""

    def test_construction(self) -> None:
        result = MagicMock()
        pr = PhaseResult(result=result, attempts=2, retry_history=[{"attempt": 1}])
        assert pr.result is result
        assert pr.attempts == 2
        assert len(pr.retry_history) == 1

    def test_default_retry_history(self) -> None:
        result = MagicMock()
        pr = PhaseResult(result=result, attempts=1)
        assert pr.retry_history == []
