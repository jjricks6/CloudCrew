"""Git repository operations for the ECS phase runner.

Handles cloning customer repos, pushing artifacts back to remote, and
syncing artifacts to S3. Extracted from __main__.py to stay within the
500-line file limit.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

import boto3

from src.config import AWS_REGION, SOW_BUCKET, TASK_LEDGER_TABLE
from src.state.ledger import read_ledger, update_deliverables
from src.state.secrets import get_github_pat

logger = logging.getLogger(__name__)


def setup_git_repo(project_id: str) -> Path:
    """Set up a git repo for the phase — clone customer repo or create a temp one.

    Args:
        project_id: The project identifier.

    Returns:
        Path to the repo working directory.
    """
    # Try to clone the customer's repo if credentials exist
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
        repo_url = ledger.git_repo_url_customer
        if repo_url:
            pat = get_github_pat(project_id)
            if pat:
                parsed = urlparse(repo_url)
                auth_url = f"https://{pat}@{parsed.hostname}{parsed.path}"
                repo_dir = Path(tempfile.mkdtemp(prefix=f"cloudcrew-{project_id}-"))
                try:
                    subprocess.run(  # noqa: S603
                        ["git", "clone", auth_url, str(repo_dir)],  # noqa: S607
                        check=True,
                        capture_output=True,
                        timeout=120,
                    )
                    # Configure git user for commits
                    subprocess.run(  # noqa: S603
                        ["git", "-C", str(repo_dir), "config", "user.email", "cloudcrew@example.com"],  # noqa: S607
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(  # noqa: S603
                        ["git", "-C", str(repo_dir), "config", "user.name", "CloudCrew"],  # noqa: S607
                        check=True,
                        capture_output=True,
                    )
                    logger.info("Cloned customer repo %s for project=%s", repo_url, project_id)
                    return repo_dir
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    logger.exception(
                        "Failed to clone customer repo %s for project=%s, falling back to temp repo",
                        repo_url,
                        project_id,
                    )
    except Exception:
        logger.exception("Error reading ledger for repo setup, falling back to temp repo")

    # Fallback: create a temporary local repo
    return _create_temp_repo(project_id)


def _create_temp_repo(project_id: str) -> Path:
    """Create an empty temporary git repo.

    Args:
        project_id: The project identifier (used in temp dir name).

    Returns:
        Path to the repo working directory.
    """
    repo_dir = Path(tempfile.mkdtemp(prefix=f"cloudcrew-{project_id}-"))
    subprocess.run(  # noqa: S603
        ["git", "init", str(repo_dir)],  # noqa: S607
        check=True,
        capture_output=True,
    )
    # Configure git user so subsequent commits (e.g., push_to_remote) work
    subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_dir), "config", "user.email", "cloudcrew@example.com"],  # noqa: S607
        check=True,
        capture_output=True,
    )
    subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_dir), "config", "user.name", "CloudCrew"],  # noqa: S607
        check=True,
        capture_output=True,
    )
    subprocess.run(  # noqa: S603
        ["git", "-C", str(repo_dir), "commit", "--allow-empty", "-m", "Initial commit"],  # noqa: S607
        check=True,
        capture_output=True,
    )
    logger.info("Created temp git repo at %s", repo_dir)
    return repo_dir


def push_to_remote(
    project_id: str,
    repo_path: str,
    phase: str,
    *,
    max_retries: int = 3,
    retry_delay: float = 5.0,
) -> None:
    """Push committed artifacts to the customer's remote GitHub repo.

    Non-blocking on failure — logs an error but does not fail the phase.
    The ``git push`` step retries up to ``max_retries`` times on transient
    failures (network errors, rate limits, etc.).

    Args:
        project_id: The project identifier.
        repo_path: Path to the local git repo.
        phase: The phase name (used in commit message).
        max_retries: Maximum push attempts (default 3).
        retry_delay: Seconds between retries (default 5).
    """
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
        repo_url = ledger.git_repo_url_customer
        if not repo_url:
            logger.info("No customer repo URL — skipping push for project=%s", project_id)
            return

        pat = get_github_pat(project_id)
        if not pat:
            logger.warning("No GitHub PAT found — skipping push for project=%s", project_id)
            return

        parsed = urlparse(repo_url)
        auth_url = f"https://{pat}@{parsed.hostname}{parsed.path}"

        # Stage any uncommitted changes and commit them
        subprocess.run(  # noqa: S603
            ["git", "-C", repo_path, "add", "-A"],  # noqa: S607
            check=True,
            capture_output=True,
        )

        status = subprocess.run(  # noqa: S603
            ["git", "-C", repo_path, "status", "--porcelain"],  # noqa: S607
            capture_output=True,
            text=True,
        )
        if status.stdout.strip():
            subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "git",
                    "-C",
                    repo_path,
                    "commit",
                    "-m",
                    f"CloudCrew: {phase} phase deliverables",
                ],
                check=True,
                capture_output=True,
            )

        # Determine the current branch name so we use the correct tracking
        # ref and push refspec (don't assume "main").
        branch_result = subprocess.run(  # noqa: S603
            ["git", "-C", repo_path, "rev-parse", "--abbrev-ref", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
        )
        current_branch = branch_result.stdout.strip()
        if not current_branch or current_branch == "HEAD":
            current_branch = "main"

        # Check for unpushed commits (agents auto-commit, so committed work
        # may exist even when there are no uncommitted changes above).
        # Only skip the push when the log command succeeds AND returns empty —
        # a failed command (e.g., origin/<branch> doesn't exist yet) means
        # this is likely the first push, so we must NOT skip.
        log_result = subprocess.run(  # noqa: S603
            ["git", "-C", repo_path, "log", "--oneline", f"origin/{current_branch}..HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
        )
        if log_result.returncode == 0 and not log_result.stdout.strip():
            logger.info("No changes to push for project=%s, phase=%s", project_id, phase)
            return

        # Push to remote with retry — use explicit refspec to avoid
        # relying on push.default or implicit branch matching.
        for attempt in range(1, max_retries + 1):
            try:
                subprocess.run(  # noqa: S603
                    [  # noqa: S607
                        "git",
                        "-C",
                        repo_path,
                        "push",
                        auth_url,
                        f"HEAD:refs/heads/{current_branch}",
                    ],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
                logger.info(
                    "Pushed %s phase artifacts to %s for project=%s",
                    phase,
                    repo_url,
                    project_id,
                )
                return
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                if attempt < max_retries:
                    logger.warning(
                        "Push attempt %d/%d failed for project=%s, phase=%s — retrying in %.0fs",
                        attempt,
                        max_retries,
                        project_id,
                        phase,
                        retry_delay,
                    )
                    time.sleep(retry_delay)
                else:
                    logger.error(
                        "Push failed after %d attempts for project=%s, phase=%s (non-fatal)",
                        max_retries,
                        project_id,
                        phase,
                    )

    except Exception:
        logger.exception(
            "Failed to push to remote for project=%s, phase=%s (non-fatal)",
            project_id,
            phase,
        )


def sync_artifacts_to_s3(project_id: str, repo_path: str, phase: str = "") -> None:
    """Upload documentation artifacts to S3 and register them as deliverables.

    Only syncs docs/ and security/ to S3 for the dashboard artifact viewer.
    Code artifacts (infra/, app/, data/) live exclusively in the customer's
    GitHub repo and are pushed there by ``push_to_remote``.

    When ``phase`` is provided, synced files are also registered as deliverables
    in the DynamoDB task ledger so the dashboard review UI can display them.

    Args:
        project_id: The project identifier.
        repo_path: Path to the local git repo.
        phase: Phase name (e.g., "ARCHITECTURE"). If provided, deliverables
            are registered in the task ledger for this phase.
    """
    if not SOW_BUCKET:
        logger.warning("SOW_BUCKET not set — skipping artifact sync")
        return

    # Only sync documentation artifacts to S3 — the dashboard artifact viewer
    # displays these during phase review.  Code (infra/, app/, data/) lives
    # exclusively in the customer's GitHub repo and is pushed by push_to_remote.
    s3 = boto3.client("s3", region_name=AWS_REGION)
    repo_root = Path(repo_path)
    allowed = ("docs/", "security/")
    synced_paths: list[str] = []
    for file in repo_root.rglob("*"):
        if not file.is_file() or ".git" in file.parts:
            continue
        rel = str(file.relative_to(repo_root))
        if any(rel.startswith(p) for p in allowed):
            try:
                s3.put_object(
                    Bucket=SOW_BUCKET,
                    Key=f"projects/{project_id}/artifacts/{rel}",
                    Body=file.read_bytes(),
                )
                synced_paths.append(rel)
            except Exception:
                logger.exception("Failed to upload artifact %s", rel)
    logger.info("Synced %d artifacts to S3 for project=%s", len(synced_paths), project_id)

    # Register synced files as deliverables so the review UI can list them
    if phase and synced_paths:
        deliverables = [
            {"name": _path_to_name(p), "git_path": p, "version": "v1.0"}
            for p in sorted(synced_paths)
            # Exclude phase summary — it's added as a separate entry in the UI
            if not p.startswith("docs/phase-summaries/")
        ]
        if deliverables:
            try:
                update_deliverables(TASK_LEDGER_TABLE, project_id, phase, deliverables)
                logger.info(
                    "Registered %d deliverables for phase=%s, project=%s",
                    len(deliverables),
                    phase,
                    project_id,
                )
            except Exception:
                logger.exception(
                    "Failed to register deliverables for phase=%s, project=%s",
                    phase,
                    project_id,
                )


def _path_to_name(git_path: str) -> str:
    """Derive a human-readable artifact name from a git path.

    Examples:
        ``docs/architecture/system-design.md``  → ``System Design``
        ``security/threat-model.md``            → ``Threat Model``

    Args:
        git_path: Relative path within the repo.

    Returns:
        A display-friendly name.
    """
    filename = Path(git_path).stem
    # Convert kebab-case/snake_case to Title Case
    name = filename.replace("-", " ").replace("_", " ")
    return name.title()
