"""Tests for src/state/broadcast.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.state.broadcast import broadcast_to_project


@pytest.mark.unit
class TestBroadcastToProject:
    """Verify broadcasting messages to WebSocket clients."""

    @patch("src.state.broadcast.CONNECTIONS_TABLE", "")
    def test_noop_when_connections_table_empty(self) -> None:
        result = broadcast_to_project("proj-1", {"event": "test"})
        assert result == 0

    @patch("src.state.broadcast.WEBSOCKET_API_ENDPOINT", "")
    @patch("src.state.broadcast.CONNECTIONS_TABLE", "cloudcrew-connections")
    def test_noop_when_endpoint_empty(self) -> None:
        result = broadcast_to_project("proj-1", {"event": "test"})
        assert result == 0

    @patch("src.state.broadcast.boto3")
    @patch("src.state.broadcast.WEBSOCKET_API_ENDPOINT", "https://ws.example.com")
    @patch("src.state.broadcast.CONNECTIONS_TABLE", "cloudcrew-connections")
    def test_sends_to_all_connections(self, mock_boto3: MagicMock) -> None:
        # Set up DynamoDB mock
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [
                {"PK": "proj-1", "SK": "conn-1"},
                {"PK": "proj-1", "SK": "conn-2"},
            ],
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        # Set up API Gateway Management API mock
        mock_apigw = MagicMock()

        def resource_side_effect(service, **kwargs):
            return mock_dynamodb

        def client_side_effect(service, **kwargs):
            return mock_apigw

        mock_boto3.resource.side_effect = resource_side_effect
        mock_boto3.client.side_effect = client_side_effect

        result = broadcast_to_project("proj-1", {"event": "phase_started"})

        assert result == 2
        assert mock_apigw.post_to_connection.call_count == 2

    @patch("src.state.broadcast.boto3")
    @patch("src.state.broadcast.WEBSOCKET_API_ENDPOINT", "https://ws.example.com")
    @patch("src.state.broadcast.CONNECTIONS_TABLE", "cloudcrew-connections")
    def test_returns_zero_when_no_connections(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_dynamodb

        result = broadcast_to_project("proj-1", {"event": "test"})

        assert result == 0

    @patch("src.state.broadcast.boto3")
    @patch("src.state.broadcast.WEBSOCKET_API_ENDPOINT", "https://ws.example.com")
    @patch("src.state.broadcast.CONNECTIONS_TABLE", "cloudcrew-connections")
    def test_cleans_up_stale_connections(self, mock_boto3: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.query.return_value = {
            "Items": [{"PK": "proj-1", "SK": "stale-conn"}],
        }
        mock_dynamodb = MagicMock()
        mock_dynamodb.Table.return_value = mock_table

        # Simulate GoneException
        mock_apigw = MagicMock()
        gone_exception = type("GoneException", (Exception,), {})
        mock_apigw.exceptions.GoneException = gone_exception
        mock_apigw.post_to_connection.side_effect = gone_exception("Gone")

        mock_boto3.resource.return_value = mock_dynamodb
        mock_boto3.client.return_value = mock_apigw

        result = broadcast_to_project("proj-1", {"event": "test"})

        assert result == 0
        mock_table.delete_item.assert_called_once()
