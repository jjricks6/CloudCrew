"""Phase summary tools for PM agent.

Provides tools for PM to generate and save phase summary documents.
"""

import logging
from typing import Any

import git
from strands import tool
from strands.types.tools import ToolContext

logger = logging.getLogger(__name__)


def _get_repo(invocation_state: dict[str, Any]) -> git.Repo:
    """Open the project Git repo from invocation_state.

    Args:
        invocation_state: Agent invocation state containing git_repo_url.

    Returns:
        A GitPython Repo object.

    Raises:
        ValueError: If git_repo_url is not set.
        git.InvalidGitRepositoryError: If the path is not a valid repo.
    """
    repo_path = invocation_state.get("git_repo_url", "")
    if not repo_path:
        msg = "git_repo_url not set in invocation_state"
        raise ValueError(msg)
    return git.Repo(str(repo_path))


def _resolve_path(repo: git.Repo, file_path: str) -> Any:
    """Resolve a relative file path within the repo working directory.

    Args:
        repo: The GitPython Repo object.
        file_path: Relative path within the repo.

    Returns:
        Absolute path to the file.

    Raises:
        ValueError: If the path tries to escape the repo directory.
    """
    from pathlib import Path

    repo_root = Path(repo.working_dir)
    resolved = (repo_root / file_path).resolve()
    if not str(resolved).startswith(str(repo_root.resolve())):
        msg = f"Path escapes repository: {file_path}"
        raise ValueError(msg)
    return resolved


@tool(context=True)
def git_write_phase_summary(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a phase summary to docs/phase-summaries/ in the project repo and commit it.

    Only the PM agent should use this tool. Files must be under docs/phase-summaries/.
    Generate this at the end of each phase, before the phase enters AWAITING_APPROVAL status.

    Args:
        file_path: Relative path within the repo (must start with docs/phase-summaries/).
        content: Phase summary content (markdown recommended).
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("docs/phase-summaries/"):
        return "Error: PM agent can only write to docs/phase-summaries/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_phase_summary: committed %s", file_path)
    return f"Committed: {file_path}"
