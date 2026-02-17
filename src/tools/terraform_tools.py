"""Terraform validation tools for infrastructure code.

Runs terraform CLI commands (init, validate) as subprocess calls against
the customer's project repository. The repo path comes from
invocation_state["git_repo_url"].

This module imports from tools/ helpers — NEVER from agents/.
"""

import logging
import subprocess
from typing import Any

from strands import tool
from strands.types.tools import ToolContext

from src.tools.git_tools import _get_repo, _resolve_path

logger = logging.getLogger(__name__)

_TERRAFORM_TIMEOUT = 60


def _run_terraform(args: list[str], cwd: str) -> subprocess.CompletedProcess[str]:
    """Run a terraform command with timeout and safety constraints.

    Args:
        args: Terraform CLI arguments (e.g. ["init", "-backend=false"]).
        cwd: Working directory for the command.

    Returns:
        CompletedProcess with stdout/stderr.

    Raises:
        FileNotFoundError: If terraform CLI is not installed.
        subprocess.TimeoutExpired: If command exceeds timeout.
    """
    return subprocess.run(  # noqa: S603
        ["terraform", *args],  # noqa: S607
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=_TERRAFORM_TIMEOUT,
    )


def _get_directory(invocation_state: dict[str, Any], directory: str) -> str:
    """Resolve and validate a directory path within the repo.

    Args:
        invocation_state: Agent invocation state containing git_repo_url.
        directory: Relative path to the directory.

    Returns:
        Absolute path string to the directory.

    Raises:
        ValueError: If git_repo_url is not set or path escapes repo.
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


@tool(context=True)
def terraform_validate(directory: str, tool_context: ToolContext) -> str:
    """Run terraform init and validate on a directory in the project repo.

    Initializes Terraform with no backend (local only) and then validates
    the configuration. Use this to check Terraform code for syntax and
    configuration errors before committing.

    Args:
        directory: Relative path to the directory containing .tf files.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Validation output or error message.
    """
    try:
        abs_path = _get_directory(tool_context.invocation_state, directory)
    except (ValueError, FileNotFoundError, NotADirectoryError) as e:
        return f"Error: {e}"

    try:
        init_result = _run_terraform(["-chdir=" + abs_path, "init", "-backend=false"], cwd=abs_path)
        if init_result.returncode != 0:
            logger.warning("terraform init failed in %s", directory)
            return f"terraform init failed:\n{init_result.stderr}"

        validate_result = _run_terraform(["-chdir=" + abs_path, "validate"], cwd=abs_path)
        if validate_result.returncode != 0:
            logger.warning("terraform validate failed in %s", directory)
            return f"terraform validate failed:\n{validate_result.stdout}\n{validate_result.stderr}"

        logger.info("terraform validate passed in %s", directory)
        return f"Validation successful:\n{validate_result.stdout}"

    except FileNotFoundError:
        return "Error: terraform CLI not found. Ensure terraform is installed and on PATH."
    except subprocess.TimeoutExpired:
        return f"Error: terraform command timed out after {_TERRAFORM_TIMEOUT}s"
