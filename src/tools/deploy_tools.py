"""Terraform deployment tools for the Production phase.

Runs terraform plan/apply/output/destroy against the customer's AWS account
using credentials stored in Secrets Manager. The Infra agent uses these tools
during the Production phase; customer approval (via PM + ask_customer) is
required before apply.

All tools automatically provision a remote S3 backend in the customer's AWS
account on first use, so Terraform state persists across ECS container restarts.

This module imports from state/ and tools/ helpers — NEVER from agents/.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any

from botocore.exceptions import ClientError
from strands import tool
from strands.types.tools import ToolContext

from src.config import TASK_LEDGER_TABLE
from src.state.ledger import read_ledger, write_ledger
from src.state.models import TerraformBackend
from src.state.secrets import get_aws_credentials
from src.tools._tf_backend import (
    build_backend_config_args,
    ensure_backend_tf,
    provision_backend,
)
from src.tools.git_tools import _get_repo, _resolve_path

logger = logging.getLogger(__name__)

_PLAN_TIMEOUT = 180
_APPLY_TIMEOUT = 600
_OUTPUT_TIMEOUT = 30
_DESTROY_TIMEOUT = 600


def _get_project_id(invocation_state: dict[str, Any]) -> str:
    """Extract project_id from invocation state.

    Args:
        invocation_state: Agent invocation state dict.

    Returns:
        The project_id string.

    Raises:
        ValueError: If project_id is not set.
    """
    project_id = str(invocation_state.get("project_id", ""))
    if not project_id:
        msg = "project_id not set in invocation state"
        raise ValueError(msg)
    return project_id


def _get_directory(invocation_state: dict[str, Any], directory: str) -> str:
    """Resolve and validate a directory path within the repo.

    Args:
        invocation_state: Agent invocation state containing git_repo_url.
        directory: Relative path to the directory.

    Returns:
        Absolute path string to the directory.

    Raises:
        ValueError: If git_repo_url is not set or path escapes repo.
        FileNotFoundError: If the directory does not exist.
        NotADirectoryError: If the path is not a directory.
    """
    repo = _get_repo(invocation_state)
    resolved = _resolve_path(repo, directory)
    if not resolved.exists():
        msg = f"Directory not found: {directory}"
        raise FileNotFoundError(msg)
    if not resolved.is_dir():
        msg = f"Not a directory: {directory}"
        raise NotADirectoryError(msg)
    return str(resolved)


def _build_aws_env(project_id: str) -> dict[str, str]:
    """Build environment dict with customer AWS credentials.

    Reads credentials from Secrets Manager and region from the task ledger.
    Inherits the current process environment and adds/overrides AWS vars.

    Args:
        project_id: The project identifier.

    Returns:
        Environment dict suitable for subprocess.run(env=...).

    Raises:
        ValueError: If AWS credentials are not stored for the project.
    """
    access_key_id, secret_access_key = get_aws_credentials(project_id)
    if not access_key_id or not secret_access_key:
        msg = "No AWS credentials found in Secrets Manager. Use store_aws_credentials during Discovery first."
        raise ValueError(msg)

    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    region = ledger.aws_region_target or "us-east-1"

    env = os.environ.copy()
    env["AWS_ACCESS_KEY_ID"] = access_key_id
    env["AWS_SECRET_ACCESS_KEY"] = secret_access_key
    env["AWS_DEFAULT_REGION"] = region
    # Prevent Terraform from prompting for input
    env["TF_INPUT"] = "0"
    return env


def _run_terraform_with_creds(
    project_id: str,
    args: list[str],
    cwd: str,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    """Run a terraform command with customer AWS credentials injected.

    Args:
        project_id: The project identifier (for credential lookup).
        args: Terraform CLI arguments (e.g. ["plan", "-no-color"]).
        cwd: Working directory for the command.
        timeout: Command timeout in seconds.

    Returns:
        CompletedProcess with stdout/stderr.

    Raises:
        ValueError: If credentials are missing.
        FileNotFoundError: If terraform CLI is not installed.
        subprocess.TimeoutExpired: If command exceeds timeout.
    """
    env = _build_aws_env(project_id)
    return subprocess.run(  # noqa: S603
        ["terraform", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _ensure_remote_backend(project_id: str) -> TerraformBackend:
    """Ensure a remote S3 backend exists for the project's Terraform state.

    Reads the task ledger to check for a cached backend config. If none exists,
    provisions a new S3 bucket + DynamoDB lock table in the customer's account
    and persists the config to the ledger.

    Args:
        project_id: The project identifier.

    Returns:
        TerraformBackend with the remote backend coordinates.

    Raises:
        ValueError: If AWS credentials are not stored for the project.
    """
    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    if ledger.terraform_backend:
        logger.info("Using cached remote backend for project=%s", project_id)
        return ledger.terraform_backend

    access_key_id, secret_access_key = get_aws_credentials(project_id)
    if not access_key_id or not secret_access_key:
        msg = "No AWS credentials found. Use store_aws_credentials during Discovery first."
        raise ValueError(msg)

    region = ledger.aws_region_target or "us-east-1"
    backend = provision_backend(project_id, region, access_key_id, secret_access_key)

    ledger.terraform_backend = backend
    write_ledger(TASK_LEDGER_TABLE, project_id, ledger)
    logger.info("Provisioned and saved remote backend for project=%s", project_id)
    return backend


def _init_with_backend(
    project_id: str,
    abs_path: str,
    backend: TerraformBackend,
    timeout: int,
) -> subprocess.CompletedProcess[str]:
    """Run terraform init with remote backend configuration.

    Ensures a ``backend.tf`` file exists in the directory, then runs
    ``terraform init -no-color -reconfigure`` with ``-backend-config`` flags
    pointing to the project's S3 state bucket.

    Args:
        project_id: The project identifier (for credential lookup).
        abs_path: Absolute path to the Terraform directory.
        backend: The remote backend configuration.
        timeout: Command timeout in seconds.

    Returns:
        CompletedProcess from the terraform init command.
    """
    ensure_backend_tf(Path(abs_path))
    backend_args = build_backend_config_args(backend)
    return _run_terraform_with_creds(
        project_id,
        ["-chdir=" + abs_path, "init", "-no-color", "-reconfigure", *backend_args],
        cwd=abs_path,
        timeout=timeout,
    )


@tool(context=True)
def terraform_plan(directory: str, tool_context: ToolContext) -> str:
    """Run terraform init and plan against the customer's AWS account.

    Initializes Terraform with the real backend (not local-only) and generates
    an execution plan showing what resources will be created, changed, or
    destroyed. Present the plan output to the customer for approval before
    running terraform_apply.

    Args:
        directory: Relative path to the directory containing .tf files.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Plan output text, or an error message.
    """
    try:
        project_id = _get_project_id(tool_context.invocation_state)
        abs_path = _get_directory(tool_context.invocation_state, directory)
    except (ValueError, FileNotFoundError, NotADirectoryError) as e:
        return f"Error: {e}"

    try:
        # Provision remote backend (idempotent — cached after first call)
        backend = _ensure_remote_backend(project_id)

        # Initialize with remote S3 backend
        init_result = _init_with_backend(project_id, abs_path, backend, _PLAN_TIMEOUT)
        if init_result.returncode != 0:
            logger.warning("terraform init failed in %s for project=%s", directory, project_id)
            return f"terraform init failed:\n{init_result.stderr}"

        # Generate execution plan
        plan_result = _run_terraform_with_creds(
            project_id,
            ["-chdir=" + abs_path, "plan", "-no-color"],
            cwd=abs_path,
            timeout=_PLAN_TIMEOUT,
        )
        if plan_result.returncode != 0:
            logger.warning("terraform plan failed in %s for project=%s", directory, project_id)
            return f"terraform plan failed:\n{plan_result.stdout}\n{plan_result.stderr}"

        logger.info("terraform plan succeeded in %s for project=%s", directory, project_id)
        return f"Plan output:\n{plan_result.stdout}"

    except ValueError as e:
        return f"Error: {e}"
    except ClientError as e:
        logger.error("AWS error during terraform plan for project=%s: %s", project_id, e)
        return f"Error provisioning backend: {e.response['Error']['Message']}"
    except FileNotFoundError:
        return "Error: terraform CLI not found. Ensure terraform is installed."
    except subprocess.TimeoutExpired:
        return f"Error: terraform command timed out after {_PLAN_TIMEOUT}s."


@tool(context=True)
def terraform_apply(directory: str, tool_context: ToolContext) -> str:
    """Apply Terraform changes to the customer's AWS account.

    Runs terraform apply with auto-approve. Only call this AFTER the customer
    has approved the plan output (via PM and ask_customer). If apply fails,
    read the error, fix the Terraform code, and run terraform_plan again.

    Args:
        directory: Relative path to the directory containing .tf files.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Apply output text, or an error message.
    """
    try:
        project_id = _get_project_id(tool_context.invocation_state)
        abs_path = _get_directory(tool_context.invocation_state, directory)
    except (ValueError, FileNotFoundError, NotADirectoryError) as e:
        return f"Error: {e}"

    try:
        # Provision remote backend and init (idempotent)
        backend = _ensure_remote_backend(project_id)
        init_result = _init_with_backend(project_id, abs_path, backend, _APPLY_TIMEOUT)
        if init_result.returncode != 0:
            logger.warning("terraform init failed in %s for project=%s", directory, project_id)
            return f"terraform init failed:\n{init_result.stderr}"

        result = _run_terraform_with_creds(
            project_id,
            ["-chdir=" + abs_path, "apply", "-auto-approve", "-no-color"],
            cwd=abs_path,
            timeout=_APPLY_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("terraform apply failed in %s for project=%s", directory, project_id)
            return f"terraform apply failed:\n{result.stdout}\n{result.stderr}"

        logger.info("terraform apply succeeded in %s for project=%s", directory, project_id)
        return f"Apply successful:\n{result.stdout}"

    except ValueError as e:
        return f"Error: {e}"
    except ClientError as e:
        logger.error("AWS error during terraform apply for project=%s: %s", project_id, e)
        return f"Error provisioning backend: {e.response['Error']['Message']}"
    except FileNotFoundError:
        return "Error: terraform CLI not found. Ensure terraform is installed."
    except subprocess.TimeoutExpired:
        return f"Error: terraform apply timed out after {_APPLY_TIMEOUT}s."


@tool(context=True)
def terraform_output(directory: str, tool_context: ToolContext) -> str:
    """Read Terraform outputs after a successful apply.

    Returns the JSON-formatted outputs (API endpoints, resource ARNs, etc.)
    from the current Terraform state. Use this after terraform_apply succeeds
    to capture deployment details.

    Args:
        directory: Relative path to the directory containing .tf files.
        tool_context: Strands tool context (injected by framework).

    Returns:
        JSON string of Terraform outputs, or an error message.
    """
    try:
        project_id = _get_project_id(tool_context.invocation_state)
        abs_path = _get_directory(tool_context.invocation_state, directory)
    except (ValueError, FileNotFoundError, NotADirectoryError) as e:
        return f"Error: {e}"

    try:
        # Provision remote backend and init (idempotent)
        backend = _ensure_remote_backend(project_id)
        init_result = _init_with_backend(project_id, abs_path, backend, _OUTPUT_TIMEOUT)
        if init_result.returncode != 0:
            logger.warning("terraform init failed in %s for project=%s", directory, project_id)
            return f"terraform init failed:\n{init_result.stderr}"

        result = _run_terraform_with_creds(
            project_id,
            ["-chdir=" + abs_path, "output", "-json"],
            cwd=abs_path,
            timeout=_OUTPUT_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("terraform output failed in %s for project=%s", directory, project_id)
            return f"terraform output failed:\n{result.stderr}"

        logger.info("terraform output read from %s for project=%s", directory, project_id)
        return result.stdout or "{}"

    except ValueError as e:
        return f"Error: {e}"
    except ClientError as e:
        logger.error("AWS error during terraform output for project=%s: %s", project_id, e)
        return f"Error provisioning backend: {e.response['Error']['Message']}"
    except FileNotFoundError:
        return "Error: terraform CLI not found. Ensure terraform is installed."
    except subprocess.TimeoutExpired:
        return f"Error: terraform output timed out after {_OUTPUT_TIMEOUT}s."


@tool(context=True)
def terraform_destroy(directory: str, tool_context: ToolContext) -> str:
    """Destroy all Terraform-managed resources in the customer's AWS account.

    Runs terraform destroy with auto-approve. Only call this AFTER the customer
    has explicitly approved teardown (via PM and ask_customer). Use for cleanup
    or rollback scenarios.

    Args:
        directory: Relative path to the directory containing .tf files.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Destroy output text, or an error message.
    """
    try:
        project_id = _get_project_id(tool_context.invocation_state)
        abs_path = _get_directory(tool_context.invocation_state, directory)
    except (ValueError, FileNotFoundError, NotADirectoryError) as e:
        return f"Error: {e}"

    try:
        # Provision remote backend and init (idempotent)
        backend = _ensure_remote_backend(project_id)
        init_result = _init_with_backend(project_id, abs_path, backend, _DESTROY_TIMEOUT)
        if init_result.returncode != 0:
            logger.warning("terraform init failed in %s for project=%s", directory, project_id)
            return f"terraform init failed:\n{init_result.stderr}"

        result = _run_terraform_with_creds(
            project_id,
            ["-chdir=" + abs_path, "destroy", "-auto-approve", "-no-color"],
            cwd=abs_path,
            timeout=_DESTROY_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning("terraform destroy failed in %s for project=%s", directory, project_id)
            return f"terraform destroy failed:\n{result.stdout}\n{result.stderr}"

        logger.info("terraform destroy succeeded in %s for project=%s", directory, project_id)
        return f"Destroy successful:\n{result.stdout}"

    except ValueError as e:
        return f"Error: {e}"
    except ClientError as e:
        logger.error("AWS error during terraform destroy for project=%s: %s", project_id, e)
        return f"Error provisioning backend: {e.response['Error']['Message']}"
    except FileNotFoundError:
        return "Error: terraform CLI not found. Ensure terraform is installed."
    except subprocess.TimeoutExpired:
        return f"Error: terraform destroy timed out after {_DESTROY_TIMEOUT}s."
