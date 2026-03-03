"""Git authentication tools for storing and verifying customer repo credentials.

The PM agent uses these during Discovery to collect the customer's GitHub PAT
and verify access to their repository. The PAT is stored in Secrets Manager
(never in the task ledger) and the repo URL is persisted on the ledger.

This module imports from state/ and config — NEVER from agents/.
"""

import logging
import subprocess
from urllib.parse import urlparse

from strands import tool
from strands.types.tools import ToolContext

from src.config import TASK_LEDGER_TABLE
from src.state.ledger import read_ledger, write_ledger
from src.state.secrets import get_github_pat, store_github_pat

logger = logging.getLogger(__name__)


def _build_auth_url(repo_url: str, pat: str) -> str:
    """Insert a PAT into an HTTPS GitHub URL for authenticated git operations.

    Args:
        repo_url: The HTTPS GitHub URL (e.g., https://github.com/org/repo).
        pat: The GitHub Personal Access Token.

    Returns:
        URL with PAT embedded (e.g., https://{pat}@github.com/org/repo).

    Raises:
        ValueError: If the URL is not a valid HTTPS GitHub URL.
    """
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or not parsed.hostname:
        msg = f"Invalid HTTPS URL: {repo_url}"
        raise ValueError(msg)
    return f"https://{pat}@{parsed.hostname}{parsed.path}"


@tool(context=True)
def store_git_credentials(
    repo_url: str,
    github_pat: str,
    tool_context: ToolContext,
) -> str:
    """Store GitHub repository URL and PAT for the project.

    Stores the PAT securely in AWS Secrets Manager and saves the repository
    URL in the task ledger. NEVER record the PAT as a ledger fact.

    Args:
        repo_url: The customer's GitHub repository HTTPS URL.
        github_pat: A GitHub Personal Access Token with repo scope.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success or error message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    if not project_id:
        return "Error: project_id not set in invocation state."

    # Validate URL format
    parsed = urlparse(repo_url)
    if parsed.scheme != "https" or not parsed.hostname:
        return f"Error: Repository URL must be HTTPS. Got: {repo_url}"

    if not github_pat or len(github_pat) < 10:
        return "Error: Invalid GitHub PAT — must be at least 10 characters."

    # Store PAT in Secrets Manager
    stored = store_github_pat(project_id, github_pat)
    if not stored:
        return "Error: Failed to store GitHub PAT in Secrets Manager. Please try again."

    # Update ledger with repo URL (never the PAT)
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
        ledger.git_repo_url_customer = repo_url.rstrip("/")
        write_ledger(TASK_LEDGER_TABLE, project_id, ledger)
    except Exception:
        logger.exception("Failed to update ledger with repo URL for project=%s", project_id)
        return "Error: PAT stored but failed to save repo URL to ledger."

    logger.info(
        "Stored git credentials for project=%s, repo=%s",
        project_id,
        repo_url,
    )
    return f"Git credentials stored successfully for {repo_url}."


@tool(context=True)
def verify_git_access(tool_context: ToolContext) -> str:
    """Verify that stored GitHub credentials can access the customer's repository.

    Reads the repo URL from the ledger and PAT from Secrets Manager, then runs
    ``git ls-remote`` to verify access.

    Args:
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with repo details, or an error message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    if not project_id:
        return "Error: project_id not set in invocation state."

    # Read repo URL from ledger
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    except Exception:
        logger.exception("Failed to read ledger for project=%s", project_id)
        return "Error: Could not read project ledger."

    repo_url = ledger.git_repo_url_customer
    if not repo_url:
        return "Error: No repository URL stored. Use store_git_credentials first."

    # Get PAT from Secrets Manager
    pat = get_github_pat(project_id)
    if not pat:
        return "Error: No GitHub PAT found in Secrets Manager. Use store_git_credentials first."

    # Verify access with git ls-remote
    try:
        auth_url = _build_auth_url(repo_url, pat)
        result = subprocess.run(  # noqa: S603 — trusted input from Secrets Manager
            ["git", "ls-remote", "--heads", auth_url],  # noqa: S607 — git is a well-known binary
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()
            logger.warning(
                "git ls-remote failed for project=%s: %s",
                project_id,
                stderr,
            )
            return (
                f"Error: Cannot access {repo_url}. "
                "Please verify the PAT has 'repo' scope and the URL is correct. "
                f"Git error: {stderr}"
            )

        # Count branches
        branches = [line for line in result.stdout.strip().split("\n") if line]
        branch_count = len(branches)
        logger.info(
            "Git access verified for project=%s, repo=%s, branches=%d",
            project_id,
            repo_url,
            branch_count,
        )
        return (
            f"Access verified for {repo_url}. "
            f"Repository has {branch_count} branch(es). "
            "Credentials are stored and ready for use."
        )
    except subprocess.TimeoutExpired:
        return f"Error: git ls-remote timed out for {repo_url}. The repository may be unreachable."
    except ValueError as e:
        return f"Error: {e}"
    except Exception:
        logger.exception("Unexpected error verifying git access for project=%s", project_id)
        return "Error: Unexpected error during git access verification."
