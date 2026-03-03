"""Tests for src/tools/phase_summary_tools.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.tools.phase_summary_tools import git_write_phase_summary


def _make_tool_context(
    repo_path: str,
    phase: str = "architecture",
) -> MagicMock:
    """Create a mock ToolContext with invocation_state."""
    ctx = MagicMock()
    ctx.invocation_state = {
        "git_repo_url": repo_path,
        "phase": phase,
    }
    return ctx


@pytest.mark.unit
class TestGitWritePhaseSummary:
    """Verify git_write_phase_summary behaviour."""

    def test_rejects_path_outside_phase_summaries(self) -> None:
        ctx = _make_tool_context("/tmp/repo")
        result = git_write_phase_summary(
            file_path="docs/architecture/design.md",
            content="# Design",
            commit_message="add design",
            tool_context=ctx,
        )
        assert "Error" in result

    @patch("src.tools.phase_summary_tools._get_repo")
    def test_writes_canonical_filename(
        self,
        mock_get_repo: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Agent passes 'architecture-phase.md' but tool normalizes to 'architecture.md'."""
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_get_repo.return_value = mock_repo

        ctx = _make_tool_context(str(tmp_path), phase="architecture")

        result = git_write_phase_summary(
            file_path="docs/phase-summaries/architecture-phase.md",
            content="# Architecture Summary",
            commit_message="add phase summary",
            tool_context=ctx,
        )

        assert "Committed" in result
        # File should be at canonical path, not the agent-provided path
        canonical = tmp_path / "docs" / "phase-summaries" / "architecture.md"
        assert canonical.exists()
        assert canonical.read_text() == "# Architecture Summary"

        # Agent-provided path should NOT exist
        agent_path = tmp_path / "docs" / "phase-summaries" / "architecture-phase.md"
        assert not agent_path.exists()

        # Git operations used canonical path
        mock_repo.index.add.assert_called_once_with(["docs/phase-summaries/architecture.md"])

    @patch("src.tools.phase_summary_tools._get_repo")
    def test_preserves_correct_filename(
        self,
        mock_get_repo: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Agent passes correct filename — no normalization needed."""
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_get_repo.return_value = mock_repo

        ctx = _make_tool_context(str(tmp_path), phase="discovery")

        result = git_write_phase_summary(
            file_path="docs/phase-summaries/discovery.md",
            content="# Discovery Summary",
            commit_message="add summary",
            tool_context=ctx,
        )

        assert "Committed" in result
        canonical = tmp_path / "docs" / "phase-summaries" / "discovery.md"
        assert canonical.exists()

    @patch("src.tools.phase_summary_tools._get_repo")
    def test_falls_back_when_no_phase_in_state(
        self,
        mock_get_repo: MagicMock,
        tmp_path: Path,
    ) -> None:
        """If phase is missing from invocation_state, use the agent-provided path."""
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_get_repo.return_value = mock_repo

        ctx = _make_tool_context(str(tmp_path), phase="")

        result = git_write_phase_summary(
            file_path="docs/phase-summaries/custom-name.md",
            content="# Custom",
            commit_message="add summary",
            tool_context=ctx,
        )

        assert "Committed" in result
        custom = tmp_path / "docs" / "phase-summaries" / "custom-name.md"
        assert custom.exists()
