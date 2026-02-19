"""Tests for src/phases/ws_handlers.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.phases.ws_handlers import (
    connect_handler,
    default_handler,
    disconnect_handler,
    route,
)


@pytest.mark.unit
class TestConnectHandler:
    """Verify WebSocket $connect handling."""

    @patch("src.phases.ws_handlers.CONNECTIONS_TABLE", "cloudcrew-connections")
    @patch("src.phases.ws_handlers._get_table")
    def test_stores_connection(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_get_table.return_value = mock_table

        event = {
            "requestContext": {"connectionId": "conn-123"},
            "queryStringParameters": {"projectId": "proj-1"},
        }
        result = connect_handler(event, None)

        assert result["statusCode"] == 200
        mock_table.put_item.assert_called_once()
        item = mock_table.put_item.call_args.kwargs["Item"]
        assert item["PK"] == "proj-1"
        assert item["SK"] == "conn-123"
        assert "ttl" in item

    def test_returns_400_when_no_project_id(self) -> None:
        event = {
            "requestContext": {"connectionId": "conn-123"},
            "queryStringParameters": {},
        }
        result = connect_handler(event, None)
        assert result["statusCode"] == 400

    def test_returns_400_when_query_params_none(self) -> None:
        event = {
            "requestContext": {"connectionId": "conn-123"},
            "queryStringParameters": None,
        }
        result = connect_handler(event, None)
        assert result["statusCode"] == 400

    @patch("src.phases.ws_handlers.CONNECTIONS_TABLE", "")
    def test_returns_ok_when_table_not_configured(self) -> None:
        event = {
            "requestContext": {"connectionId": "conn-123"},
            "queryStringParameters": {"projectId": "proj-1"},
        }
        result = connect_handler(event, None)
        assert result["statusCode"] == 200


@pytest.mark.unit
class TestDisconnectHandler:
    """Verify WebSocket $disconnect handling."""

    @patch("src.phases.ws_handlers.CONNECTIONS_TABLE", "cloudcrew-connections")
    @patch("src.phases.ws_handlers._get_table")
    def test_deletes_connection(self, mock_get_table: MagicMock) -> None:
        mock_table = MagicMock()
        mock_table.scan.return_value = {
            "Items": [{"PK": "proj-1", "SK": "conn-123"}],
        }
        mock_get_table.return_value = mock_table

        event = {"requestContext": {"connectionId": "conn-123"}}
        result = disconnect_handler(event, None)

        assert result["statusCode"] == 200
        mock_table.delete_item.assert_called_once_with(
            Key={"PK": "proj-1", "SK": "conn-123"},
        )

    @patch("src.phases.ws_handlers.CONNECTIONS_TABLE", "")
    def test_noop_when_table_not_configured(self) -> None:
        event = {"requestContext": {"connectionId": "conn-123"}}
        result = disconnect_handler(event, None)
        assert result["statusCode"] == 200


@pytest.mark.unit
class TestDefaultHandler:
    """Verify WebSocket $default handling."""

    def test_handles_heartbeat(self) -> None:
        event = {
            "requestContext": {"connectionId": "conn-123"},
            "body": '{"action": "heartbeat"}',
        }
        result = default_handler(event, None)
        assert result["statusCode"] == 200
        assert result["body"] == "pong"

    def test_handles_empty_body(self) -> None:
        event = {
            "requestContext": {"connectionId": "conn-123"},
            "body": "",
        }
        result = default_handler(event, None)
        assert result["statusCode"] == 200

    def test_handles_invalid_json(self) -> None:
        event = {
            "requestContext": {"connectionId": "conn-123"},
            "body": "not json",
        }
        result = default_handler(event, None)
        assert result["statusCode"] == 200


@pytest.mark.unit
class TestRoute:
    """Verify WebSocket route dispatcher."""

    @patch("src.phases.ws_handlers.connect_handler")
    def test_routes_connect(self, mock_handler: MagicMock) -> None:
        mock_handler.return_value = {"statusCode": 200}
        event = {"requestContext": {"routeKey": "$connect"}}
        route(event, None)
        mock_handler.assert_called_once()

    @patch("src.phases.ws_handlers.disconnect_handler")
    def test_routes_disconnect(self, mock_handler: MagicMock) -> None:
        mock_handler.return_value = {"statusCode": 200}
        event = {"requestContext": {"routeKey": "$disconnect"}}
        route(event, None)
        mock_handler.assert_called_once()

    @patch("src.phases.ws_handlers.default_handler")
    def test_routes_default(self, mock_handler: MagicMock) -> None:
        mock_handler.return_value = {"statusCode": 200}
        event = {"requestContext": {"routeKey": "$default"}}
        route(event, None)
        mock_handler.assert_called_once()

    @patch("src.phases.ws_handlers.default_handler")
    def test_routes_unknown_to_default(self, mock_handler: MagicMock) -> None:
        mock_handler.return_value = {"statusCode": 200}
        event = {"requestContext": {"routeKey": "custom_action"}}
        route(event, None)
        mock_handler.assert_called_once()
