"""WebSocket API Gateway Lambda handlers for real-time dashboard events.

Manages WebSocket connections (connect/disconnect) in DynamoDB. The
broadcast_to_project utility lives in src/state/broadcast.py so that
state modules can import it without violating architecture boundaries.

This module is in phases/ — the ONLY package allowed to import from agents/.
(Though this module does not import agents — it handles infrastructure only.)
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import boto3

from src.config import AWS_REGION, CONNECTIONS_TABLE

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _get_table(table_name: str) -> Any:
    """Get a DynamoDB Table resource."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def _ttl_2h() -> int:
    """Return a Unix timestamp 2 hours from now (connection expiry)."""
    return int(datetime.now(UTC).timestamp()) + 7200


def connect_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle WebSocket $connect route.

    Stores the connection ID and associated project ID in DynamoDB so
    broadcast_to_project() can find all connected clients.

    The project_id is passed as a query string parameter:
    ``wss://...?projectId=<uuid>``

    Args:
        event: API Gateway WebSocket event.
        context: Lambda context (unused).

    Returns:
        HTTP 200 response.
    """
    connection_id = event["requestContext"]["connectionId"]
    query_params = event.get("queryStringParameters") or {}
    project_id = query_params.get("projectId", "")

    if not project_id:
        logger.warning("WebSocket connect without projectId, connectionId=%s", connection_id)
        return {"statusCode": 400, "body": "Missing projectId query parameter"}

    if not CONNECTIONS_TABLE:
        logger.warning("CONNECTIONS_TABLE not configured, skipping connection storage")
        return {"statusCode": 200, "body": "OK"}

    table = _get_table(CONNECTIONS_TABLE)
    table.put_item(
        Item={
            "PK": project_id,
            "SK": connection_id,
            "connected_at": _now_iso(),
            "ttl": _ttl_2h(),
        },
    )
    logger.info("WebSocket connected: connection=%s project=%s", connection_id, project_id)
    return {"statusCode": 200, "body": "Connected"}


def disconnect_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle WebSocket $disconnect route.

    Removes the connection record from DynamoDB. Since we don't know
    the project_id at disconnect time, we scan for the connection_id.

    Args:
        event: API Gateway WebSocket event.
        context: Lambda context (unused).

    Returns:
        HTTP 200 response.
    """
    connection_id = event["requestContext"]["connectionId"]

    if not CONNECTIONS_TABLE:
        return {"statusCode": 200, "body": "OK"}

    # At small scale (<100 connections) a scan is fine.
    # At larger scale, add a GSI on connectionId.
    table = _get_table(CONNECTIONS_TABLE)
    response = table.scan(
        FilterExpression="SK = :conn_id",
        ExpressionAttributeValues={":conn_id": connection_id},
    )
    for item in response.get("Items", []):
        table.delete_item(
            Key={"PK": item["PK"], "SK": item["SK"]},
        )
    logger.info("WebSocket disconnected: connection=%s", connection_id)
    return {"statusCode": 200, "body": "Disconnected"}


def default_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle WebSocket $default route.

    Processes incoming messages from connected clients. Currently handles
    heartbeat/ping messages.

    Args:
        event: API Gateway WebSocket event.
        context: Lambda context (unused).

    Returns:
        HTTP 200 response.
    """
    connection_id = event["requestContext"]["connectionId"]
    body = event.get("body", "")

    try:
        message = json.loads(body) if body else {}
    except json.JSONDecodeError:
        message = {}

    action = message.get("action", "")

    if action == "heartbeat":
        logger.debug("Heartbeat from connection=%s", connection_id)
        return {"statusCode": 200, "body": "pong"}

    logger.debug("Default handler: connection=%s action=%s", connection_id, action)
    return {"statusCode": 200, "body": "OK"}


def route(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route WebSocket events to the appropriate handler.

    API Gateway sends the route key in event.requestContext.routeKey.

    Args:
        event: API Gateway WebSocket event.
        context: Lambda context.

    Returns:
        Response dict.
    """
    route_key = event.get("requestContext", {}).get("routeKey", "$default")

    if route_key == "$connect":
        return connect_handler(event, context)
    if route_key == "$disconnect":
        return disconnect_handler(event, context)
    return default_handler(event, context)
