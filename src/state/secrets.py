"""Secrets Manager integration for sensitive credentials.

This module handles storing and fetching secrets from AWS Secrets Manager:
- Bedrock API key (cross-account inference)
- GitHub PATs (per-project customer repo access)
- AWS IAM access keys (per-project customer account access)

Caching is used for read-heavy paths to minimize API calls.

.. note::
    AWS access keys are a temporary solution. TODO: migrate to cross-account
    IAM role assumption (``sts:AssumeRole``) for better security — the customer
    would create a role with a trust policy for CloudCrew's account.
"""

import json
import logging
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError

from src.config import AWS_REGION, BEDROCK_API_KEY_SECRET

logger = logging.getLogger(__name__)

_secrets_client = boto3.client("secretsmanager", region_name=AWS_REGION)


@lru_cache(maxsize=1)
def get_bedrock_api_key() -> str:
    """Fetch Bedrock API key from Secrets Manager.

    Uses LRU cache to avoid repeated API calls. Cache is shared across
    Lambda container lifecycle.

    Returns:
        The Bedrock API key string, or empty string if retrieval fails.

    Raises:
        Logs errors but does not raise — returns empty string to allow graceful
        degradation if Secrets Manager is unavailable (e.g., during local dev).
    """
    try:
        response = _secrets_client.get_secret_value(SecretId=BEDROCK_API_KEY_SECRET)

        # SecretString can be either a string directly or JSON
        secret = str(response.get("SecretString", ""))
        if secret.startswith("{"):
            try:
                parsed: dict[str, str] = json.loads(secret)
                api_key = parsed.get("api_key", "")
                return api_key or ""
            except (json.JSONDecodeError, ValueError):
                return secret
        return secret
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.warning(
                "Bedrock API key secret not found in Secrets Manager: %s",
                BEDROCK_API_KEY_SECRET,
            )
        else:
            logger.error(
                "Failed to retrieve Bedrock API key from Secrets Manager: %s",
                e.response["Error"]["Code"],
            )
        return ""
    except Exception as e:
        logger.error("Unexpected error fetching Bedrock API key: %s", type(e).__name__)
        return ""


def clear_bedrock_api_key_cache() -> None:
    """Clear the cached Bedrock API key (for testing/debugging)."""
    get_bedrock_api_key.cache_clear()


def store_github_pat(project_id: str, pat: str) -> bool:
    """Store a GitHub PAT in Secrets Manager for a project.

    Creates the secret if it doesn't exist, or updates it if it does.
    The secret is stored under ``cloudcrew/{project_id}/github-pat``.

    Args:
        project_id: The project identifier.
        pat: The GitHub Personal Access Token.

    Returns:
        True if the PAT was stored successfully, False otherwise.
    """
    secret_id = f"cloudcrew/{project_id}/github-pat"
    try:
        _secrets_client.create_secret(
            Name=secret_id,
            SecretString=pat,
            Description=f"GitHub PAT for CloudCrew project {project_id}",
        )
        logger.info("Created GitHub PAT secret for project=%s", project_id)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceExistsException":
            try:
                _secrets_client.put_secret_value(
                    SecretId=secret_id,
                    SecretString=pat,
                )
                logger.info("Updated GitHub PAT secret for project=%s", project_id)
                return True
            except ClientError:
                logger.exception("Failed to update GitHub PAT for project=%s", project_id)
                return False
        logger.exception("Failed to create GitHub PAT secret for project=%s", project_id)
        return False
    except Exception:
        logger.exception("Unexpected error storing GitHub PAT for project=%s", project_id)
        return False


def get_github_pat(project_id: str) -> str:
    """Retrieve a GitHub PAT from Secrets Manager for a project.

    Args:
        project_id: The project identifier.

    Returns:
        The GitHub PAT string, or empty string if retrieval fails.
    """
    secret_id = f"cloudcrew/{project_id}/github-pat"
    try:
        response = _secrets_client.get_secret_value(SecretId=secret_id)
        return str(response.get("SecretString", ""))
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.info("GitHub PAT not found for project=%s", project_id)
        else:
            logger.error(
                "Failed to retrieve GitHub PAT for project=%s: %s",
                project_id,
                e.response["Error"]["Code"],
            )
        return ""
    except Exception:
        logger.exception("Unexpected error fetching GitHub PAT for project=%s", project_id)
        return ""


def store_aws_credentials(project_id: str, access_key_id: str, secret_access_key: str) -> bool:
    """Store AWS IAM access keys in Secrets Manager for a project.

    Creates the secret if it doesn't exist, or updates it if it does.
    The secret is stored as JSON under ``cloudcrew/{project_id}/aws-credentials``.

    Args:
        project_id: The project identifier.
        access_key_id: The AWS access key ID.
        secret_access_key: The AWS secret access key.

    Returns:
        True if the credentials were stored successfully, False otherwise.
    """
    secret_id = f"cloudcrew/{project_id}/aws-credentials"
    payload = json.dumps({"access_key_id": access_key_id, "secret_access_key": secret_access_key})
    try:
        _secrets_client.create_secret(
            Name=secret_id,
            SecretString=payload,
            Description=f"AWS IAM access keys for CloudCrew project {project_id}",
        )
        logger.info("Created AWS credentials secret for project=%s", project_id)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceExistsException":
            try:
                _secrets_client.put_secret_value(
                    SecretId=secret_id,
                    SecretString=payload,
                )
                logger.info("Updated AWS credentials secret for project=%s", project_id)
                return True
            except ClientError:
                logger.exception("Failed to update AWS credentials for project=%s", project_id)
                return False
        logger.exception("Failed to create AWS credentials secret for project=%s", project_id)
        return False
    except Exception:
        logger.exception("Unexpected error storing AWS credentials for project=%s", project_id)
        return False


def get_aws_credentials(project_id: str) -> tuple[str, str]:
    """Retrieve AWS IAM access keys from Secrets Manager for a project.

    Args:
        project_id: The project identifier.

    Returns:
        Tuple of (access_key_id, secret_access_key). Returns ("", "") if
        retrieval fails.
    """
    secret_id = f"cloudcrew/{project_id}/aws-credentials"
    try:
        response = _secrets_client.get_secret_value(SecretId=secret_id)
        secret = str(response.get("SecretString", ""))
        parsed: dict[str, str] = json.loads(secret)
        return parsed.get("access_key_id", ""), parsed.get("secret_access_key", "")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            logger.info("AWS credentials not found for project=%s", project_id)
        else:
            logger.error(
                "Failed to retrieve AWS credentials for project=%s: %s",
                project_id,
                e.response["Error"]["Code"],
            )
        return "", ""
    except (json.JSONDecodeError, ValueError):
        logger.exception("Malformed AWS credentials secret for project=%s", project_id)
        return "", ""
    except Exception:
        logger.exception("Unexpected error fetching AWS credentials for project=%s", project_id)
        return "", ""
