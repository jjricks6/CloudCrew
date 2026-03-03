"""Tests for src/phases/git_ops.py."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.state.models import TaskLedger


@pytest.mark.unit
class TestSetupGitRepo:
    """Verify setup_git_repo clones or creates temp repo."""

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_clones_customer_repo_when_credentials_exist(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import setup_git_repo

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        with patch("src.phases.git_ops.tempfile.mkdtemp", return_value=str(tmp_path)):
            result = setup_git_repo("proj-1")

        assert result == tmp_path
        # Should have called git clone, then config user.email, then config user.name
        assert mock_subprocess.run.call_count == 3
        clone_call = mock_subprocess.run.call_args_list[0]
        assert "clone" in clone_call[0][0]

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_falls_back_to_temp_when_no_repo_url(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import setup_git_repo

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")

        with patch("src.phases.git_ops.tempfile.mkdtemp", return_value=str(tmp_path)):
            result = setup_git_repo("proj-1")

        assert result == tmp_path
        mock_get_pat.assert_not_called()
        # Should have called git init, config user.email, config user.name, commit --allow-empty
        assert mock_subprocess.run.call_count == 4
        init_call = mock_subprocess.run.call_args_list[0]
        assert "init" in init_call[0][0]

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_falls_back_to_temp_when_no_pat(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import setup_git_repo

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = ""

        with patch("src.phases.git_ops.tempfile.mkdtemp", return_value=str(tmp_path)):
            result = setup_git_repo("proj-1")

        assert result == tmp_path
        # Fell back to init + config email + config name + commit
        assert mock_subprocess.run.call_count == 4

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_falls_back_on_clone_failure(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
        tmp_path: Path,
    ) -> None:
        import subprocess

        from src.phases.git_ops import setup_git_repo

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        # Clone fails, then init + commit succeed
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise subprocess.CalledProcessError(128, "git clone")
            return MagicMock()

        mock_subprocess.run.side_effect = side_effect
        mock_subprocess.CalledProcessError = subprocess.CalledProcessError
        mock_subprocess.TimeoutExpired = subprocess.TimeoutExpired

        with patch("src.phases.git_ops.tempfile.mkdtemp", return_value=str(tmp_path)):
            result = setup_git_repo("proj-1")

        assert result == tmp_path


@pytest.mark.unit
class TestPushToRemote:
    """Verify push_to_remote behavior."""

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_pushes_when_uncommitted_changes_exist(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        # git add, git status (has changes), git commit, rev-parse, git log, git push
        status_result = MagicMock()
        status_result.stdout = "M docs/sow.md\n"
        branch_result = MagicMock()
        branch_result.stdout = "main"
        log_result = MagicMock()
        log_result.stdout = "abc1234 CloudCrew: ARCHITECTURE phase deliverables\n"
        log_result.returncode = 0
        mock_subprocess.run.side_effect = [
            MagicMock(),  # git add
            status_result,  # git status (uncommitted changes)
            MagicMock(),  # git commit
            branch_result,  # git rev-parse --abbrev-ref HEAD
            log_result,  # git log (unpushed commits)
            MagicMock(),  # git push
        ]

        push_to_remote("proj-1", "/tmp/repo", "ARCHITECTURE")

        assert mock_subprocess.run.call_count == 6

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_pushes_pre_committed_changes(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """Agents auto-commit, so push_to_remote must detect unpushed commits."""
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        # No uncommitted changes, but there ARE unpushed commits
        status_result = MagicMock()
        status_result.stdout = ""
        branch_result = MagicMock()
        branch_result.stdout = "main"
        log_result = MagicMock()
        log_result.stdout = "abc1234 feat: add PoC app\ndef5678 feat: add tests\n"
        log_result.returncode = 0
        mock_subprocess.run.side_effect = [
            MagicMock(),  # git add
            status_result,  # git status (clean)
            branch_result,  # git rev-parse --abbrev-ref HEAD
            log_result,  # git log (unpushed commits)
            MagicMock(),  # git push
        ]

        push_to_remote("proj-1", "/tmp/repo", "POC")

        # No commit step (nothing to commit), but push still happens
        assert mock_subprocess.run.call_count == 5

    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_skips_when_no_repo_url(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
    ) -> None:
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(project_id="proj-1")

        # Should not raise
        push_to_remote("proj-1", "/tmp/repo", "DISCOVERY")
        mock_get_pat.assert_not_called()

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_skips_when_no_changes(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        # git add succeeds, git status shows no changes, git log shows no unpushed commits
        status_result = MagicMock()
        status_result.stdout = ""
        branch_result = MagicMock()
        branch_result.stdout = "main"
        log_result = MagicMock()
        log_result.stdout = ""
        log_result.returncode = 0
        mock_subprocess.run.side_effect = [
            MagicMock(),  # git add
            status_result,  # git status (empty)
            branch_result,  # git rev-parse --abbrev-ref HEAD
            log_result,  # git log (no unpushed commits, returncode=0)
        ]

        push_to_remote("proj-1", "/tmp/repo", "ARCHITECTURE")

        # Should not attempt commit or push (add + status + rev-parse + log = 4)
        assert mock_subprocess.run.call_count == 4

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_does_not_raise_on_push_failure(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"
        mock_subprocess.run.side_effect = RuntimeError("Push failed")

        # Should not raise — logs and returns
        push_to_remote("proj-1", "/tmp/repo", "POC")

    @patch("src.phases.git_ops.time")
    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_retries_push_on_failure(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        """Push retries on CalledProcessError and succeeds on second attempt."""
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        status_result = MagicMock()
        status_result.stdout = ""
        branch_result = MagicMock()
        branch_result.stdout = "main"
        log_result = MagicMock()
        log_result.stdout = "abc1234 feat: add PoC\n"
        log_result.returncode = 0
        push_error = subprocess.CalledProcessError(1, "git push")

        mock_subprocess.run.side_effect = [
            MagicMock(),  # git add
            status_result,  # git status (clean)
            branch_result,  # git rev-parse --abbrev-ref HEAD
            log_result,  # git log (has unpushed commits)
            push_error,  # first push fails
            MagicMock(),  # second push succeeds
        ]
        mock_subprocess.CalledProcessError = subprocess.CalledProcessError
        mock_subprocess.TimeoutExpired = subprocess.TimeoutExpired

        push_to_remote("proj-1", "/tmp/repo", "POC", max_retries=3, retry_delay=0.0)

        # 6 calls: add, status, rev-parse, log, push (fail), push (succeed)
        assert mock_subprocess.run.call_count == 6
        mock_time.sleep.assert_called_once_with(0.0)

    @patch("src.phases.git_ops.time")
    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_push_gives_up_after_max_retries(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        """Push logs error after all retries exhausted (does not raise)."""
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        status_result = MagicMock()
        status_result.stdout = ""
        branch_result = MagicMock()
        branch_result.stdout = "main"
        log_result = MagicMock()
        log_result.stdout = "abc1234 feat: add PoC\n"
        log_result.returncode = 0
        push_error = subprocess.CalledProcessError(1, "git push")

        mock_subprocess.run.side_effect = [
            MagicMock(),  # git add
            status_result,  # git status (clean)
            branch_result,  # git rev-parse --abbrev-ref HEAD
            log_result,  # git log (has unpushed commits)
            push_error,  # push attempt 1
            push_error,  # push attempt 2
        ]
        mock_subprocess.CalledProcessError = subprocess.CalledProcessError
        mock_subprocess.TimeoutExpired = subprocess.TimeoutExpired

        # Should not raise — logs error and returns
        push_to_remote("proj-1", "/tmp/repo", "POC", max_retries=2, retry_delay=0.0)

        # 6 calls: add, status, rev-parse, log, push (fail), push (fail)
        assert mock_subprocess.run.call_count == 6
        mock_time.sleep.assert_called_once_with(0.0)

    @patch("src.phases.git_ops.subprocess")
    @patch("src.phases.git_ops.get_github_pat")
    @patch("src.phases.git_ops.read_ledger", new_callable=MagicMock)
    def test_pushes_when_origin_branch_missing(
        self,
        mock_read_ledger: MagicMock,
        mock_get_pat: MagicMock,
        mock_subprocess: MagicMock,
    ) -> None:
        """First push to an empty repo — origin/main doesn't exist yet."""
        from src.phases.git_ops import push_to_remote

        mock_read_ledger.return_value = TaskLedger(
            project_id="proj-1",
            git_repo_url_customer="https://github.com/org/repo",
        )
        mock_get_pat.return_value = "ghp_test123"

        status_result = MagicMock()
        status_result.stdout = ""
        branch_result = MagicMock()
        branch_result.stdout = "main"
        # git log origin/main..HEAD fails because origin/main doesn't exist
        log_result = MagicMock()
        log_result.stdout = ""
        log_result.returncode = 128  # fatal: bad revision 'origin/main..HEAD'

        mock_subprocess.run.side_effect = [
            MagicMock(),  # git add
            status_result,  # git status (clean)
            branch_result,  # git rev-parse --abbrev-ref HEAD
            log_result,  # git log (fails — no origin/main ref)
            MagicMock(),  # git push (should still be attempted)
        ]

        push_to_remote("proj-1", "/tmp/repo", "POC")

        # 5 calls: add, status, rev-parse, log (fail), push (success)
        assert mock_subprocess.run.call_count == 5


