"""ADR (Architecture Decision Record) generation tool.

Formats ADRs using the Nygard template and writes them to the project repo.
This module imports from state/ and templates/ — NEVER from agents/.
"""

import logging
import re
from pathlib import Path
from typing import Any

import git
from strands import tool
from strands.types.tools import ToolContext

from src.templates import load_template

logger = logging.getLogger(__name__)

ADR_DIRECTORY = "docs/architecture/decisions"


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Args:
        text: Input text to slugify.

    Returns:
        Lowercased, hyphen-separated slug.
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    return re.sub(r"[-\s]+", "-", slug).strip("-")


def _next_adr_number(repo_root: Path) -> int:
    """Determine the next ADR sequence number.

    Args:
        repo_root: Root directory of the git repo.

    Returns:
        Next available ADR number (1-based).
    """
    decisions_dir = repo_root / ADR_DIRECTORY
    if not decisions_dir.exists():
        return 1
    existing = sorted(decisions_dir.glob("*.md"))
    if not existing:
        return 1
    # Extract number from filenames like "0001-some-title.md"
    for adr_file in reversed(existing):
        match = re.match(r"(\d+)", adr_file.name)
        if match:
            return int(match.group(1)) + 1
    return 1


def _get_repo(invocation_state: dict[str, Any]) -> git.Repo:
    """Open the project Git repo from invocation_state.

    Args:
        invocation_state: Agent invocation state containing git_repo_url.

    Returns:
        A GitPython Repo object.

    Raises:
        ValueError: If git_repo_url is not set.
    """
    repo_path = invocation_state.get("git_repo_url", "")
    if not repo_path:
        msg = "git_repo_url not set in invocation_state"
        raise ValueError(msg)
    return git.Repo(str(repo_path))


@tool(context=True)
def write_adr(
    title: str,
    status: str,
    context: str,
    decision: str,
    consequences: str,
    tool_context: ToolContext,
) -> str:
    """Create an Architecture Decision Record in the project repo.

    Generates a numbered ADR file using the Nygard template and commits it
    to docs/architecture/decisions/.

    Args:
        title: Short descriptive title for the ADR.
        status: Status of the decision (Proposed, Accepted, Deprecated, Superseded).
        context: What is the issue being addressed?
        decision: What is the change being proposed or done?
        consequences: What becomes easier or harder because of this?
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    repo = _get_repo(tool_context.invocation_state)
    repo_root = Path(repo.working_dir)
    template = load_template("adr.md")
    content = template.format(
        title=title,
        status=status,
        context=context,
        decision=decision,
        consequences=consequences,
    )

    number = _next_adr_number(repo_root)
    slug = _slugify(title)
    filename = f"{number:04d}-{slug}.md"
    relative_path = f"{ADR_DIRECTORY}/{filename}"

    absolute_path = repo_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(content)

    repo.index.add([relative_path])
    repo.index.commit(f"docs: add ADR {number:04d} — {title}")

    logger.info("write_adr: committed %s", relative_path)
    return f"Committed ADR: {relative_path}"
