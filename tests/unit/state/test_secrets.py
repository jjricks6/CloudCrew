"""Tests for Secrets Manager integration (Bedrock API key + GitHub PAT + AWS credentials)."""

import json
from unittest.mock import patch

import pytest
from botocore.exceptions import ClientError
from src.state.secrets import (
    clear_bedrock_api_key_cache,
    get_aws_credentials,
    get_bedrock_api_key,
    get_github_pat,
    store_aws_credentials,
    store_github_pat,
)


@pytest.mark.unit
class TestGetBedrockApiKey:
    """Test suite for get_bedrock_api_key()."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        clear_bedrock_api_key_cache()

    def test_get_api_key_plain_string(self) -> None:
        """Retrieve API key stored as plain string in Secrets Manager."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": "test-api-key-123"}

            result = get_bedrock_api_key()

            assert result == "test-api-key-123"
            mock_client.get_secret_value.assert_called_once_with(SecretId="cloudcrew/bedrock-api-key")

    def test_get_api_key_json_format(self) -> None:
        """Retrieve API key from JSON secret with 'api_key' field."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            secret_json = json.dumps({"api_key": "test-api-key-456"})
            mock_client.get_secret_value.return_value = {"SecretString": secret_json}

            result = get_bedrock_api_key()

            assert result == "test-api-key-456"

    def test_get_api_key_caching(self) -> None:
        """Verify that API key is cached across multiple calls."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": "cached-key"}

            result1 = get_bedrock_api_key()
            result2 = get_bedrock_api_key()

            # Both results should be the same
            assert result1 == result2 == "cached-key"
            # But the client should only be called once due to caching
            mock_client.get_secret_value.assert_called_once()

    def test_get_api_key_secret_not_found(self) -> None:
        """Return empty string when secret doesn't exist."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            error_response = {"Error": {"Code": "ResourceNotFoundException"}}
            mock_client.get_secret_value.side_effect = ClientError(error_response, "GetSecretValue")

            result = get_bedrock_api_key()

            assert result == ""

    def test_get_api_key_access_denied(self) -> None:
        """Return empty string when access is denied."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            error_response = {"Error": {"Code": "AccessDeniedException"}}
            mock_client.get_secret_value.side_effect = ClientError(error_response, "GetSecretValue")

            result = get_bedrock_api_key()

            assert result == ""

    def test_get_api_key_unexpected_error(self) -> None:
        """Return empty string on unexpected errors."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.side_effect = Exception("Network error")

            result = get_bedrock_api_key()

            assert result == ""

    def test_get_api_key_empty_secret(self) -> None:
        """Handle empty secret gracefully."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": ""}

            result = get_bedrock_api_key()

            assert result == ""

    def test_clear_cache(self) -> None:
        """Verify cache can be cleared and refetched."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": "first-key"}

            result1 = get_bedrock_api_key()
            assert result1 == "first-key"
            assert mock_client.get_secret_value.call_count == 1

            # Clear cache
            clear_bedrock_api_key_cache()

            # Update mock for next call
            mock_client.get_secret_value.return_value = {"SecretString": "second-key"}
            result2 = get_bedrock_api_key()

            assert result2 == "second-key"
            assert mock_client.get_secret_value.call_count == 2


@pytest.mark.unit
class TestStoreGithubPat:
    """Test suite for store_github_pat()."""

    def test_creates_new_secret(self) -> None:
        """Store PAT by creating a new secret."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            result = store_github_pat("proj-1", "ghp_test123456")

            assert result is True
            mock_client.create_secret.assert_called_once_with(
                Name="cloudcrew/proj-1/github-pat",
                SecretString="ghp_test123456",
                Description="GitHub PAT for CloudCrew project proj-1",
            )

    def test_updates_existing_secret(self) -> None:
        """Fall back to put_secret_value when secret already exists."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = ClientError(
                {"Error": {"Code": "ResourceExistsException"}},
                "CreateSecret",
            )

            result = store_github_pat("proj-1", "ghp_updated_token")

            assert result is True
            mock_client.put_secret_value.assert_called_once_with(
                SecretId="cloudcrew/proj-1/github-pat",
                SecretString="ghp_updated_token",
            )

    def test_returns_false_on_create_failure(self) -> None:
        """Return False when create fails with non-exists error."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = ClientError(
                {"Error": {"Code": "AccessDeniedException"}},
                "CreateSecret",
            )

            result = store_github_pat("proj-1", "ghp_test")

            assert result is False

    def test_returns_false_on_update_failure(self) -> None:
        """Return False when both create and update fail."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = ClientError(
                {"Error": {"Code": "ResourceExistsException"}},
                "CreateSecret",
            )
            mock_client.put_secret_value.side_effect = ClientError(
                {"Error": {"Code": "InternalServiceError"}},
                "PutSecretValue",
            )

            result = store_github_pat("proj-1", "ghp_test")

            assert result is False

    def test_returns_false_on_unexpected_error(self) -> None:
        """Return False on unexpected exceptions."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = RuntimeError("Network error")

            result = store_github_pat("proj-1", "ghp_test")

            assert result is False


