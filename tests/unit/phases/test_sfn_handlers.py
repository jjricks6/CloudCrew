"""Tests for src/phases/sfn_handlers.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
@patch("src.phases.sfn_handlers.broadcast_to_project")
class TestStartPhaseHandler:
    """Verify start_phase_handler behavior."""

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.sfn_handlers.boto3")
    def test_starts_ecs_task(
        self,
        mock_boto3: MagicMock,
        mock_read_ledger: MagicMock,
        _mock_write_ledger: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.sfn_handlers import start_phase_handler
        from src.state.models import TaskLedger

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")
        mock_ecs = MagicMock()
        mock_boto3.client.return_value = mock_ecs
        mock_ecs.run_task.return_value = {
            "tasks": [{"taskArn": "arn:aws:ecs:us-east-1:123:task/abc"}],
            "failures": [],
        }

        event = {
            "project_id": "proj-1",
            "phase": "DISCOVERY",
            "task_token": "token-abc",
            "customer_feedback": "",
        }

        result = start_phase_handler(event, None)

        mock_ecs.run_task.assert_called_once()
        assert result["ecs_task_arn"] == "arn:aws:ecs:us-east-1:123:task/abc"
        assert result["project_id"] == "proj-1"
        assert result["phase"] == "DISCOVERY"

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.sfn_handlers.boto3")
    def test_passes_env_vars_to_ecs(
        self,
        mock_boto3: MagicMock,
        mock_read_ledger: MagicMock,
        _mock_write_ledger: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.sfn_handlers import start_phase_handler
        from src.state.models import TaskLedger

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")
        mock_ecs = MagicMock()
        mock_boto3.client.return_value = mock_ecs
        mock_ecs.run_task.return_value = {"tasks": [{"taskArn": "arn"}], "failures": []}

        event = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "task_token": "token-xyz",
            "customer_feedback": "Fix the VPC",
        }

        start_phase_handler(event, None)

        call_kwargs = mock_ecs.run_task.call_args.kwargs
        overrides = call_kwargs["overrides"]["containerOverrides"][0]["environment"]
        env_map = {e["name"]: e["value"] for e in overrides}
        assert env_map["PROJECT_ID"] == "proj-1"
        assert env_map["PHASE"] == "ARCHITECTURE"
        assert env_map["TASK_TOKEN"] == "token-xyz"
        assert env_map["CUSTOMER_FEEDBACK"] == "Fix the VPC"

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.sfn_handlers.boto3")
    def test_updates_ledger_phase_and_status(
        self,
        mock_boto3: MagicMock,
        mock_read_ledger: MagicMock,
        mock_write_ledger: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        """Verify ledger is updated to new phase/IN_PROGRESS before ECS launch."""
        from src.phases.sfn_handlers import start_phase_handler
        from src.state.models import Phase, PhaseStatus, TaskLedger

        mock_ledger = TaskLedger(
            project_id="proj-1",
            current_phase=Phase.DISCOVERY,
            phase_status=PhaseStatus.AWAITING_APPROVAL,
        )
        mock_read_ledger.return_value = mock_ledger
        mock_ecs = MagicMock()
        mock_boto3.client.return_value = mock_ecs
        mock_ecs.run_task.return_value = {"tasks": [{"taskArn": "arn"}], "failures": []}

        event = {
            "project_id": "proj-1",
            "phase": "ARCHITECTURE",
            "task_token": "token-abc",
        }

        start_phase_handler(event, None)

        # Verify ledger was updated to new phase before ECS launch
        assert mock_ledger.current_phase == Phase.ARCHITECTURE
        assert mock_ledger.phase_status == PhaseStatus.IN_PROGRESS
        mock_write_ledger.assert_called_once()

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.sfn_handlers.boto3")
    def test_raises_on_ecs_launch_failure(
        self,
        mock_boto3: MagicMock,
        mock_read_ledger: MagicMock,
        _mock_write_ledger: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        """Verify RuntimeError raised when ECS returns no tasks."""
        from src.phases.sfn_handlers import start_phase_handler
        from src.state.models import TaskLedger

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")
        mock_ecs = MagicMock()
        mock_boto3.client.return_value = mock_ecs
        mock_ecs.run_task.return_value = {
            "tasks": [],
            "failures": [{"reason": "RESOURCE:ENI", "detail": "no capacity"}],
        }

        event = {
            "project_id": "proj-1",
            "phase": "DISCOVERY",
            "task_token": "token-abc",
        }

        with pytest.raises(RuntimeError, match="ECS RunTask returned no tasks"):
            start_phase_handler(event, None)


@pytest.mark.unit
@patch("src.phases.sfn_handlers.broadcast_to_project")
class TestStoreApprovalTokenHandler:
    """Verify store_approval_token_handler behavior."""

    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.sfn_handlers.store_token")
    def test_stores_token_and_updates_ledger(
        self,
        mock_store_token: MagicMock,
        mock_read_ledger: MagicMock,
        mock_write_ledger: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.sfn_handlers import store_approval_token_handler
        from src.state.models import PhaseStatus, TaskLedger

        mock_ledger = TaskLedger(project_id="proj-1")
        mock_read_ledger.return_value = mock_ledger

        event = {
            "project_id": "proj-1",
            "phase": "DISCOVERY",
            "task_token": "token-abc",
        }

        result = store_approval_token_handler(event, None)

        mock_store_token.assert_called_once_with("cloudcrew-projects", "proj-1", "DISCOVERY", "token-abc")
        assert mock_ledger.phase_status == PhaseStatus.AWAITING_APPROVAL
        mock_write_ledger.assert_called_once()
        assert result["status"] == "TOKEN_STORED"


@pytest.mark.unit
class TestSfnRoute:
    """Verify sfn_handlers.route dispatcher."""

    @patch("src.phases.sfn_handlers.start_phase_handler")
    def test_routes_start_phase(self, mock_handler: MagicMock) -> None:
        from src.phases.sfn_handlers import route

        mock_handler.return_value = {"ecs_task_arn": "arn"}
        event = {"action": "start_phase", "project_id": "p1", "phase": "DISCOVERY", "task_token": "t"}
        result = route(event, None)
        mock_handler.assert_called_once()
        assert result["ecs_task_arn"] == "arn"

    @patch("src.phases.sfn_handlers.broadcast_to_project")
    @patch("src.state.ledger.write_ledger")
    @patch("src.state.ledger.read_ledger")
    @patch("src.phases.sfn_handlers.store_token")
    def test_routes_store_approval(
        self,
        _mock_store: MagicMock,
        mock_read: MagicMock,
        _mock_write: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.sfn_handlers import route
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1")
        event = {"action": "store_approval_token", "project_id": "p1", "phase": "DISCOVERY", "task_token": "t"}
        result = route(event, None)
        assert result["status"] == "TOKEN_STORED"

    def test_routes_unknown_action(self) -> None:
        from src.phases.sfn_handlers import route

        result = route({"action": "bad"}, None)
        assert "Unknown action" in result["error"]