@pytest.mark.unit
class TestSyncArtifactsToS3:
    """Verify sync_artifacts_to_s3 uploads docs/security and skips code dirs."""

    @patch("src.phases.git_ops.boto3")
    @patch("src.phases.git_ops.SOW_BUCKET", "my-bucket")
    def test_syncs_docs_and_security_only(
        self,
        mock_boto3: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import sync_artifacts_to_s3

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        # Create files in docs, security, app, and .git
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "sow.md").write_text("SOW content")
        (tmp_path / "security").mkdir()
        (tmp_path / "security" / "scan.md").write_text("Scan")
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("code")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")

        sync_artifacts_to_s3("proj-1", str(tmp_path))

        # Only docs/ and security/ synced; app/ and .git/ excluded
        assert mock_s3.put_object.call_count == 2
        uploaded_keys = [call.kwargs["Key"] for call in mock_s3.put_object.call_args_list]
        assert any("docs/sow.md" in k for k in uploaded_keys)
        assert any("security/scan.md" in k for k in uploaded_keys)
        assert not any("app/" in k for k in uploaded_keys)
        assert not any(".git" in k for k in uploaded_keys)

    @patch("src.phases.git_ops.boto3")
    @patch("src.phases.git_ops.SOW_BUCKET", "my-bucket")
    def test_skips_code_directories(
        self,
        mock_boto3: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import sync_artifacts_to_s3

        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3

        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "sow.md").write_text("SOW")
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("code")
        (tmp_path / "infra").mkdir()
        (tmp_path / "infra" / "main.tf").write_text("terraform")
        (tmp_path / "data").mkdir()
        (tmp_path / "data" / "schema.sql").write_text("CREATE TABLE")

        sync_artifacts_to_s3("proj-1", str(tmp_path))

        # Only docs/ synced; app/, infra/, data/ excluded (code lives in GitHub)
        assert mock_s3.put_object.call_count == 1

    @patch("src.phases.git_ops.SOW_BUCKET", "")
    def test_skips_when_no_bucket(self) -> None:
        from src.phases.git_ops import sync_artifacts_to_s3

        # Should not raise
        sync_artifacts_to_s3("proj-1", "/tmp/repo")

    @patch("src.phases.git_ops.update_deliverables")
    @patch("src.phases.git_ops.boto3")
    @patch("src.phases.git_ops.SOW_BUCKET", "my-bucket")
    def test_registers_deliverables_when_phase_provided(
        self,
        mock_boto3: MagicMock,
        mock_update_deliverables: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import sync_artifacts_to_s3

        mock_boto3.client.return_value = MagicMock()

        (tmp_path / "docs" / "architecture").mkdir(parents=True)
        (tmp_path / "docs" / "architecture" / "system-design.md").write_text("design")
        (tmp_path / "security").mkdir()
        (tmp_path / "security" / "threat-model.md").write_text("threats")

        sync_artifacts_to_s3("proj-1", str(tmp_path), "ARCHITECTURE")

        mock_update_deliverables.assert_called_once()
        call_args = mock_update_deliverables.call_args
        assert call_args[0][1] == "proj-1"
        assert call_args[0][2] == "ARCHITECTURE"
        deliverables = call_args[0][3]
        assert len(deliverables) == 2
        names = {d["name"] for d in deliverables}
        assert "System Design" in names
        assert "Threat Model" in names

    @patch("src.phases.git_ops.update_deliverables")
    @patch("src.phases.git_ops.boto3")
    @patch("src.phases.git_ops.SOW_BUCKET", "my-bucket")
    def test_excludes_phase_summaries_from_deliverables(
        self,
        mock_boto3: MagicMock,
        mock_update_deliverables: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import sync_artifacts_to_s3

        mock_boto3.client.return_value = MagicMock()

        (tmp_path / "docs" / "phase-summaries").mkdir(parents=True)
        (tmp_path / "docs" / "phase-summaries" / "architecture.md").write_text("summary")
        (tmp_path / "docs" / "architecture").mkdir(parents=True)
        (tmp_path / "docs" / "architecture" / "design.md").write_text("design")

        sync_artifacts_to_s3("proj-1", str(tmp_path), "ARCHITECTURE")

        # Phase summary is synced to S3 but NOT registered as a deliverable
        mock_update_deliverables.assert_called_once()
        deliverables = mock_update_deliverables.call_args[0][3]
        assert len(deliverables) == 1
        assert deliverables[0]["git_path"] == "docs/architecture/design.md"

    @patch("src.phases.git_ops.update_deliverables")
    @patch("src.phases.git_ops.boto3")
    @patch("src.phases.git_ops.SOW_BUCKET", "my-bucket")
    def test_skips_deliverable_registration_without_phase(
        self,
        mock_boto3: MagicMock,
        mock_update_deliverables: MagicMock,
        tmp_path: Path,
    ) -> None:
        from src.phases.git_ops import sync_artifacts_to_s3

        mock_boto3.client.return_value = MagicMock()

        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "sow.md").write_text("SOW")

        sync_artifacts_to_s3("proj-1", str(tmp_path))

        mock_update_deliverables.assert_not_called()


@pytest.mark.unit
class TestPathToName:
    """Verify _path_to_name helper."""

    def test_kebab_case_markdown(self) -> None:
        from src.phases.git_ops import _path_to_name

        assert _path_to_name("docs/architecture/system-design.md") == "System Design"

    def test_snake_case(self) -> None:
        from src.phases.git_ops import _path_to_name

        assert _path_to_name("security/threat_model.md") == "Threat Model"

    def test_simple_filename(self) -> None:
        from src.phases.git_ops import _path_to_name

        assert _path_to_name("docs/discovery/requirements.md") == "Requirements"

    def test_nested_path(self) -> None:
        from src.phases.git_ops import _path_to_name

        assert _path_to_name("docs/project-plan/sow.md") == "Sow"
