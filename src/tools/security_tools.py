"""Security scanning tools for infrastructure code.

Runs Checkov as a subprocess against Terraform files in the customer's
project repository. The repo path comes from invocation_state["git_repo_url"].

This module imports from tools/ helpers — NEVER from agents/.
"""

import json
import logging
import subprocess
from typing import Any

from strands import tool
from strands.types.tools import ToolContext

from src.tools.git_tools import _get_repo, _resolve_path

logger = logging.getLogger(__name__)

_CHECKOV_TIMEOUT = 120


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


def _format_checkov_results(raw_output: str) -> str:
    """Parse Checkov JSON output into a human-readable summary.

    Args:
        raw_output: Raw JSON string from Checkov stdout.

    Returns:
        Formatted summary with pass/fail counts and failed check details.
    """
    try:
        data = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError):
        return f"Could not parse Checkov output as JSON. Raw output:\n{raw_output}"

    # Checkov may return a list (multiple frameworks) or a single dict
    results_list = data if isinstance(data, list) else [data]

    lines: list[str] = []
    for result in results_list:
        summary = result.get("summary", {})
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        skipped = summary.get("skipped", 0)
        lines.append(f"Passed: {passed} | Failed: {failed} | Skipped: {skipped}")

        failed_checks = result.get("results", {}).get("failed_checks", [])
        if not failed_checks:
            continue

        lines.append("\nFailed checks:")
        for check in failed_checks:
            check_id = check.get("check_id", "unknown")
            check_name = check.get("name", "unknown")
            severity = check.get("severity", "UNKNOWN")
            resource = check.get("resource", "unknown")
            file_path = check.get("file_path", "unknown")
            lines.append(f"  [{severity}] {check_id}: {check_name}")
            lines.append(f"    Resource: {resource} ({file_path})")

    if not lines:
        return "No results returned from Checkov."

    return "\n".join(lines)


@tool(context=True)
def checkov_scan(directory: str, tool_context: ToolContext) -> str:
    """Run Checkov security scan on Terraform files in the project repo.

    Scans for security misconfigurations, compliance violations, and
    infrastructure best practice issues. Returns a summary of findings
    with severity levels.

    Args:
        directory: Relative path to the directory containing .tf files.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Scan results with severity counts and failed checks, or error message.
    """
    try:
        abs_path = _get_directory(tool_context.invocation_state, directory)
    except (ValueError, FileNotFoundError, NotADirectoryError) as e:
        return f"Error: {e}"

    try:
        result = subprocess.run(  # noqa: S603
            ["checkov", "-d", abs_path, "--framework", "terraform", "-o", "json", "--compact"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=_CHECKOV_TIMEOUT,
        )

        # Checkov returns exit code 1 when it finds failures (not an error)
        output = result.stdout or result.stderr
        if not output:
            return "Checkov produced no output."

        logger.info("checkov_scan completed for %s (exit code %d)", directory, result.returncode)
        return _format_checkov_results(output)

    except FileNotFoundError:
        return "Error: checkov CLI not found. Ensure checkov is installed and on PATH."
    except subprocess.TimeoutExpired:
        return f"Error: checkov scan timed out after {_CHECKOV_TIMEOUT}s"
