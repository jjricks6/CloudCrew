"""Scoped Git tools for reading and writing project repository files.

Tools in this module operate on the customer's project Git repository.
They use GitPython for git operations (add, commit). The repo path comes
from invocation_state["git_repo_url"], which points to a local clone
(set by the ECS phase runner in production, or PROJECT_REPO_PATH env var in dev).

This module imports from state/ and config — NEVER from agents/.
"""

import json
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
        return (
            f"Directory '{directory}' does not exist yet — no files have been "
            "created there. This is normal if this area of the project hasn't "
            "been worked on yet. Do not retry with different paths."
        )
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


@tool(context=True)
def git_write_infra(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a file to infra/ in the project repo and commit it.

    Only the Infra agent should use this tool. Files must be under infra/.

    Args:
        file_path: Relative path within the repo (must start with infra/).
        content: File content to write.
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("infra/"):
        return "Error: Infra agent can only write to infra/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_infra: committed %s", file_path)
    return f"Committed: {file_path}"


@tool(context=True)
def git_write_security(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a file to security/ in the project repo and commit it.

    Only the Security agent should use this tool. Files must be under security/.

    Args:
        file_path: Relative path within the repo (must start with security/).
        content: File content to write.
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("security/"):
        return "Error: Security agent can only write to security/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_security: committed %s", file_path)
    return f"Committed: {file_path}"


@tool(context=True)
def git_write_project_plan(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a file to docs/project-plan/ in the project repo and commit it.

    Only the PM agent should use this tool. Files must be under docs/project-plan/.

    Args:
        file_path: Relative path within the repo (must start with docs/project-plan/).
        content: File content to write.
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("docs/project-plan/"):
        return "Error: PM agent can only write to docs/project-plan/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_project_plan: committed %s", file_path)
    return f"Committed: {file_path}"


@tool(context=True)
def git_write_app(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a file to app/ in the project repo and commit it.

    Only the Dev agent should use this tool. Files must be under app/.

    Args:
        file_path: Relative path within the repo (must start with app/).
        content: File content to write.
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("app/"):
        return "Error: Dev agent can only write to app/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_app: committed %s", file_path)
    return f"Committed: {file_path}"


@tool(context=True)
def git_write_data(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a file to data/ in the project repo and commit it.

    Only the Data agent should use this tool. Files must be under data/.

    Args:
        file_path: Relative path within the repo (must start with data/).
        content: File content to write.
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("data/"):
        return "Error: Data agent can only write to data/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_data: committed %s", file_path)
    return f"Committed: {file_path}"


@tool(context=True)
def git_write_tests(
    file_path: str,
    content: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write a file to app/tests/ in the project repo and commit it.

    Only the QA agent should use this tool. Files must be under app/tests/.

    Args:
        file_path: Relative path within the repo (must start with app/tests/).
        content: File content to write.
        commit_message: Git commit message describing the change.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    if not file_path.startswith("app/tests/"):
        return "Error: QA agent can only write to app/tests/"
    repo = _get_repo(tool_context.invocation_state)
    resolved = _resolve_path(repo, file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content)
    repo.index.add([file_path])
    repo.index.commit(commit_message)
    logger.info("git_write_tests: committed %s", file_path)
    return f"Committed: {file_path}"


# ---------------------------------------------------------------------------
# Batch write helpers
# ---------------------------------------------------------------------------


def _batch_write(
    files_json: str,
    prefix: str,
    commit_message: str,
    agent_label: str,
    tool_context: ToolContext,
) -> str:
    """Write multiple files in a single commit.

    Args:
        files_json: JSON array of objects with "path" and "content" keys.
        prefix: Required path prefix (e.g. "app/").
        commit_message: Git commit message for all files.
        agent_label: Human label for error messages (e.g. "Dev agent").
        tool_context: Strands tool context (injected by framework).

    Returns:
        Summary of committed files or an error message.
    """
    try:
        files = json.loads(files_json)
    except json.JSONDecodeError as exc:
        return f"Error: invalid JSON — {exc}"

    if not isinstance(files, list) or len(files) == 0:
        return "Error: files_json must be a non-empty JSON array"

    # Validate every path before writing anything.
    for entry in files:
        if not isinstance(entry, dict) or "path" not in entry or "content" not in entry:
            return "Error: each entry must have 'path' and 'content' keys"
        if not entry["path"].startswith(prefix):
            return f"Error: {agent_label} can only write to {prefix} — got {entry['path']}"

    repo = _get_repo(tool_context.invocation_state)
    written_paths: list[str] = []

    for entry in files:
        resolved = _resolve_path(repo, entry["path"])
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(entry["content"])
        written_paths.append(entry["path"])

    repo.index.add(written_paths)
    repo.index.commit(commit_message)
    logger.info("batch_write(%s): committed %d files", prefix, len(written_paths))
    return f"Committed {len(written_paths)} files:\n" + "\n".join(f"  - {p}" for p in written_paths)


@tool(context=True)
def git_write_app_batch(
    files_json: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write multiple files to app/ in the project repo in a single commit.

    Use this instead of calling git_write_app repeatedly when you have several
    files ready at once. Much faster because it makes one commit for all files.

    Args:
        files_json: JSON array of {"path": "app/...", "content": "..."} objects.
        commit_message: Git commit message describing the batch of changes.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Summary of committed files, or an error message.
    """
    return _batch_write(files_json, "app/", commit_message, "Dev agent", tool_context)


@tool(context=True)
def git_write_infra_batch(
    files_json: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write multiple files to infra/ in the project repo in a single commit.

    Use this instead of calling git_write_infra repeatedly when you have several
    files ready at once (e.g. main.tf, variables.tf, outputs.tf for a module).
    Much faster because it makes one commit for all files.

    Args:
        files_json: JSON array of {"path": "infra/...", "content": "..."} objects.
        commit_message: Git commit message describing the batch of changes.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Summary of committed files, or an error message.
    """
    return _batch_write(files_json, "infra/", commit_message, "Infra agent", tool_context)


@tool(context=True)
def git_write_data_batch(
    files_json: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write multiple files to data/ in the project repo in a single commit.

    Use this instead of calling git_write_data repeatedly when you have several
    files ready at once. Much faster because it makes one commit for all files.

    Args:
        files_json: JSON array of {"path": "data/...", "content": "..."} objects.
        commit_message: Git commit message describing the batch of changes.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Summary of committed files, or an error message.
    """
    return _batch_write(files_json, "data/", commit_message, "Data agent", tool_context)


@tool(context=True)
def git_write_tests_batch(
    files_json: str,
    commit_message: str,
    tool_context: ToolContext,
) -> str:
    """Write multiple files to app/tests/ in the project repo in a single commit.

    Use this instead of calling git_write_tests repeatedly when you have several
    test files ready at once. Much faster because it makes one commit for all files.

    Args:
        files_json: JSON array of {"path": "app/tests/...", "content": "..."} objects.
        commit_message: Git commit message describing the batch of changes.
        tool_context: Strands tool context (injected by framework).

    Returns:
        Summary of committed files, or an error message.
    """
    return _batch_write(files_json, "app/tests/", commit_message, "QA agent", tool_context)
