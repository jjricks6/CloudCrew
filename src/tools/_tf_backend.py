"""Terraform remote backend provisioning for customer AWS accounts.

Creates S3 bucket + DynamoDB lock table in the customer's account for
durable Terraform state. Idempotent — safe to call multiple times.

This module imports from state/ and config — NEVER from agents/.
"""

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.state.models import TerraformBackend

logger = logging.getLogger(__name__)

# Naming conventions
_BUCKET_PREFIX = "cloudcrew-tfstate"
_TABLE_PREFIX = "cloudcrew-tflocks"
_STATE_KEY = "terraform.tfstate"

# Minimal backend.tf — values injected via -backend-config CLI flags
_BACKEND_TF_CONTENT = 'terraform {\n  backend "s3" {}\n}\n'


def _bucket_name(project_id: str) -> str:
    """Generate S3 bucket name for a project's Terraform state.

    Args:
        project_id: The project identifier.

    Returns:
        Globally unique S3 bucket name (max 63 chars).
    """
    return f"{_BUCKET_PREFIX}-{project_id}"[:63]


def _table_name(project_id: str) -> str:
    """Generate DynamoDB table name for a project's Terraform lock.

    Args:
        project_id: The project identifier.

    Returns:
        DynamoDB table name (max 255 chars).
    """
    return f"{_TABLE_PREFIX}-{project_id}"[:255]


def provision_backend(
    project_id: str,
    region: str,
    access_key_id: str,
    secret_access_key: str,
) -> TerraformBackend:
    """Provision S3 bucket + DynamoDB lock table in the customer's account.

    Idempotent: if resources already exist, returns their coordinates
    without error.

    Args:
        project_id: The CloudCrew project identifier.
        region: AWS region for backend resources.
        access_key_id: Customer AWS access key ID.
        secret_access_key: Customer AWS secret access key.

    Returns:
        TerraformBackend with the provisioned resource coordinates.

    Raises:
        ClientError: If AWS API calls fail for reasons other than
            resource-already-exists.
    """
    bucket = _bucket_name(project_id)
    table = _table_name(project_id)

    session = boto3.Session(
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
    )

    _ensure_s3_bucket(session, bucket, region)
    _ensure_dynamodb_table(session, table, region)

    logger.info(
        "Terraform backend ready: bucket=%s table=%s region=%s",
        bucket,
        table,
        region,
    )
    return TerraformBackend(
        bucket=bucket,
        key=_STATE_KEY,
        region=region,
        dynamodb_table=table,
        provisioned_at=datetime.now(UTC).isoformat(),
    )


def _ensure_s3_bucket(session: boto3.Session, bucket: str, region: str) -> None:
    """Create S3 bucket with versioning, encryption, and public access block.

    Idempotent — skips creation if bucket already exists and is owned by caller.

    Args:
        session: Authenticated boto3 session for the customer's account.
        bucket: S3 bucket name.
        region: AWS region.

    Raises:
        ClientError: If bucket creation fails for a non-idempotent reason.
    """
    s3 = session.client("s3", region_name=region)

    try:
        create_kwargs: dict[str, Any] = {"Bucket": bucket}
        # us-east-1 must NOT specify LocationConstraint
        if region != "us-east-1":
            create_kwargs["CreateBucketConfiguration"] = {
                "LocationConstraint": region,
            }
        s3.create_bucket(**create_kwargs)
        logger.info("Created S3 state bucket: %s in %s", bucket, region)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code == "BucketAlreadyOwnedByYou":
            logger.info("S3 state bucket already exists: %s", bucket)
        else:
            raise

    # Enable versioning (protects against accidental state deletion)
    s3.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={"Status": "Enabled"},
    )

    # Enable default encryption (SSE-S3)
    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}},
            ],
        },
    )

    # Block all public access
    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )


def _ensure_dynamodb_table(session: boto3.Session, table: str, region: str) -> None:
    """Create DynamoDB lock table with PAY_PER_REQUEST billing.

    Idempotent — skips creation if table already exists.

    Args:
        session: Authenticated boto3 session for the customer's account.
        table: DynamoDB table name.
        region: AWS region.

    Raises:
        ClientError: If table creation fails for a non-idempotent reason.
    """
    dynamodb = session.client("dynamodb", region_name=region)

    try:
        dynamodb.create_table(
            TableName=table,
            KeySchema=[{"AttributeName": "LockID", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "LockID", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        logger.info("Created DynamoDB lock table: %s in %s", table, region)
        waiter = dynamodb.get_waiter("table_exists")
        waiter.wait(TableName=table, WaiterConfig={"Delay": 2, "MaxAttempts": 30})
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            logger.info("DynamoDB lock table already exists: %s", table)
        else:
            raise


def build_backend_config_args(backend: TerraformBackend) -> list[str]:
    """Build -backend-config CLI arguments for terraform init.

    Args:
        backend: The TerraformBackend configuration.

    Returns:
        List of CLI argument strings for terraform init.
    """
    return [
        f"-backend-config=bucket={backend.bucket}",
        f"-backend-config=key={backend.key}",
        f"-backend-config=region={backend.region}",
        f"-backend-config=dynamodb_table={backend.dynamodb_table}",
        "-backend-config=encrypt=true",
    ]


def ensure_backend_tf(directory: Path) -> bool:
    """Write a minimal backend.tf if one does not already exist.

    Checks all .tf files in the directory for an existing ``backend "s3"``
    block. If none is found, writes a minimal backend.tf with an empty S3
    backend block (values injected via -backend-config at runtime).

    Args:
        directory: Path to the Terraform directory.

    Returns:
        True if a backend.tf was written, False if one already existed.
    """
    for tf_file in directory.glob("*.tf"):
        content = tf_file.read_text()
        if 'backend "s3"' in content:
            logger.info("Existing S3 backend found in %s", tf_file.name)
            return False

    backend_path = directory / "backend.tf"
    backend_path.write_text(_BACKEND_TF_CONTENT)
    logger.info("Wrote minimal backend.tf to %s", directory)
    return True
