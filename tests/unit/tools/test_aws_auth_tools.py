"""Tests for src/tools/aws_auth_tools.py."""

from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

# Test fixture values — stored as constants to avoid S106 (hardcoded password) lint warnings.
_TEST_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
_TEST_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
_TEST_ACCOUNT_ID = "123456789012"
_TEST_REGION = "us-east-1"


def _make_tool_context(project_id: str = "proj-1") -> MagicMock:
    """Create a mock ToolContext with project_id in invocation_state."""
    ctx = MagicMock()
    ctx.invocation_state = {"project_id": project_id}
    return ctx


def _call_store(
    ctx: MagicMock,
    access_key_id: str = _TEST_ACCESS_KEY,
    secret_access_key: str = _TEST_SECRET_KEY,
    account_id: str = _TEST_ACCOUNT_ID,
    region: str = _TEST_REGION,
) -> str:
    """Call store_aws_credentials_tool with test defaults."""
    from src.tools.aws_auth_tools import store_aws_credentials_tool

    return str(
        store_aws_credentials_tool(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            account_id=account_id,
            region=region,
            tool_context=ctx,
        )
    )


@pytest.mark.unit
class TestStoreAwsCredentialsTool:
    """Verify store_aws_credentials_tool behavior."""

    @patch("src.tools.aws_auth_tools.write_ledger")
    @patch("src.tools.aws_auth_tools.read_ledger")
    @patch("src.tools.aws_auth_tools.store_aws_credentials")
    def test_stores_credentials_and_updates_ledger(
        self,
        mock_store: MagicMock,
        mock_read_ledger: MagicMock,
        mock_write_ledger: MagicMock,
    ) -> None:
        """Happy path: store credentials and update ledger."""
        from src.state.models import TaskLedger

        mock_store.return_value = True
        mock_ledger = TaskLedger(project_id="proj-1")
        mock_read_ledger.return_value = mock_ledger

        ctx = _make_tool_context()
        result = _call_store(ctx)

        assert "successfully" in result
        assert _TEST_ACCOUNT_ID in result
        mock_store.assert_called_once_with("proj-1", _TEST_ACCESS_KEY, _TEST_SECRET_KEY)
        assert mock_ledger.aws_account_id == _TEST_ACCOUNT_ID
        assert mock_ledger.aws_region_target == _TEST_REGION
        mock_write_ledger.assert_called_once()

    def test_rejects_invalid_access_key_format(self) -> None:
        """Reject access key that doesn't start with AKIA."""
        ctx = _make_tool_context()
        result = _call_store(ctx, access_key_id="XYZAIOSFODNN7EXAMPLE")

        assert "Error" in result
        assert "AKIA" in result

    def test_rejects_wrong_length_access_key(self) -> None:
        """Reject access key with wrong length."""
        ctx = _make_tool_context()
        result = _call_store(ctx, access_key_id="AKIA_SHORT")

        assert "Error" in result
        assert "20" in result

    def test_rejects_wrong_length_secret_key(self) -> None:
        """Reject secret key with wrong length."""
        short_secret = "too-short"
        ctx = _make_tool_context()
        result = _call_store(ctx, secret_access_key=short_secret)

        assert "Error" in result
        assert "40" in result

    def test_rejects_invalid_account_id(self) -> None:
        """Reject non-12-digit account ID."""
        ctx = _make_tool_context()
        result = _call_store(ctx, account_id="12345")

        assert "Error" in result
        assert "12-digit" in result

    def test_rejects_missing_project_id(self) -> None:
        """Reject when project_id is missing from invocation state."""
        ctx = _make_tool_context(project_id="")
        result = _call_store(ctx)

        assert "Error" in result
        assert "project_id" in result

    @patch("src.tools.aws_auth_tools.store_aws_credentials")
    def test_handles_secrets_manager_failure(
        self,
        mock_store: MagicMock,
    ) -> None:
        """Return error when Secrets Manager store fails."""
        mock_store.return_value = False

        ctx = _make_tool_context()
        result = _call_store(ctx)

        assert "Error" in result
        assert "Failed to store" in result


