"""Tests for src/tools/git_tools.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.tools.git_tools import (
    _get_repo,
    _resolve_path,
    git_list,
    git_read,
    git_write_architecture,
    git_write_infra,
    git_write_project_plan,
    git_write_security,
)


@pytest.mark.unit
class TestGetRepo:
    """Verify _get_repo helper."""

    def test_missing_repo_url_raises(self) -> None:
        with pytest.raises(ValueError, match="git_repo_url not set"):
            _get_repo({})

    def test_empty_repo_url_raises(self) -> None:
        with pytest.raises(ValueError, match="git_repo_url not set"):
            _get_repo({"git_repo_url": ""})

    @patch("src.tools.git_tools.git.Repo")
    def test_valid_repo_url(self, mock_repo_cls: MagicMock) -> None:
        mock_repo_cls.return_value = MagicMock()
        repo = _get_repo({"git_repo_url": "/tmp/test-repo"})
        mock_repo_cls.assert_called_once_with("/tmp/test-repo")
        assert repo is not None


@pytest.mark.unit
class TestResolvePath:
    """Verify _resolve_path helper."""

    def test_path_escape_raises(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        with pytest.raises(ValueError, match="Path escapes repository"):
            _resolve_path(mock_repo, "../../etc/passwd")

    def test_normal_path_resolves(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        result = _resolve_path(mock_repo, "docs/architecture/doc.md")
        assert str(result).startswith(str(tmp_path))


@pytest.mark.unit
class TestGitRead:
    """Verify git_read tool."""

    def test_read_existing_file(self, tmp_path: Path) -> None:
        (tmp_path / "test.txt").write_text("hello world")
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_read("test.txt", mock_context)

        assert result == "hello world"

    def test_read_missing_file(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_read("nonexistent.txt", mock_context)

        assert "Error: file not found" in result


@pytest.mark.unit
class TestGitList:
    """Verify git_list tool."""

    def test_list_directory(self, tmp_path: Path) -> None:
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "a.md").write_text("a")
        (docs_dir / "b.md").write_text("b")

        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_list("docs", mock_context)

        assert "docs/a.md" in result
        assert "docs/b.md" in result

    def test_list_missing_directory(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_list("nonexistent", mock_context)

        assert "Error: directory not found" in result

    def test_list_file_not_directory(self, tmp_path: Path) -> None:
        (tmp_path / "file.txt").write_text("data")
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_list("file.txt", mock_context)

        assert "Error: not a directory" in result


@pytest.mark.unit
class TestGitWriteArchitecture:
    """Verify git_write_architecture tool."""

    def test_rejects_non_architecture_path(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_architecture("infra/main.tf", "content", "msg", mock_context)
        assert "Error" in result

    def test_writes_and_commits(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_architecture(
                "docs/architecture/design.md",
                "# Design Doc",
                "docs: add design doc",
                mock_context,
            )

        assert "Committed" in result
        written_file = tmp_path / "docs" / "architecture" / "design.md"
        assert written_file.exists()
        assert written_file.read_text() == "# Design Doc"
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("docs: add design doc")


@pytest.mark.unit
class TestGitWriteInfra:
    """Verify git_write_infra tool."""

    def test_rejects_non_infra_path(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_infra("docs/readme.md", "content", "msg", mock_context)
        assert "Error" in result

    def test_writes_and_commits(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_infra(
                "infra/modules/vpc/main.tf",
                'resource "aws_vpc" "main" {}',
                "infra: add vpc module",
                mock_context,
            )

        assert "Committed" in result
        written_file = tmp_path / "infra" / "modules" / "vpc" / "main.tf"
        assert written_file.exists()
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("infra: add vpc module")

    def test_accepts_nested_infra_path(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_infra(
                "infra/modules/rds/variables.tf",
                'variable "db_name" {}',
                "infra: add rds variables",
                mock_context,
            )

        assert "Committed" in result


@pytest.mark.unit
class TestGitWriteSecurity:
    """Verify git_write_security tool."""

    def test_rejects_non_security_path(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_security("infra/main.tf", "content", "msg", mock_context)
        assert "Error" in result

    def test_writes_and_commits(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_security(
                "security/reviews/report.md",
                "# Security Report",
                "security: add review",
                mock_context,
            )

        assert "Committed" in result
        written_file = tmp_path / "security" / "reviews" / "report.md"
        assert written_file.exists()
        assert written_file.read_text() == "# Security Report"
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("security: add review")

    def test_accepts_nested_security_path(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_security(
                "security/policies/iam-review.md",
                "# IAM Review",
                "security: add iam review",
                mock_context,
            )

        assert "Committed" in result


@pytest.mark.unit
class TestGitWriteProjectPlan:
    """Verify git_write_project_plan tool."""

    def test_rejects_non_project_plan_path(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_project_plan("infra/main.tf", "content", "msg", mock_context)
        assert "Error" in result

    def test_writes_and_commits(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_project_plan(
                "docs/project-plan/plan.md",
                "# Project Plan",
                "docs: add project plan",
                mock_context,
            )

        assert "Committed" in result
        written_file = tmp_path / "docs" / "project-plan" / "plan.md"
        assert written_file.exists()
        assert written_file.read_text() == "# Project Plan"
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("docs: add project plan")

    def test_accepts_nested_project_plan_path(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_project_plan(
                "docs/project-plan/phases/discovery.md",
                "# Discovery Phase",
                "docs: add discovery phase plan",
                mock_context,
            )

        assert "Committed" in result
