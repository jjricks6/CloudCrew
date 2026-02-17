"""Security review report generation tool.

Creates structured security review reports using a template and commits
them to the project repository under security/reviews/.

This module imports from templates/ and tools/ — NEVER from agents/.
"""

import datetime
import logging
import re
from pathlib import Path
from typing import Any

import git
from strands import tool
from strands.types.tools import ToolContext

from src.templates import load_template

logger = logging.getLogger(__name__)

SECURITY_REVIEW_DIRECTORY = "security/reviews"


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
def write_security_review(
    title: str,
    scope: str,
    verdict: str,
    critical_count: int,
    high_count: int,
    medium_count: int,
    low_count: int,
    findings: str,
    recommendations: str,
    tool_context: ToolContext,
) -> str:
    """Create a security review report and commit it to the project repo.

    Generates a dated security review file using the security_review template
    and commits it to security/reviews/.

    Args:
        title: Short descriptive title for the review.
        scope: What was reviewed (e.g., "infra/modules/vpc").
        verdict: Overall verdict (PASS, FAIL, CONDITIONAL_PASS).
        critical_count: Number of critical severity findings.
        high_count: Number of high severity findings.
        medium_count: Number of medium severity findings.
        low_count: Number of low severity findings.
        findings: Detailed findings text (markdown).
        recommendations: Remediation recommendations (markdown).
        tool_context: Strands tool context (injected by framework).

    Returns:
        Success message with the committed file path, or an error message.
    """
    repo = _get_repo(tool_context.invocation_state)
    repo_root = Path(repo.working_dir)
    template = load_template("security_review.md")

    today = datetime.datetime.now(tz=datetime.UTC).strftime("%Y-%m-%d")
    content = template.format(
        title=title,
        date=today,
        scope=scope,
        verdict=verdict,
        critical_count=critical_count,
        high_count=high_count,
        medium_count=medium_count,
        low_count=low_count,
        findings=findings,
        recommendations=recommendations,
    )

    date_prefix = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d")
    slug = _slugify(title)
    filename = f"{date_prefix}-{slug}.md"
    relative_path = f"{SECURITY_REVIEW_DIRECTORY}/{filename}"

    absolute_path = repo_root / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_text(content)

    repo.index.add([relative_path])
    repo.index.commit(f"security: add review — {title}")

    logger.info("write_security_review: committed %s", relative_path)
    return f"Committed security review: {relative_path}"
