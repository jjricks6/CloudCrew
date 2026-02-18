"""Tests for src/state/interrupts.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestStoreInterrupt:
    """Verify store_interrupt behavior."""

    @patch("src.state.interrupts.boto3")
    def test_store_interrupt(self, mock_boto3: MagicMock) -> None:
        from src.state.interrupts import store_interrupt

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        store_interrupt("test-table", "proj-1", "int-001", "What color?")

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "PROJECT#proj-1"
        assert item["SK"] == "INTERRUPT#int-001"
        assert item["question"] == "What color?"
        assert item["status"] == "PENDING"
        assert item["response"] == ""


@pytest.mark.unit
class TestGetInterruptResponse:
    """Verify get_interrupt_response behavior."""

    @patch("src.state.interrupts.boto3")
    def test_pending_returns_empty(self, mock_boto3: MagicMock) -> None:
        from src.state.interrupts import get_interrupt_response

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {"status": "PENDING", "response": ""},
        }

        result = get_interrupt_response("test-table", "proj-1", "int-001")
        assert result == ""

    @patch("src.state.interrupts.boto3")
    def test_answered_returns_response(self, mock_boto3: MagicMock) -> None:
        from src.state.interrupts import get_interrupt_response

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {"status": "ANSWERED", "response": "Blue"},
        }

        result = get_interrupt_response("test-table", "proj-1", "int-001")
        assert result == "Blue"

    @patch("src.state.interrupts.boto3")
    def test_not_found_returns_empty(self, mock_boto3: MagicMock) -> None:
        from src.state.interrupts import get_interrupt_response

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {}

        result = get_interrupt_response("test-table", "proj-1", "int-001")
        assert result == ""


@pytest.mark.unit
class TestStoreInterruptResponse:
    """Verify store_interrupt_response behavior."""

    @patch("src.state.interrupts.boto3")
    def test_store_response(self, mock_boto3: MagicMock) -> None:
        from src.state.interrupts import store_interrupt_response

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        store_interrupt_response("test-table", "proj-1", "int-001", "Blue")

        mock_table.update_item.assert_called_once()
        call_kwargs = mock_table.update_item.call_args.kwargs
        assert call_kwargs["Key"]["PK"] == "PROJECT#proj-1"
        assert call_kwargs["Key"]["SK"] == "INTERRUPT#int-001"
        assert call_kwargs["ExpressionAttributeValues"][":resp"] == "Blue"
        assert call_kwargs["ExpressionAttributeValues"][":status"] == "ANSWERED"
