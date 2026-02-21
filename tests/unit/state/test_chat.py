"""Tests for src/state/chat.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.chat import (
    ChatMessage,
    chat_history_to_prompt,
    get_chat_history,
    new_message_id,
    store_chat_message,
)


@pytest.mark.unit
class TestStoreChatMessage:
    """Verify storing chat messages to DynamoDB."""

    @patch("src.state.chat._get_table")
    def test_stores_message_with_correct_keys(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        result = store_chat_message(
            table_name="cloudcrew-projects",
            project_id="proj-1",
            message_id="msg-001",
            role="customer",
            content="Hello PM!",
            timestamp="2026-01-01T00:00:00",
        )

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]

        assert item["PK"] == "PROJECT#proj-1"
        assert item["SK"].startswith("CHAT#2026-01-01T00:00:00#msg-001")
        assert item["role"] == "customer"
        assert item["content"] == "Hello PM!"
        assert item["message_id"] == "msg-001"

        assert isinstance(result, ChatMessage)
        assert result.message_id == "msg-001"
        assert result.role == "customer"

    @patch("src.state.chat._get_table")
    def test_defaults_timestamp_to_now(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        result = store_chat_message(
            table_name="cloudcrew-projects",
            project_id="proj-1",
            message_id="msg-002",
            role="pm",
            content="Hi there!",
        )

        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["timestamp"] != ""
        assert result.timestamp != ""


@pytest.mark.unit
class TestGetChatHistory:
    """Verify querying chat history."""

    @patch("src.state.chat._get_table")
    def test_returns_messages_in_chronological_order(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        # DynamoDB returns newest first (ScanIndexForward=False)
        mock_table.query.return_value = {
            "Items": [
                {
                    "message_id": "msg-2",
                    "role": "pm",
                    "content": "Hello!",
                    "timestamp": "2026-01-01T00:01:00",
                },
                {
                    "message_id": "msg-1",
                    "role": "customer",
                    "content": "Hi!",
                    "timestamp": "2026-01-01T00:00:00",
                },
            ],
        }
        mock_get_table.return_value = mock_table

        messages = get_chat_history("cloudcrew-projects", "proj-1")

        # Should be reversed to chronological order
        assert len(messages) == 2
        assert messages[0].message_id == "msg-1"
        assert messages[1].message_id == "msg-2"

    @patch("src.state.chat._get_table")
    def test_returns_empty_list_when_no_messages(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_get_table.return_value = mock_table

        messages = get_chat_history("cloudcrew-projects", "proj-1")

        assert messages == []

    @patch("src.state.chat._get_table")
    def test_passes_limit_to_query(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_get_table.return_value = mock_table

        get_chat_history("cloudcrew-projects", "proj-1", limit=10)

        query_kwargs = mock_table.query.call_args.kwargs
        assert query_kwargs["Limit"] == 10
        assert query_kwargs["ScanIndexForward"] is False

    @patch("src.state.chat._get_table")
    def test_queries_with_chat_prefix(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_get_table.return_value = mock_table

        get_chat_history("cloudcrew-projects", "proj-1")

        query_kwargs = mock_table.query.call_args.kwargs
        assert ":prefix" in query_kwargs["ExpressionAttributeValues"]
        assert query_kwargs["ExpressionAttributeValues"][":prefix"] == "CHAT#"


@pytest.mark.unit
class TestChatHistoryToPrompt:
    """Verify formatting chat history for PM agent."""

    def test_formats_customer_and_pm_messages(self) -> None:
        messages = [
            ChatMessage(message_id="1", role="customer", content="Hello", timestamp="t1"),
            ChatMessage(message_id="2", role="pm", content="Hi there!", timestamp="t2"),
        ]

        result = chat_history_to_prompt(messages)

        assert "[Customer]: Hello" in result
        assert "[PM]: Hi there!" in result

    def test_returns_placeholder_for_empty_history(self) -> None:
        result = chat_history_to_prompt([])
        assert "No previous messages" in result


@pytest.mark.unit
class TestNewMessageId:
    """Verify message ID generation."""

    def test_returns_unique_ids(self) -> None:
        id1 = new_message_id()
        id2 = new_message_id()
        assert id1 != id2
        assert len(id1) > 0
