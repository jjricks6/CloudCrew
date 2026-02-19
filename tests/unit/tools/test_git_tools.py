"""Tests for src/tools/git_tools.py."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.tools.git_tools import (
    _get_repo,
    _resolve_path,
    git_list,
    git_read,
    git_write_app,
    git_write_app_batch,
    git_write_architecture,
    git_write_data,
    git_write_data_batch,
    git_write_infra,
    git_write_infra_batch,
    git_write_project_plan,
    git_write_security,
    git_write_tests,
    git_write_tests_batch,
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

        assert "does not exist yet" in result

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


@pytest.mark.unit
class TestGitWriteApp:
    """Verify git_write_app tool."""

    def test_rejects_non_app_path(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_app("infra/main.tf", "content", "msg", mock_context)
        assert "Error" in result

    def test_writes_and_commits(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_app(
                "app/src/main.py",
                "print('hello')",
                "feat: add main entry point",
                mock_context,
            )

        assert "Committed" in result
        written_file = tmp_path / "app" / "src" / "main.py"
        assert written_file.exists()
        assert written_file.read_text() == "print('hello')"
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("feat: add main entry point")


@pytest.mark.unit
class TestGitWriteData:
    """Verify git_write_data tool."""

    def test_rejects_non_data_path(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_data("app/main.py", "content", "msg", mock_context)
        assert "Error" in result

    def test_writes_and_commits(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_data(
                "data/schemas/users.sql",
                "CREATE TABLE users (id INT);",
                "data: add users schema",
                mock_context,
            )

        assert "Committed" in result
        written_file = tmp_path / "data" / "schemas" / "users.sql"
        assert written_file.exists()
        assert written_file.read_text() == "CREATE TABLE users (id INT);"
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("data: add users schema")


@pytest.mark.unit
class TestGitWriteTests:
    """Verify git_write_tests tool."""

    def test_rejects_non_tests_path(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_tests("app/src/main.py", "content", "msg", mock_context)
        assert "Error" in result

    def test_rejects_app_without_tests(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_tests("app/main.py", "content", "msg", mock_context)
        assert "Error" in result

    def test_writes_and_commits(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_tests(
                "app/tests/test_main.py",
                "def test_hello(): assert True",
                "test: add main tests",
                mock_context,
            )

        assert "Committed" in result
        written_file = tmp_path / "app" / "tests" / "test_main.py"
        assert written_file.exists()
        assert written_file.read_text() == "def test_hello(): assert True"
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("test: add main tests")


# ---------------------------------------------------------------------------
# Batch write tool tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGitWriteAppBatch:
    """Verify git_write_app_batch tool."""

    def test_rejects_non_app_path(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps([{"path": "infra/main.tf", "content": "bad"}])
        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_app_batch(files, "msg", mock_context)
        assert "Error" in result

    def test_writes_multiple_files_single_commit(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps(
            [
                {"path": "app/src/main.py", "content": "print('hello')"},
                {"path": "app/src/config.py", "content": "DEBUG = True"},
                {"path": "app/requirements.txt", "content": "flask>=3.0"},
            ]
        )

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_app_batch(files, "feat: add app scaffolding", mock_context)

        assert "Committed 3 files" in result
        assert (tmp_path / "app" / "src" / "main.py").read_text() == "print('hello')"
        assert (tmp_path / "app" / "src" / "config.py").read_text() == "DEBUG = True"
        assert (tmp_path / "app" / "requirements.txt").read_text() == "flask>=3.0"
        mock_repo.index.add.assert_called_once()
        mock_repo.index.commit.assert_called_once_with("feat: add app scaffolding")

    def test_rejects_invalid_json(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_app_batch("not json", "msg", mock_context)
        assert "Error: invalid JSON" in result

    def test_rejects_empty_array(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        result = git_write_app_batch("[]", "msg", mock_context)
        assert "Error" in result

    def test_rejects_missing_keys(self, tmp_path: Path) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps([{"path": "app/foo.py"}])
        result = git_write_app_batch(files, "msg", mock_context)
        assert "Error" in result

    def test_no_files_written_if_any_path_invalid(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps(
            [
                {"path": "app/good.py", "content": "ok"},
                {"path": "infra/bad.tf", "content": "nope"},
            ]
        )
        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_app_batch(files, "msg", mock_context)

        assert "Error" in result
        assert not (tmp_path / "app" / "good.py").exists()


@pytest.mark.unit
class TestGitWriteInfraBatch:
    """Verify git_write_infra_batch tool."""

    def test_rejects_non_infra_path(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps([{"path": "app/main.py", "content": "bad"}])
        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_infra_batch(files, "msg", mock_context)
        assert "Error" in result

    def test_writes_module_files_single_commit(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps(
            [
                {"path": "infra/modules/vpc/main.tf", "content": 'resource "aws_vpc" "main" {}'},
                {"path": "infra/modules/vpc/variables.tf", "content": 'variable "cidr" {}'},
                {"path": "infra/modules/vpc/outputs.tf", "content": 'output "vpc_id" {}'},
            ]
        )

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_infra_batch(files, "infra: add vpc module", mock_context)

        assert "Committed 3 files" in result
        assert (tmp_path / "infra" / "modules" / "vpc" / "main.tf").exists()
        assert (tmp_path / "infra" / "modules" / "vpc" / "variables.tf").exists()
        assert (tmp_path / "infra" / "modules" / "vpc" / "outputs.tf").exists()
        mock_repo.index.commit.assert_called_once_with("infra: add vpc module")


@pytest.mark.unit
class TestGitWriteDataBatch:
    """Verify git_write_data_batch tool."""

    def test_rejects_non_data_path(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps([{"path": "app/main.py", "content": "bad"}])
        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_data_batch(files, "msg", mock_context)
        assert "Error" in result

    def test_writes_multiple_schemas(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps(
            [
                {"path": "data/schemas/users.sql", "content": "CREATE TABLE users (id INT);"},
                {"path": "data/schemas/orders.sql", "content": "CREATE TABLE orders (id INT);"},
            ]
        )

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_data_batch(files, "data: add schemas", mock_context)

        assert "Committed 2 files" in result
        assert (tmp_path / "data" / "schemas" / "users.sql").exists()
        assert (tmp_path / "data" / "schemas" / "orders.sql").exists()
        mock_repo.index.commit.assert_called_once_with("data: add schemas")


@pytest.mark.unit
class TestGitWriteTestsBatch:
    """Verify git_write_tests_batch tool."""

    def test_rejects_non_tests_path(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps([{"path": "app/src/main.py", "content": "bad"}])
        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_tests_batch(files, "msg", mock_context)
        assert "Error" in result

    def test_writes_multiple_test_files(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        files = json.dumps(
            [
                {"path": "app/tests/test_health.py", "content": "def test_health(): pass"},
                {"path": "app/tests/test_auth.py", "content": "def test_auth(): pass"},
                {"path": "app/tests/test_api.py", "content": "def test_api(): pass"},
            ]
        )

        with patch("src.tools.git_tools.git.Repo", return_value=mock_repo):
            result = git_write_tests_batch(files, "test: add test suite", mock_context)

        assert "Committed 3 files" in result
        assert (tmp_path / "app" / "tests" / "test_health.py").exists()
        assert (tmp_path / "app" / "tests" / "test_auth.py").exists()
        assert (tmp_path / "app" / "tests" / "test_api.py").exists()
        mock_repo.index.commit.assert_called_once_with("test: add test suite")
