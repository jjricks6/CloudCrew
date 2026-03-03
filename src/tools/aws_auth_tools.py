"""AWS authentication tools for storing and verifying customer account credentials.

The PM agent uses these during Discovery to collect the customer's IAM access
keys and verify access to their AWS account. The keys are stored in Secrets
Manager (never in the task ledger) and account metadata is persisted on the ledger.

This module imports from state/ and config — NEVER from agents/.

.. note::
    IAM access keys are a temporary solution. TODO: migrate to cross-account
    IAM role assumption (``sts:AssumeRole``) for better security.
"""

import logging

import boto3
from botocore.exceptions import ClientError
from strands import tool
from strands.types.tools import ToolContext

from src.config import TASK_LEDGER_TABLE
from src.state.ledger import read_ledger, write_ledger
from src.state.secrets import get_aws_credentials, store_aws_credentials

logger = logging.getLogger(__name__)

_ACCESS_KEY_PREFIX = "AKIA"
_ACCESS_KEY_LENGTH = 20
_SECRET_KEY_LENGTH = 40


@tool(context=True)
def store_aws_credentials_tool(
    access_key_id: str,
    secret_access_key: str,
    account_id: str,
    region: str,
    tool_context: ToolContext,
) -> str:
    """Store AWS IAM access keys and account details for the project.

    Stores the keys securely in AWS Secrets Manager and saves the account ID
    and region in the task ledger. NEVER record the access keys as ledger facts.

    Args:
        access_key_id: The AWS access key ID (starts with AKIA, 20 characters).
        secret_access_key: The AWS secret access key (40 characters).
        account_id: The 12-digit AWS account ID.
        region: The target AWS region (e.g., us-east-1).
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success or error message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    if not project_id:
        return "Error: project_id not set in invocation state."

    # Validate access key format
    if not access_key_id or len(access_key_id) != _ACCESS_KEY_LENGTH:
        return f"Error: Access Key ID must be {_ACCESS_KEY_LENGTH} characters. Got {len(access_key_id)} characters."
    if not access_key_id.startswith(_ACCESS_KEY_PREFIX):
        return f"Error: Access Key ID must start with '{_ACCESS_KEY_PREFIX}'."

    if not secret_access_key or len(secret_access_key) != _SECRET_KEY_LENGTH:
        return (
            f"Error: Secret Access Key must be {_SECRET_KEY_LENGTH} characters. "
            f"Got {len(secret_access_key)} characters."
        )

    # Validate account ID (12 digits)
    if not account_id or len(account_id) != 12 or not account_id.isdigit():
        return "Error: AWS account ID must be a 12-digit number."

    if not region:
        return "Error: AWS region is required."

    # Store keys in Secrets Manager
    stored = store_aws_credentials(project_id, access_key_id, secret_access_key)
    if not stored:
        return "Error: Failed to store AWS credentials in Secrets Manager. Please try again."

    # Update ledger with account metadata (never the keys)
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
        ledger.aws_account_id = account_id
        ledger.aws_region_target = region
        write_ledger(TASK_LEDGER_TABLE, project_id, ledger)
    except Exception:
        logger.exception("Failed to update ledger with AWS account info for project=%s", project_id)
        return "Error: Keys stored but failed to save account details to ledger."

    logger.info(
        "Stored AWS credentials for project=%s, account=%s, region=%s",
        project_id,
        account_id,
        region,
    )
    return f"AWS credentials stored successfully for account {account_id} in region {region}."


@tool(context=True)
def verify_aws_access(tool_context: ToolContext) -> str:
    """Verify that stored AWS credentials can access the customer's account.

    Reads account details from the ledger and keys from Secrets Manager,
    then calls ``sts:GetCallerIdentity`` to confirm access and verify the
    account ID matches.

    Args:
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with account details, or an error message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    if not project_id:
        return "Error: project_id not set in invocation state."

    # Read account ID from ledger
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    except Exception:
        logger.exception("Failed to read ledger for project=%s", project_id)
        return "Error: Could not read project ledger."

    expected_account = ledger.aws_account_id
    region = ledger.aws_region_target
    if not expected_account:
        return "Error: No AWS account ID stored. Use store_aws_credentials first."

    # Get keys from Secrets Manager
    access_key_id, secret_access_key = get_aws_credentials(project_id)
    if not access_key_id or not secret_access_key:
        return "Error: No AWS credentials found in Secrets Manager. Use store_aws_credentials first."

    # Verify access with STS GetCallerIdentity
    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region or "us-east-1",
        )
        identity = sts.get_caller_identity()
        actual_account = identity.get("Account", "")
        arn = identity.get("Arn", "")

        if actual_account != expected_account:
            logger.warning(
                "AWS account mismatch for project=%s: expected=%s, actual=%s",
                project_id,
                expected_account,
                actual_account,
            )
            return (
                f"Error: Account mismatch. You said account {expected_account} "
                f"but the credentials belong to account {actual_account}. "
                "Please double-check the account ID and credentials."
            )

        logger.info(
            "AWS access verified for project=%s, account=%s, arn=%s",
            project_id,
            actual_account,
            arn,
        )
        return (
            f"AWS access verified for account {actual_account} "
            f"in region {region}. IAM identity: {arn}. "
            "Credentials are stored and ready for use."
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.warning("STS verification failed for project=%s: %s", project_id, error_code)
        if error_code in ("InvalidClientTokenId", "SignatureDoesNotMatch"):
            return "Error: Invalid AWS credentials. Please double-check the Access Key ID and Secret Access Key."
        return f"Error: AWS verification failed — {error_code}. Please check your credentials."
    except Exception:
        logger.exception("Unexpected error verifying AWS access for project=%s", project_id)
        return "Error: Unexpected error during AWS access verification."
