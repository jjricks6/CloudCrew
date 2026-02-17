"""Tests for src/tools/adr_writer.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.tools.adr_writer import _next_adr_number, _slugify, write_adr


@pytest.mark.unit
class TestSlugify:
    """Verify _slugify helper."""

    def test_basic_slugify(self) -> None:
        assert _slugify("Use DynamoDB for state") == "use-dynamodb-for-state"

    def test_special_characters_removed(self) -> None:
        assert _slugify("Use S3 (not EFS)") == "use-s3-not-efs"

    def test_multiple_spaces_collapsed(self) -> None:
        assert _slugify("too   many   spaces") == "too-many-spaces"

    def test_leading_trailing_stripped(self) -> None:
        assert _slugify("  trimmed  ") == "trimmed"


@pytest.mark.unit
class TestNextAdrNumber:
    """Verify _next_adr_number helper."""

    def test_empty_directory(self, tmp_path: Path) -> None:
        assert _next_adr_number(tmp_path) == 1

    def test_no_decisions_directory(self, tmp_path: Path) -> None:
        assert _next_adr_number(tmp_path) == 1

    def test_existing_adrs(self, tmp_path: Path) -> None:
        decisions = tmp_path / "docs" / "architecture" / "decisions"
        decisions.mkdir(parents=True)
        (decisions / "0001-first-decision.md").write_text("adr 1")
        (decisions / "0002-second-decision.md").write_text("adr 2")
        assert _next_adr_number(tmp_path) == 3


@pytest.mark.unit
class TestWriteAdr:
    """Verify write_adr tool."""

    def test_creates_adr_file(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.adr_writer.git.Repo", return_value=mock_repo):
            result = write_adr(
                title="Use DynamoDB for State",
                status="Accepted",
                context="We need a database for task ledger state.",
                decision="Use DynamoDB with on-demand billing.",
                consequences="Lower cost at low scale; limited query flexibility.",
                tool_context=mock_context,
            )

        assert "Committed ADR" in result
        assert "0001-use-dynamodb-for-state.md" in result

        adr_file = tmp_path / "docs" / "architecture" / "decisions" / "0001-use-dynamodb-for-state.md"
        assert adr_file.exists()
        content = adr_file.read_text()
        assert "Use DynamoDB for State" in content
        assert "Accepted" in content
        assert "We need a database" in content

    def test_increments_adr_number(self, tmp_path: Path) -> None:
        decisions = tmp_path / "docs" / "architecture" / "decisions"
        decisions.mkdir(parents=True)
        (decisions / "0001-existing.md").write_text("existing")

        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.adr_writer.git.Repo", return_value=mock_repo):
            result = write_adr(
                title="Second Decision",
                status="Proposed",
                context="Context",
                decision="Decision",
                consequences="Consequences",
                tool_context=mock_context,
            )

        assert "0002-second-decision.md" in result

    def test_commits_with_correct_message(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.adr_writer.git.Repo", return_value=mock_repo):
            write_adr(
                title="My Decision",
                status="Accepted",
                context="ctx",
                decision="dec",
                consequences="con",
                tool_context=mock_context,
            )

        mock_repo.index.add.assert_called_once()
        commit_msg = mock_repo.index.commit.call_args[0][0]
        assert "ADR 0001" in commit_msg
        assert "My Decision" in commit_msg
