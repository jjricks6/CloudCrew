"""Tests for src/state/approval.py."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestStoreToken:
    """Verify store_token behavior."""

    @patch("src.state.approval.boto3")
    def test_store_token(self, mock_boto3: MagicMock) -> None:
        from src.state.approval import store_token

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        store_token("test-table", "proj-1", "DISCOVERY", "token-abc")

        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "PROJECT#proj-1"
        assert item["SK"] == "TOKEN#DISCOVERY"
        assert item["task_token"] == "token-abc"
        assert item["phase"] == "DISCOVERY"
        assert "created_at" in item


@pytest.mark.unit
class TestGetToken:
    """Verify get_token behavior."""

    @patch("src.state.approval.boto3")
    def test_get_token_found(self, mock_boto3: MagicMock) -> None:
        from src.state.approval import get_token

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {
            "Item": {"task_token": "token-xyz"},
        }

        result = get_token("test-table", "proj-1", "DISCOVERY")
        assert result == "token-xyz"

    @patch("src.state.approval.boto3")
    def test_get_token_not_found(self, mock_boto3: MagicMock) -> None:
        from src.state.approval import get_token

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        mock_table.get_item.return_value = {}

        result = get_token("test-table", "proj-1", "DISCOVERY")
        assert result == ""


@pytest.mark.unit
class TestDeleteToken:
    """Verify delete_token behavior."""

    @patch("src.state.approval.boto3")
    def test_delete_token(self, mock_boto3: MagicMock) -> None:
        from src.state.approval import delete_token

        mock_table = MagicMock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        delete_token("test-table", "proj-1", "DISCOVERY")

        mock_table.delete_item.assert_called_once_with(
            Key={"PK": "PROJECT#proj-1", "SK": "TOKEN#DISCOVERY"},
        )
