"""Scoped Git tools for reading and writing project repository files.

Tools in this module operate on the customer's project Git repository.
They use GitPython for git operations (add, commit). The repo path comes
from invocation_state["git_repo_url"], which points to a local clone
(set by the ECS phase runner in production, or PROJECT_REPO_PATH env var in dev).

This module imports from state/ and config — NEVER from agents/.
"""

import logging
from pathlib import Path
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


def _resolve_path(repo: git.Repo, file_path: str) -> Path:
    """Resolve a relative file path within the repo working directory.

    Args:
        repo: The GitPython Repo object.
        file_path: Relative path within the repo.

    Returns:
        Absolute path to the file.

    Raises:
        ValueError: If the path tries to escape the repo directory.
    """
    repo_root = Path(repo.working_dir)
    resolved = (repo_root / file_path).resolve()
    if not str(resolved).startswith(str(repo_root.resolve())):
        msg = f"Path escapes repository: {file_path}"
        raise ValueError(msg)
    return resolved


@tool(context=True)
def git_read(file_path: str, tool_context: ToolContext) -> str:
    """Read a file from the project repository.

    Args:
        file_path: Relative path to the file within the repo.
        tool_context: Strands tool context (injected by framework).

    Returns:
        The file contents as a string.
    """
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    if not resolved.exists():
        return f"Error: file not found: {file_path}"
    logger.info("git_read: %s", file_path)
    return resolved.read_text()


@tool(context=True)
def git_list(directory: str, tool_context: ToolContext) -> str:
    """List files in a directory in the project repository.

    Args:
        directory: Relative path to the directory within the repo.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Newline-separated list of relative file paths, or an error message.
    """
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, directory)
    if not resolved.exists():
        return f"Error: directory not found: {directory}"
    if not resolved.is_dir():
        return f"Error: not a directory: {directory}"
    logger.info("git_list: %s", directory)
    repo_root = Path(repo.working_dir)
    files = sorted(str(p.relative_to(repo_root)) for p in resolved.rglob("*") if p.is_file() and ".git" not in p.parts)
    return "\n".join(files)


@tool(context=True)
def git_write_architecture(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a file to docs/architecture/ in the project repo and commit it.

    Only the SA agent should use this tool. Files must be under docs/architecture/.

    Args:
        file_path: Relative path within the repo (must start with docs/architecture/).
        content: File content to write.
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("docs/architecture/"):
        return "Error: SA agent can only write to docs/architecture/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_architecture: committed %s", file_path)
    return f"Committed: {file_path}"
