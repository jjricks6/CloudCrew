"""Tests for src/tools/deploy_tools.py."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from src.state.models import TerraformBackend
from src.tools.deploy_tools import (
    terraform_apply,
    terraform_destroy,
    terraform_output,
    terraform_plan,
)

# Module path prefix for patching
_MOD = "src.tools.deploy_tools"

_MOCK_BACKEND = TerraformBackend(
    bucket="cloudcrew-tfstate-proj-123",
    key="terraform.tfstate",
    region="us-west-2",
    dynamodb_table="cloudcrew-tflocks-proj-123",
)


def _make_context(tmp_path: Path, *, project_id: str = "proj-123") -> MagicMock:
    """Build a mock ToolContext with invocation_state pointing at a temp repo."""
    ctx = MagicMock()
    ctx.invocation_state = {
        "project_id": project_id,
        "git_repo_url": str(tmp_path),
    }
    return ctx


def _make_repo(tmp_path: Path) -> MagicMock:
    repo = MagicMock()
    repo.working_dir = str(tmp_path)
    return repo


def _mock_ledger(region: str = "us-west-2") -> MagicMock:
    ledger = MagicMock()
    ledger.aws_region_target = region
    return ledger


def _success_result(stdout: str = "", stderr: str = "") -> MagicMock:
    r = MagicMock()
    r.returncode = 0
    r.stdout = stdout
    r.stderr = stderr
    return r


def _failure_result(stdout: str = "", stderr: str = "") -> MagicMock:
    r = MagicMock()
    r.returncode = 1
    r.stdout = stdout
    r.stderr = stderr
    return r


def _init_ok() -> MagicMock:
    """Return a successful init result for _init_with_backend."""
    return _success_result()


@pytest.mark.unit
class TestTerraformPlan:
    """Verify terraform_plan tool."""

    def test_plan_success(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        plan_ok = _success_result(stdout="Plan: 3 to add, 0 to change, 0 to destroy.")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=plan_ok) as mock_run,
        ):
            result = terraform_plan("infra", ctx)

        assert "Plan: 3 to add" in result
        # Verify AWS creds were injected into env for the plan command
        env = mock_run.call_args.kwargs["env"]
        assert env["AWS_ACCESS_KEY_ID"] == "AKID"
        assert env["AWS_SECRET_ACCESS_KEY"] == "SECRET"
        assert env["AWS_DEFAULT_REGION"] == "us-west-2"
        assert env["TF_INPUT"] == "0"

    def test_plan_no_credentials(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(
                f"{_MOD}._ensure_remote_backend",
                side_effect=ValueError("No AWS credentials found. Use store_aws_credentials during Discovery first."),
            ),
        ):
            result = terraform_plan("infra", ctx)

        assert "No AWS credentials" in result

    def test_plan_no_project_id(self) -> None:
        ctx = MagicMock()
        ctx.invocation_state = {}

        result = terraform_plan("infra", ctx)
        assert "Error" in result

    def test_plan_timeout(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(
                f"{_MOD}._init_with_backend",
                side_effect=subprocess.TimeoutExpired(cmd="terraform", timeout=180),
            ),
        ):
            result = terraform_plan("infra", ctx)

        assert "timed out" in result

    def test_plan_init_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_fail = _failure_result(stderr="backend init error")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_fail),
        ):
            result = terraform_plan("infra", ctx)

        assert "terraform init failed" in result
        assert "backend init error" in result

    def test_plan_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        plan_fail = _failure_result(stdout="Error: Invalid resource", stderr="details")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=plan_fail),
        ):
            result = terraform_plan("infra", ctx)

        assert "terraform plan failed" in result

    def test_plan_terraform_not_found(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", side_effect=FileNotFoundError),
        ):
            result = terraform_plan("infra", ctx)

        assert "terraform CLI not found" in result

    def test_plan_directory_not_found(self, tmp_path: Path) -> None:
        ctx = _make_context(tmp_path)

        with patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)):
            result = terraform_plan("nonexistent", ctx)

        assert "Error" in result

    def test_plan_backend_provisioning_error(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(
                f"{_MOD}._ensure_remote_backend",
                side_effect=ClientError(
                    {"Error": {"Code": "AccessDenied", "Message": "Insufficient permissions"}},
                    "CreateBucket",
                ),
            ),
        ):
            result = terraform_plan("infra", ctx)

        assert "Error provisioning backend" in result
        assert "Insufficient permissions" in result

    def test_plan_default_region(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        plan_ok = _success_result(stdout="No changes.")
        ledger = MagicMock()
        ledger.aws_region_target = None

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=ledger),
            patch(f"{_MOD}.subprocess.run", return_value=plan_ok) as mock_run,
        ):
            result = terraform_plan("infra", ctx)

        assert "No changes" in result
        env = mock_run.call_args.kwargs["env"]
        assert env["AWS_DEFAULT_REGION"] == "us-east-1"


@pytest.mark.unit
class TestTerraformApply:
    """Verify terraform_apply tool."""

    def test_apply_success(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        apply_ok = _success_result(stdout="Apply complete! Resources: 3 added.")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=apply_ok),
        ):
            result = terraform_apply("infra", ctx)

        assert "Apply successful" in result
        assert "3 added" in result

    def test_apply_failure_returns_error(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        apply_fail = _failure_result(
            stdout="Error creating S3 bucket",
            stderr="AccessDenied",
        )

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=apply_fail),
        ):
            result = terraform_apply("infra", ctx)

        assert "terraform apply failed" in result
        assert "Error creating S3 bucket" in result
        assert "AccessDenied" in result

    def test_apply_timeout(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(
                f"{_MOD}._init_with_backend",
                side_effect=subprocess.TimeoutExpired(cmd="terraform", timeout=600),
            ),
        ):
            result = terraform_apply("infra", ctx)

        assert "timed out" in result
        assert "600" in result

    def test_apply_no_project_id(self) -> None:
        ctx = MagicMock()
        ctx.invocation_state = {}

        result = terraform_apply("infra", ctx)
        assert "Error" in result

    def test_apply_init_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_fail = _failure_result(stderr="backend init error")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_fail),
        ):
            result = terraform_apply("infra", ctx)

        assert "terraform init failed" in result


@pytest.mark.unit
class TestTerraformOutput:
    """Verify terraform_output tool."""

    def test_output_success(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        output_ok = _success_result(stdout='{"api_url": {"value": "https://api.example.com"}}')

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=output_ok),
        ):
            result = terraform_output("infra", ctx)

        assert "api_url" in result

    def test_output_empty_state(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        output_ok = _success_result(stdout="")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=output_ok),
        ):
            result = terraform_output("infra", ctx)

        assert result == "{}"

    def test_output_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        output_fail = _failure_result(stderr="No state file found")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=output_fail),
        ):
            result = terraform_output("infra", ctx)

        assert "terraform output failed" in result

    def test_output_timeout(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(
                f"{_MOD}._init_with_backend",
                side_effect=subprocess.TimeoutExpired(cmd="terraform", timeout=30),
            ),
        ):
            result = terraform_output("infra", ctx)

        assert "timed out" in result


@pytest.mark.unit
class TestTerraformDestroy:
    """Verify terraform_destroy tool."""

    def test_destroy_success(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        destroy_ok = _success_result(stdout="Destroy complete! Resources: 3 destroyed.")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=destroy_ok),
        ):
            result = terraform_destroy("infra", ctx)

        assert "Destroy successful" in result

    def test_destroy_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_ok = _success_result()
        destroy_fail = _failure_result(
            stdout="Error destroying resources",
            stderr="DependencyViolation",
        )

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_ok),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.read_ledger", return_value=_mock_ledger()),
            patch(f"{_MOD}.subprocess.run", return_value=destroy_fail),
        ):
            result = terraform_destroy("infra", ctx)

        assert "terraform destroy failed" in result

    def test_destroy_timeout(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(
                f"{_MOD}._init_with_backend",
                side_effect=subprocess.TimeoutExpired(cmd="terraform", timeout=600),
            ),
        ):
            result = terraform_destroy("infra", ctx)

        assert "timed out" in result

    def test_destroy_init_failure(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        ctx = _make_context(tmp_path)

        init_fail = _failure_result(stderr="backend init error")

        with (
            patch(f"{_MOD}._get_repo", return_value=_make_repo(tmp_path)),
            patch(f"{_MOD}._ensure_remote_backend", return_value=_MOCK_BACKEND),
            patch(f"{_MOD}._init_with_backend", return_value=init_fail),
        ):
            result = terraform_destroy("infra", ctx)

        assert "terraform init failed" in result


@pytest.mark.unit
class TestEnsureRemoteBackend:
    """Verify _ensure_remote_backend helper."""

    def test_returns_cached_backend(self) -> None:
        from src.tools.deploy_tools import _ensure_remote_backend

        ledger = MagicMock()
        ledger.terraform_backend = _MOCK_BACKEND

        with patch(f"{_MOD}.read_ledger", return_value=ledger):
            result = _ensure_remote_backend("proj-123")

        assert result is _MOCK_BACKEND

    def test_provisions_and_saves_new_backend(self) -> None:
        from src.tools.deploy_tools import _ensure_remote_backend

        ledger = MagicMock()
        ledger.terraform_backend = None
        ledger.aws_region_target = "us-west-2"

        with (
            patch(f"{_MOD}.read_ledger", return_value=ledger),
            patch(f"{_MOD}.get_aws_credentials", return_value=("AKID", "SECRET")),
            patch(f"{_MOD}.provision_backend", return_value=_MOCK_BACKEND) as mock_prov,
            patch(f"{_MOD}.write_ledger") as mock_write,
        ):
            result = _ensure_remote_backend("proj-123")

        assert result is _MOCK_BACKEND
        mock_prov.assert_called_once_with("proj-123", "us-west-2", "AKID", "SECRET")
        mock_write.assert_called_once()

    def test_raises_without_credentials(self) -> None:
        from src.tools.deploy_tools import _ensure_remote_backend

        ledger = MagicMock()
        ledger.terraform_backend = None

        with (
            patch(f"{_MOD}.read_ledger", return_value=ledger),
            patch(f"{_MOD}.get_aws_credentials", return_value=("", "")),
            pytest.raises(ValueError, match="No AWS credentials"),
        ):
            _ensure_remote_backend("proj-123")


@pytest.mark.unit
class TestInitWithBackend:
    """Verify _init_with_backend helper."""

    def test_calls_ensure_backend_tf_and_runs_init(self, tmp_path: Path) -> None:
        from src.tools.deploy_tools import _init_with_backend

        init_ok = _success_result()
        abs_path = str(tmp_path / "infra")

        with (
            patch(f"{_MOD}.ensure_backend_tf") as mock_ensure,
            patch(f"{_MOD}._run_terraform_with_creds", return_value=init_ok) as mock_run,
        ):
            result = _init_with_backend("proj-123", abs_path, _MOCK_BACKEND, 180)

        mock_ensure.assert_called_once()
        assert result is init_ok
        # Verify -reconfigure and -backend-config flags
        call_args = mock_run.call_args
        tf_args = call_args.args[1]
        assert "-reconfigure" in tf_args
        assert "-backend-config=bucket=cloudcrew-tfstate-proj-123" in tf_args
        assert "-backend-config=encrypt=true" in tf_args