@pytest.mark.unit
class TestGetGithubPat:
    """Test suite for get_github_pat()."""

    def test_retrieves_pat(self) -> None:
        """Retrieve PAT from Secrets Manager."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": "ghp_test123"}

            result = get_github_pat("proj-1")

            assert result == "ghp_test123"
            mock_client.get_secret_value.assert_called_once_with(
                SecretId="cloudcrew/proj-1/github-pat",
            )

    def test_returns_empty_on_not_found(self) -> None:
        """Return empty string when secret doesn't exist."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}},
                "GetSecretValue",
            )

            result = get_github_pat("proj-1")

            assert result == ""

    def test_returns_empty_on_access_denied(self) -> None:
        """Return empty string when access is denied."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.side_effect = ClientError(
                {"Error": {"Code": "AccessDeniedException"}},
                "GetSecretValue",
            )

            result = get_github_pat("proj-1")

            assert result == ""

    def test_returns_empty_on_unexpected_error(self) -> None:
        """Return empty string on unexpected exceptions."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.side_effect = RuntimeError("Network error")

            result = get_github_pat("proj-1")

            assert result == ""


@pytest.mark.unit
class TestStoreAwsCredentials:
    """Test suite for store_aws_credentials()."""

    def test_creates_new_aws_secret(self) -> None:
        """Store AWS credentials by creating a new secret."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            result = store_aws_credentials("proj-1", "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

            assert result is True
            call_args = mock_client.create_secret.call_args
            assert call_args.kwargs["Name"] == "cloudcrew/proj-1/aws-credentials"
            payload = json.loads(call_args.kwargs["SecretString"])
            assert payload["access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
            assert payload["secret_access_key"] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    def test_updates_existing_aws_secret(self) -> None:
        """Fall back to put_secret_value when secret already exists."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = ClientError(
                {"Error": {"Code": "ResourceExistsException"}},
                "CreateSecret",
            )

            result = store_aws_credentials("proj-1", "AKIAIOSFODNN7EXAMPLE", "secretkey1234567890secretkey1234567890")

            assert result is True
            call_args = mock_client.put_secret_value.call_args
            assert call_args.kwargs["SecretId"] == "cloudcrew/proj-1/aws-credentials"
            payload = json.loads(call_args.kwargs["SecretString"])
            assert payload["access_key_id"] == "AKIAIOSFODNN7EXAMPLE"

    def test_store_aws_credentials_handles_failure(self) -> None:
        """Return False when create fails with non-exists error."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = ClientError(
                {"Error": {"Code": "AccessDeniedException"}},
                "CreateSecret",
            )

            result = store_aws_credentials("proj-1", "AKIAIOSFODNN7EXAMPLE", "secretkey")

            assert result is False

    def test_returns_false_on_update_failure(self) -> None:
        """Return False when both create and update fail."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = ClientError(
                {"Error": {"Code": "ResourceExistsException"}},
                "CreateSecret",
            )
            mock_client.put_secret_value.side_effect = ClientError(
                {"Error": {"Code": "InternalServiceError"}},
                "PutSecretValue",
            )

            result = store_aws_credentials("proj-1", "AKIAIOSFODNN7EXAMPLE", "secretkey")

            assert result is False

    def test_returns_false_on_unexpected_error(self) -> None:
        """Return False on unexpected exceptions."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.create_secret.side_effect = RuntimeError("Network error")

            result = store_aws_credentials("proj-1", "AKIAIOSFODNN7EXAMPLE", "secretkey")

            assert result is False


@pytest.mark.unit
class TestGetAwsCredentials:
    """Test suite for get_aws_credentials()."""

    def test_retrieves_aws_credentials(self) -> None:
        """Retrieve AWS credentials from Secrets Manager."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            payload = json.dumps({"access_key_id": "AKIAIOSFODNN7EXAMPLE", "secret_access_key": "wJalrXUtnFEMI"})
            mock_client.get_secret_value.return_value = {"SecretString": payload}

            access_key, secret_key = get_aws_credentials("proj-1")

            assert access_key == "AKIAIOSFODNN7EXAMPLE"
            assert secret_key == "wJalrXUtnFEMI"
            mock_client.get_secret_value.assert_called_once_with(
                SecretId="cloudcrew/proj-1/aws-credentials",
            )

    def test_returns_empty_when_aws_credentials_not_found(self) -> None:
        """Return empty tuple when secret doesn't exist."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException"}},
                "GetSecretValue",
            )

            access_key, secret_key = get_aws_credentials("proj-1")

            assert access_key == ""
            assert secret_key == ""

    def test_returns_empty_on_aws_credentials_error(self) -> None:
        """Return empty tuple on other ClientError."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.side_effect = ClientError(
                {"Error": {"Code": "AccessDeniedException"}},
                "GetSecretValue",
            )

            access_key, secret_key = get_aws_credentials("proj-1")

            assert access_key == ""
            assert secret_key == ""

    def test_returns_empty_on_malformed_json(self) -> None:
        """Return empty tuple when secret contains invalid JSON."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.return_value = {"SecretString": "not-json"}

            access_key, secret_key = get_aws_credentials("proj-1")

            assert access_key == ""
            assert secret_key == ""

    def test_returns_empty_on_unexpected_error(self) -> None:
        """Return empty tuple on unexpected exceptions."""
        with patch("src.state.secrets._secrets_client") as mock_client:
            mock_client.get_secret_value.side_effect = RuntimeError("Network error")

            access_key, secret_key = get_aws_credentials("proj-1")

            assert access_key == ""
            assert secret_key == ""
