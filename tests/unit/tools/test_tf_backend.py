"""Tests for src/tools/_tf_backend.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from src.state.models import TerraformBackend
from src.tools._tf_backend import (
    _bucket_name,
    _table_name,
    build_backend_config_args,
    ensure_backend_tf,
    provision_backend,
)

_MOD = "src.tools._tf_backend"


def _mock_client_dispatch(mock_s3: MagicMock, mock_dynamodb: MagicMock | None = None) -> MagicMock:
    """Return a side_effect-ready function for session.client dispatching."""
    clients = {"s3": mock_s3, "dynamodb": mock_dynamodb or MagicMock()}

    def _dispatch(service: str, region_name: str = "") -> MagicMock:
        del region_name  # accepted but unused; boto3 passes it as kwarg
        return clients.get(service, MagicMock())

    return _dispatch


@pytest.mark.unit
class TestBucketName:
    """Verify S3 bucket name generation."""

    def test_normal_name(self) -> None:
        assert _bucket_name("proj-123") == "cloudcrew-tfstate-proj-123"

    def test_truncated_to_63_chars(self) -> None:
        long_id = "a" * 100
        result = _bucket_name(long_id)
        assert len(result) == 63
        assert result.startswith("cloudcrew-tfstate-")


@pytest.mark.unit
class TestTableName:
    """Verify DynamoDB table name generation."""

    def test_normal_name(self) -> None:
        assert _table_name("proj-123") == "cloudcrew-tflocks-proj-123"

    def test_truncated_to_255_chars(self) -> None:
        long_id = "b" * 300
        result = _table_name(long_id)
        assert len(result) == 255
        assert result.startswith("cloudcrew-tflocks-")


@pytest.mark.unit
class TestProvisionBackend:
    """Verify backend provisioning."""

    def test_success(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_dynamodb = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3, mock_dynamodb)
        mock_waiter = MagicMock()
        mock_dynamodb.get_waiter.return_value = mock_waiter

        with patch(f"{_MOD}.boto3.Session", return_value=mock_session):
            result = provision_backend("proj-1", "us-west-2", "AKID", "SECRET")

        assert isinstance(result, TerraformBackend)
        assert result.bucket == "cloudcrew-tfstate-proj-1"
        assert result.key == "terraform.tfstate"
        assert result.region == "us-west-2"
        assert result.dynamodb_table == "cloudcrew-tflocks-proj-1"
        assert result.provisioned_at != ""

    def test_idempotent_bucket(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_dynamodb = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3, mock_dynamodb)
        mock_waiter = MagicMock()
        mock_dynamodb.get_waiter.return_value = mock_waiter

        # Simulate BucketAlreadyOwnedByYou
        mock_s3.create_bucket.side_effect = ClientError(
            {"Error": {"Code": "BucketAlreadyOwnedByYou", "Message": ""}},
            "CreateBucket",
        )

        with patch(f"{_MOD}.boto3.Session", return_value=mock_session):
            result = provision_backend("proj-1", "us-west-2", "AKID", "SECRET")

        assert isinstance(result, TerraformBackend)
        # Versioning and encryption should still be applied
        mock_s3.put_bucket_versioning.assert_called_once()
        mock_s3.put_bucket_encryption.assert_called_once()

    def test_idempotent_table(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_dynamodb = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3, mock_dynamodb)

        # Simulate ResourceInUseException (table already exists)
        mock_dynamodb.create_table.side_effect = ClientError(
            {"Error": {"Code": "ResourceInUseException", "Message": ""}},
            "CreateTable",
        )

        with patch(f"{_MOD}.boto3.Session", return_value=mock_session):
            result = provision_backend("proj-1", "us-east-1", "AKID", "SECRET")

        assert isinstance(result, TerraformBackend)
        # Waiter should NOT be called for existing table
        mock_dynamodb.get_waiter.assert_not_called()

    def test_us_east_1_no_location_constraint(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_dynamodb = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3, mock_dynamodb)
        mock_waiter = MagicMock()
        mock_dynamodb.get_waiter.return_value = mock_waiter

        with patch(f"{_MOD}.boto3.Session", return_value=mock_session):
            provision_backend("proj-1", "us-east-1", "AKID", "SECRET")

        call_kwargs = mock_s3.create_bucket.call_args.kwargs
        assert "CreateBucketConfiguration" not in call_kwargs

    def test_non_us_east_1_has_location_constraint(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_dynamodb = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3, mock_dynamodb)
        mock_waiter = MagicMock()
        mock_dynamodb.get_waiter.return_value = mock_waiter

        with patch(f"{_MOD}.boto3.Session", return_value=mock_session):
            provision_backend("proj-1", "eu-west-1", "AKID", "SECRET")

        call_kwargs = mock_s3.create_bucket.call_args.kwargs
        assert call_kwargs["CreateBucketConfiguration"]["LocationConstraint"] == "eu-west-1"

    def test_s3_error_propagates(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3)

        mock_s3.create_bucket.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "No access"}},
            "CreateBucket",
        )

        with (
            patch(f"{_MOD}.boto3.Session", return_value=mock_session),
            pytest.raises(ClientError),
        ):
            provision_backend("proj-1", "us-west-2", "AKID", "SECRET")

    def test_bucket_already_exists_different_owner_propagates(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3)

        # BucketAlreadyExists = different account owns the name
        mock_s3.create_bucket.side_effect = ClientError(
            {"Error": {"Code": "BucketAlreadyExists", "Message": "Bucket name taken"}},
            "CreateBucket",
        )

        with (
            patch(f"{_MOD}.boto3.Session", return_value=mock_session),
            pytest.raises(ClientError),
        ):
            provision_backend("proj-1", "us-west-2", "AKID", "SECRET")

    def test_dynamodb_error_propagates(self) -> None:
        mock_session = MagicMock()
        mock_s3 = MagicMock()
        mock_dynamodb = MagicMock()
        mock_session.client.side_effect = _mock_client_dispatch(mock_s3, mock_dynamodb)

        mock_dynamodb.create_table.side_effect = ClientError(
            {"Error": {"Code": "AccessDeniedException", "Message": "No access"}},
            "CreateTable",
        )

        with (
            patch(f"{_MOD}.boto3.Session", return_value=mock_session),
            pytest.raises(ClientError),
        ):
            provision_backend("proj-1", "us-west-2", "AKID", "SECRET")


@pytest.mark.unit
class TestBuildBackendConfigArgs:
    """Verify CLI flag generation."""

    def test_flag_list(self) -> None:
        backend = TerraformBackend(
            bucket="my-bucket",
            key="terraform.tfstate",
            region="us-west-2",
            dynamodb_table="my-locks",
        )
        args = build_backend_config_args(backend)
        assert args == [
            "-backend-config=bucket=my-bucket",
            "-backend-config=key=terraform.tfstate",
            "-backend-config=region=us-west-2",
            "-backend-config=dynamodb_table=my-locks",
            "-backend-config=encrypt=true",
        ]


@pytest.mark.unit
class TestEnsureBackendTf:
    """Verify backend.tf file writer."""

    def test_writes_when_missing(self, tmp_path: Path) -> None:
        result = ensure_backend_tf(tmp_path)
        assert result is True
        backend_tf = tmp_path / "backend.tf"
        assert backend_tf.exists()
        content = backend_tf.read_text()
        assert 'backend "s3"' in content

    def test_skips_when_existing(self, tmp_path: Path) -> None:
        existing = tmp_path / "main.tf"
        existing.write_text('terraform {\n  backend "s3" {\n    bucket = "x"\n  }\n}\n')

        result = ensure_backend_tf(tmp_path)
        assert result is False
        # Should NOT create a separate backend.tf
        assert not (tmp_path / "backend.tf").exists()

    def test_skips_when_backend_tf_exists(self, tmp_path: Path) -> None:
        existing = tmp_path / "backend.tf"
        existing.write_text('terraform {\n  backend "s3" {}\n}\n')

        result = ensure_backend_tf(tmp_path)
        assert result is False
