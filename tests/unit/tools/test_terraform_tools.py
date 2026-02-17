"""Tests for src/tools/terraform_tools.py."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.tools.terraform_tools import terraform_validate


@pytest.mark.unit
class TestTerraformValidate:
    """Verify terraform_validate tool."""

    def test_missing_repo_url(self) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {}

        result = terraform_validate("infra/", mock_context)
        assert "Error" in result

    def test_missing_directory(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.terraform_tools._get_repo", return_value=mock_repo):
            result = terraform_validate("nonexistent/", mock_context)

        assert "Error" in result

    def test_terraform_not_found(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with (
            patch("src.tools.terraform_tools._get_repo", return_value=mock_repo),
            patch("src.tools.terraform_tools.subprocess.run", side_effect=FileNotFoundError),
        ):
            result = terraform_validate("infra", mock_context)

        assert "terraform CLI not found" in result

    def test_init_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        failed_init = MagicMock()
        failed_init.returncode = 1
        failed_init.stderr = "init error"

        with (
            patch("src.tools.terraform_tools._get_repo", return_value=mock_repo),
            patch("src.tools.terraform_tools.subprocess.run", return_value=failed_init),
        ):
            result = terraform_validate("infra", mock_context)

        assert "terraform init failed" in result
        assert "init error" in result

    def test_validate_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        success_init = MagicMock()
        success_init.returncode = 0
        failed_validate = MagicMock()
        failed_validate.returncode = 1
        failed_validate.stdout = "validation error"
        failed_validate.stderr = ""

        with (
            patch("src.tools.terraform_tools._get_repo", return_value=mock_repo),
            patch("src.tools.terraform_tools.subprocess.run", side_effect=[success_init, failed_validate]),
        ):
            result = terraform_validate("infra", mock_context)

        assert "terraform validate failed" in result

    def test_validate_success(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        success = MagicMock()
        success.returncode = 0
        success.stdout = "Success! The configuration is valid."

        with (
            patch("src.tools.terraform_tools._get_repo", return_value=mock_repo),
            patch("src.tools.terraform_tools.subprocess.run", return_value=success),
        ):
            result = terraform_validate("infra", mock_context)

        assert "Validation successful" in result

    def test_timeout(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with (
            patch("src.tools.terraform_tools._get_repo", return_value=mock_repo),
            patch(
                "src.tools.terraform_tools.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="terraform", timeout=60),
            ),
        ):
            result = terraform_validate("infra", mock_context)

        assert "timed out" in result