@pytest.mark.unit
class TestVerifyAwsAccess:
    """Verify verify_aws_access behavior."""

    @patch("src.tools.aws_auth_tools.boto3")
    @patch("src.tools.aws_auth_tools.get_aws_credentials")
    @patch("src.tools.aws_auth_tools.read_ledger")
    def test_verifies_aws_access_success(
        self,
        mock_read_ledger: MagicMock,
        mock_get_creds: MagicMock,
        mock_boto3: MagicMock,
    ) -> None:
        """Happy path: STS returns matching account."""
        from src.state.models import TaskLedger
        from src.tools.aws_auth_tools import verify_aws_access

        mock_ledger = TaskLedger(
            project_id="proj-1",
            aws_account_id=_TEST_ACCOUNT_ID,
            aws_region_target=_TEST_REGION,
        )
        mock_read_ledger.return_value = mock_ledger
        mock_get_creds.return_value = (_TEST_ACCESS_KEY, _TEST_SECRET_KEY)

        mock_sts = MagicMock()
        mock_boto3.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            "Account": _TEST_ACCOUNT_ID,
            "Arn": f"arn:aws:iam::{_TEST_ACCOUNT_ID}:user/test",
        }

        ctx = _make_tool_context()
        result = verify_aws_access(tool_context=ctx)

        assert "verified" in result
        assert _TEST_ACCOUNT_ID in result
        mock_boto3.client.assert_called_once_with(
            "sts",
            aws_access_key_id=_TEST_ACCESS_KEY,
            aws_secret_access_key=_TEST_SECRET_KEY,
            region_name=_TEST_REGION,
        )

    @patch("src.tools.aws_auth_tools.boto3")
    @patch("src.tools.aws_auth_tools.get_aws_credentials")
    @patch("src.tools.aws_auth_tools.read_ledger")
    def test_verifies_aws_access_account_mismatch(
        self,
        mock_read_ledger: MagicMock,
        mock_get_creds: MagicMock,
        mock_boto3: MagicMock,
    ) -> None:
        """Error when STS account doesn't match expected."""
        from src.state.models import TaskLedger
        from src.tools.aws_auth_tools import verify_aws_access

        mock_ledger = TaskLedger(
            project_id="proj-1",
            aws_account_id=_TEST_ACCOUNT_ID,
            aws_region_target=_TEST_REGION,
        )
        mock_read_ledger.return_value = mock_ledger
        mock_get_creds.return_value = (_TEST_ACCESS_KEY, _TEST_SECRET_KEY)

        mock_sts = MagicMock()
        mock_boto3.client.return_value = mock_sts
        mock_sts.get_caller_identity.return_value = {
            "Account": "999999999999",
            "Arn": "arn:aws:iam::999999999999:user/wrong",
        }

        ctx = _make_tool_context()
        result = verify_aws_access(tool_context=ctx)

        assert "Error" in result
        assert "mismatch" in result
        assert _TEST_ACCOUNT_ID in result
        assert "999999999999" in result

    @patch("src.tools.aws_auth_tools.get_aws_credentials")
    @patch("src.tools.aws_auth_tools.read_ledger")
    def test_verifies_aws_access_no_credentials(
        self,
        mock_read_ledger: MagicMock,
        mock_get_creds: MagicMock,
    ) -> None:
        """Error when no credentials found in Secrets Manager."""
        from src.state.models import TaskLedger
        from src.tools.aws_auth_tools import verify_aws_access

        mock_ledger = TaskLedger(
            project_id="proj-1",
            aws_account_id=_TEST_ACCOUNT_ID,
            aws_region_target=_TEST_REGION,
        )
        mock_read_ledger.return_value = mock_ledger
        mock_get_creds.return_value = ("", "")

        ctx = _make_tool_context()
        result = verify_aws_access(tool_context=ctx)

        assert "Error" in result
        assert "No AWS credentials found" in result

    @patch("src.tools.aws_auth_tools.boto3")
    @patch("src.tools.aws_auth_tools.get_aws_credentials")
    @patch("src.tools.aws_auth_tools.read_ledger")
    def test_verifies_aws_access_sts_error(
        self,
        mock_read_ledger: MagicMock,
        mock_get_creds: MagicMock,
        mock_boto3: MagicMock,
    ) -> None:
        """Error when STS call fails with invalid credentials."""
        from src.state.models import TaskLedger
        from src.tools.aws_auth_tools import verify_aws_access

        mock_ledger = TaskLedger(
            project_id="proj-1",
            aws_account_id=_TEST_ACCOUNT_ID,
            aws_region_target=_TEST_REGION,
        )
        mock_read_ledger.return_value = mock_ledger
        mock_get_creds.return_value = (_TEST_ACCESS_KEY, "bad-secret-key-value-here")

        mock_sts = MagicMock()
        mock_boto3.client.return_value = mock_sts
        mock_sts.get_caller_identity.side_effect = ClientError(
            {"Error": {"Code": "InvalidClientTokenId", "Message": "bad token"}},
            "GetCallerIdentity",
        )

        ctx = _make_tool_context()
        result = verify_aws_access(tool_context=ctx)

        assert "Error" in result
        assert "Invalid AWS credentials" in result

    @patch("src.tools.aws_auth_tools.read_ledger")
    def test_verifies_aws_access_no_account_id(
        self,
        mock_read_ledger: MagicMock,
    ) -> None:
        """Error when no account ID stored in ledger."""
        from src.state.models import TaskLedger
        from src.tools.aws_auth_tools import verify_aws_access

        mock_ledger = TaskLedger(project_id="proj-1")
        mock_read_ledger.return_value = mock_ledger

        ctx = _make_tool_context()
        result = verify_aws_access(tool_context=ctx)

        assert "Error" in result
        assert "No AWS account ID stored" in result

    def test_verifies_aws_access_no_project_id(self) -> None:
        """Error when project_id is missing from invocation state."""
        from src.tools.aws_auth_tools import verify_aws_access

        ctx = _make_tool_context(project_id="")
        result = verify_aws_access(tool_context=ctx)

        assert "Error" in result
        assert "project_id" in result
