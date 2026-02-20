"""Tests for src/phases/pm_chat_handler.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.chat import ChatMessage
from src.state.models import Phase, PhaseStatus, TaskLedger


@pytest.mark.unit
class TestPMChatHandler:
    """Verify the PM chat Lambda handler."""

    @patch("src.phases.pm_chat_handler.broadcast_to_project")
    @patch("src.phases.pm_chat_handler.store_chat_message")
    @patch("src.phases.pm_chat_handler.create_pm_agent")
    @patch("src.phases.pm_chat_handler.get_chat_history")
    @patch("src.phases.pm_chat_handler.read_ledger")
    def test_handler_invokes_pm_and_stores_response(
        self,
        mock_read_ledger: MagicMock,
        mock_get_history: MagicMock,
        mock_create_pm: MagicMock,
        mock_store: MagicMock,
        mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.pm_chat_handler import handler

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            current_phase=Phase.DISCOVERY,
            phase_status=PhaseStatus.IN_PROGRESS,
        )
        mock_get_history.return_value = []

        mock_pm = MagicMock()
        mock_pm.return_value = "I can help with that!"
        mock_create_pm.return_value = mock_pm

        event = {
            "project_id": "proj-1",
            "customer_message": "What's the status?",
            "message_id": "msg-001",
        }

        result = handler(event, None)

        # Verify PM was created and callback was set
        mock_create_pm.assert_called_once()
        assert mock_pm.callback_handler is not None

        # Verify PM was invoked
        mock_pm.assert_called_once()
        task_arg = mock_pm.call_args.args[0]
        assert "What's the status?" in task_arg

        # Verify response was stored
        mock_store.assert_called_once()
        store_kwargs = mock_store.call_args.kwargs
        assert store_kwargs["role"] == "pm"
        assert store_kwargs["content"] == "I can help with that!"

        # Verify broadcasts were made (thinking + done)
        broadcast_calls = mock_broadcast.call_args_list
        events = [call.args[1]["event"] for call in broadcast_calls]
        assert "chat_thinking" in events
        assert "chat_done" in events

        # Verify return value
        assert result["project_id"] == "proj-1"
        assert "pm_message_id" in result
        assert result["response_length"] > 0

    @patch("src.phases.pm_chat_handler.broadcast_to_project")
    @patch("src.phases.pm_chat_handler.store_chat_message")
    @patch("src.phases.pm_chat_handler.create_pm_agent")
    @patch("src.phases.pm_chat_handler.get_chat_history")
    @patch("src.phases.pm_chat_handler.read_ledger")
    def test_handler_includes_chat_history_in_prompt(
        self,
        mock_read_ledger: MagicMock,
        mock_get_history: MagicMock,
        mock_create_pm: MagicMock,
        _mock_store: MagicMock,
        _mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.pm_chat_handler import handler

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")
        mock_get_history.return_value = [
            ChatMessage(message_id="prev-1", role="customer", content="Previous question", timestamp="t1"),
            ChatMessage(message_id="prev-2", role="pm", content="Previous answer", timestamp="t2"),
        ]

        mock_pm = MagicMock()
        mock_pm.return_value = "Updated answer"
        mock_create_pm.return_value = mock_pm

        event = {
            "project_id": "proj-1",
            "customer_message": "Follow-up question",
            "message_id": "msg-002",
        }

        handler(event, None)

        task_arg = mock_pm.call_args.args[0]
        assert "Previous question" in task_arg
        assert "Previous answer" in task_arg
        assert "Follow-up question" in task_arg

    @patch("src.phases.pm_chat_handler.broadcast_to_project")
    @patch("src.phases.pm_chat_handler.store_chat_message")
    @patch("src.phases.pm_chat_handler.create_pm_agent")
    @patch("src.phases.pm_chat_handler.get_chat_history")
    @patch("src.phases.pm_chat_handler.read_ledger")
    def test_handler_recovers_from_agent_error(
        self,
        mock_read_ledger: MagicMock,
        mock_get_history: MagicMock,
        mock_create_pm: MagicMock,
        mock_store: MagicMock,
        mock_broadcast: MagicMock,
    ) -> None:
        from src.phases.pm_chat_handler import handler

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")
        mock_get_history.return_value = []

        mock_pm = MagicMock()
        mock_pm.side_effect = RuntimeError("Agent crashed")
        mock_create_pm.return_value = mock_pm

        event = {
            "project_id": "proj-1",
            "customer_message": "Hello",
            "message_id": "msg-003",
        }

        handler(event, None)

        # Should still store a fallback message
        mock_store.assert_called_once()
        store_kwargs = mock_store.call_args.kwargs
        assert "error" in store_kwargs["content"].lower()

        # Should still broadcast done
        broadcast_events = [call.args[1]["event"] for call in mock_broadcast.call_args_list]
        assert "chat_done" in broadcast_events


@pytest.mark.unit
class TestWSCallback:
    """Verify the WebSocket callback factory."""

    @patch("src.phases.pm_chat_handler.broadcast_to_project")
    def test_callback_broadcasts_data_with_phase(self, mock_broadcast: MagicMock) -> None:
        from src.phases.pm_chat_handler import _make_ws_callback

        callback = _make_ws_callback("proj-1", "DISCOVERY")
        callback(data="Hello")

        mock_broadcast.assert_called_once()
        msg = mock_broadcast.call_args.args[1]
        assert msg["event"] == "chat_chunk"
        assert msg["content"] == "Hello"
        assert msg["project_id"] == "proj-1"
        assert msg["phase"] == "DISCOVERY"

    @patch("src.phases.pm_chat_handler.broadcast_to_project")
    def test_callback_ignores_empty_data(self, mock_broadcast: MagicMock) -> None:
        from src.phases.pm_chat_handler import _make_ws_callback

        callback = _make_ws_callback("proj-1", "DISCOVERY")
        callback(data="")

        mock_broadcast.assert_not_called()

    @patch("src.phases.pm_chat_handler.broadcast_to_project")
    def test_callback_ignores_complete_flag(self, mock_broadcast: MagicMock) -> None:
        from src.phases.pm_chat_handler import _make_ws_callback

        callback = _make_ws_callback("proj-1", "DISCOVERY")
        callback(data="", complete=True)

        mock_broadcast.assert_not_called()
