"""WebSocket broadcast utility for pushing events to connected dashboard clients.

Queries the connections table for all clients subscribed to a project and
sends a message to each via the API Gateway Management API.

This module imports from config — NEVER from agents/, tools/, or phases/.
"""

import json
import logging
from typing import Any

import boto3

from src.config import AWS_REGION, CONNECTIONS_TABLE, WEBSOCKET_API_ENDPOINT

logger = logging.getLogger(__name__)


def broadcast_to_project(project_id: str, message: dict[str, Any]) -> int:
    """Broadcast a message to all WebSocket clients subscribed to a project.

    Queries DynamoDB for all connection IDs associated with the project,
    then posts the message to each via the API Gateway Management API.
    Stale connections (GoneException) are automatically cleaned up.

    When CONNECTIONS_TABLE or WEBSOCKET_API_ENDPOINT is not configured,
    this is a no-op (returns 0).

    Args:
        project_id: The project to broadcast to.
        message: Dict to serialize as JSON and send.

    Returns:
        Number of clients the message was successfully sent to.
    """
    if not CONNECTIONS_TABLE or not WEBSOCKET_API_ENDPOINT:
        return 0

    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(CONNECTIONS_TABLE)

    response = table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": project_id},
    )
    connections = response.get("Items", [])

    if not connections:
        return 0

    apigw = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=WEBSOCKET_API_ENDPOINT,
        region_name=AWS_REGION,
    )

    payload = json.dumps(message).encode("utf-8")
    sent = 0

    for conn in connections:
        connection_id = conn["SK"]
        try:
            apigw.post_to_connection(
                ConnectionId=connection_id,
                Data=payload,
            )
            sent += 1
        except apigw.exceptions.GoneException:
            logger.debug("Removing stale connection %s", connection_id)
            table.delete_item(Key={"PK": conn["PK"], "SK": conn["SK"]})
        except Exception:
            logger.exception("Failed to send to connection %s", connection_id)

    logger.debug(
        "Broadcast to %d/%d clients for project %s",
        sent,
        len(connections),
        project_id,
    )
    return sent
