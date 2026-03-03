"""Tests for src/tools/git_auth_tools.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.tools.git_auth_tools import _build_auth_url


@pytest.mark.unit
class TestBuildAuthUrl:
    """Verify _build_auth_url helper."""

    def test_inserts_pat_into_https_url(self) -> None:
        result = _build_auth_url("https://github.com/org/repo", "ghp_abc123")
        assert result == "https://ghp_abc123@github.com/org/repo"

    def test_handles_trailing_dot_git(self) -> None:
        result = _build_auth_url("https://github.com/org/repo.git", "ghp_abc")
        assert result == "https://ghp_abc@github.com/org/repo.git"

    def test_raises_on_non_https(self) -> None:
        with pytest.raises(ValueError, match="Invalid HTTPS URL"):
            _build_auth_url("http://github.com/org/repo", "ghp_abc")

    def test_raises_on_ssh_url(self) -> None:
        with pytest.raises(ValueError, match="Invalid HTTPS URL"):
            _build_auth_url("git@github.com:org/repo.git", "ghp_abc")


@pytest.mark.unit
class TestStoreGitCredentials:
    """Verify store_git_credentials tool."""

    @patch("src.tools.git_auth_tools.write_ledger")
    @patch("src.tools.git_auth_tools.read_ledger")
    @patch("src.tools.git_auth_tools.store_github_pat")
    def test_stores_pat_and_updates_ledger(
        self,
        mock_store_pat: MagicMock,
        mock_read_ledger: MagicMock,
        mock_write_ledger: MagicMock,
    ) -> None:
        from src.state.models import TaskLedger
        from src.tools.git_auth_tools import store_git_credentials

        mock_store_pat.return_value = True
        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = store_git_credentials(
            repo_url="https://github.com/org/repo",
            github_pat="ghp_test123456",
            tool_context=ctx,
        )

        assert "successfully" in result
        mock_store_pat.assert_called_once_with("proj-1", "ghp_test123456")
        mock_write_ledger.assert_called_once()
        written_ledger = mock_write_ledger.call_args[0][2]
        assert written_ledger.git_repo_url_customer == "https://github.com/org/repo"

    @patch("src.tools.git_auth_tools.store_github_pat")
    def test_rejects_non_https_url(self, mock_store: MagicMock) -> None:
        from src.tools.git_auth_tools import store_git_credentials

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = store_git_credentials(
            repo_url="git@github.com:org/repo.git",
            github_pat="ghp_test123456",
            tool_context=ctx,
        )

        assert "HTTPS" in result
        mock_store.assert_not_called()

    @patch("src.tools.git_auth_tools.store_github_pat")
    def test_rejects_short_pat(self, mock_store: MagicMock) -> None:
        from src.tools.git_auth_tools import store_git_credentials

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = store_git_credentials(
            repo_url="https://github.com/org/repo",
            github_pat="short",
            tool_context=ctx,
        )

        assert "Invalid GitHub PAT" in result
        mock_store.assert_not_called()

    @patch("src.tools.git_auth_tools.store_github_pat")
    def test_handles_pat_store_failure(self, mock_store: MagicMock) -> None:
        from src.tools.git_auth_tools import store_git_credentials

        mock_store.return_value = False
        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = store_git_credentials(
            repo_url="https://github.com/org/repo",
            github_pat="ghp_test123456",
            tool_context=ctx,
        )

        assert "Failed to store" in result

    def test_errors_without_project_id(self) -> None:
        from src.tools.git_auth_tools import store_git_credentials

        ctx = MagicMock()
        ctx.invocation_state = {}

        result = store_git_credentials(
            repo_url="https://github.com/org/repo",
            github_pat="ghp_test123456",
            tool_context=ctx,
        )

        assert "project_id" in result

    @patch("src.tools.git_auth_tools.write_ledger")
    @patch("src.tools.git_auth_tools.read_ledger")
    @patch("src.tools.git_auth_tools.store_github_pat")
    def test_strips_trailing_slash_from_url(
        self,
        mock_store_pat: MagicMock,
        mock_read_ledger: MagicMock,
        mock_write_ledger: MagicMock,
    ) -> None:
        from src.state.models import TaskLedger
        from src.tools.git_auth_tools import store_git_credentials

        mock_store_pat.return_value = True
        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        store_git_credentials(
            repo_url="https://github.com/org/repo/",
            github_pat="ghp_test123456",
            tool_context=ctx,
        )

        written_ledger = mock_write_ledger.call_args[0][2]
        assert written_ledger.git_repo_url_customer == "https://github.com/org/repo"


@pytest.mark.unit
class TestVerifyGitAccess:
    """Verify verify_git_access tool."""

    @patch("src.tools.git_auth_tools.subprocess")
    @patch("src.tools.git_auth_tools.get_github_pat")
    @patch("src.tools.git_auth_tools.read_ledger")
    def test_verifies_access_successfully(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from src.state.models import TaskLedger
        from src.tools.git_auth_tools import verify_git_access

        ledger = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_read_ledger.return_value = ledger
        mock_get_pat.return_value = "ghp_test123"

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "abc123\trefs/heads/main\n"
        mock_subprocess.run.return_value = mock_result

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = verify_git_access(tool_context=ctx)

        assert "verified" in result.lower()
        assert "1 branch" in result

    @patch("src.tools.git_auth_tools.get_github_pat")
    @patch("src.tools.git_auth_tools.read_ledger")
    def test_errors_when_no_repo_url(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
    ) -> None:
        from src.state.models import TaskLedger
        from src.tools.git_auth_tools import verify_git_access

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = verify_git_access(tool_context=ctx)

        assert "No repository URL" in result
        mock_get_pat.assert_not_called()

    @patch("src.tools.git_auth_tools.get_github_pat")
    @patch("src.tools.git_auth_tools.read_ledger")
    def test_errors_when_no_pat(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
    ) -> None:
        from src.state.models import TaskLedger
        from src.tools.git_auth_tools import verify_git_access

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = ""

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = verify_git_access(tool_context=ctx)

        assert "No GitHub PAT" in result

    @patch("src.tools.git_auth_tools.subprocess")
    @patch("src.tools.git_auth_tools.get_github_pat")
    @patch("src.tools.git_auth_tools.read_ledger")
    def test_handles_git_ls_remote_failure(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from src.state.models import TaskLedger
        from src.tools.git_auth_tools import verify_git_access

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_bad_token"

        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stderr = "fatal: Authentication failed"
        mock_subprocess.run.return_value = mock_result

        ctx = MagicMock()
        ctx.invocation_state = {"project_id": "proj-1"}

        result = verify_git_access(tool_context=ctx)

        assert "Cannot access" in result
        assert "Authentication failed" in result
