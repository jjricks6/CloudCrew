"""Tests for src/phases/artifact_handlers.py."""

import json
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError

TEST_USER_ID = "test-user-123"


def _event(
    path_params: dict[str, str],
    query_params: dict[str, str] | None = None,
) -> dict[str, object]:
    event: dict[str, object] = {
        "pathParameters": path_params,
        "requestContext": {"authorizer": {"claims": {"sub": TEST_USER_ID}}},
    }
    if query_params:
        event["queryStringParameters"] = query_params
    return event


@pytest.mark.unit
class TestArtifactContentHandler:
    """Verify artifact_content_handler behaviour."""

    def test_rejects_missing_project_id(self) -> None:
        from src.phases.artifact_handlers import artifact_content_handler

        result = artifact_content_handler({"pathParameters": {}})
        assert result["statusCode"] == 400

    @patch("src.phases.auth_utils.read_ledger")
    def test_rejects_missing_path(self, mock_read: MagicMock) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        result = artifact_content_handler(_event({"id": "p1"}))
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "path" in body["error"]

    @patch("src.phases.auth_utils.read_ledger")
    def test_rejects_disallowed_prefix(self, mock_read: MagicMock) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        result = artifact_content_handler(_event({"id": "p1"}, {"path": "etc/passwd"}))
        assert result["statusCode"] == 403

    @patch("src.phases.artifact_handlers.SOW_BUCKET", "")
    @patch("src.phases.auth_utils.read_ledger")
    def test_503_when_bucket_not_configured(self, mock_read: MagicMock) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        result = artifact_content_handler(_event({"id": "p1"}, {"path": "docs/sow.md"}))
        assert result["statusCode"] == 503

    @patch("src.phases.artifact_handlers.boto3")
    @patch("src.phases.artifact_handlers.SOW_BUCKET", "test-bucket")
    @patch("src.phases.auth_utils.read_ledger")
    def test_returns_file_not_found(self, mock_read: MagicMock, mock_boto3: MagicMock) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_s3.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
            "GetObject",
        )

        result = artifact_content_handler(_event({"id": "p1"}, {"path": "docs/nonexistent.md"}))
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["exists"] is False

    @patch("src.phases.artifact_handlers.boto3")
    @patch("src.phases.artifact_handlers.SOW_BUCKET", "test-bucket")
    @patch("src.phases.auth_utils.read_ledger")
    def test_returns_artifact_content(self, mock_read: MagicMock, mock_boto3: MagicMock) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_body = MagicMock()
        mock_body.read.return_value = b"# Phase Summary\nAll done."
        mock_s3.get_object.return_value = {"Body": mock_body}

        result = artifact_content_handler(_event({"id": "p1"}, {"path": "docs/phase-summaries/architecture.md"}))
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["exists"] is True
        assert body["content"] == "# Phase Summary\nAll done."

    @patch("src.phases.auth_utils.read_ledger")
    def test_rejects_path_traversal(self, mock_read: MagicMock) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        result = artifact_content_handler(_event({"id": "p1"}, {"path": "docs/../../../etc/passwd"}))
        assert result["statusCode"] == 403


@pytest.mark.unit
class TestArtifactListHandler:
    """Verify artifact listing via action=list."""

    @patch("src.phases.artifact_handlers.boto3")
    @patch("src.phases.artifact_handlers.SOW_BUCKET", "test-bucket")
    @patch("src.phases.auth_utils.read_ledger")
    def test_lists_artifacts_from_s3(
        self,
        mock_read: MagicMock,
        mock_boto3: MagicMock,
    ) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "projects/p1/artifacts/docs/phase-summaries/architecture.md"},
                    {"Key": "projects/p1/artifacts/docs/architecture/system-design.md"},
                    {"Key": "projects/p1/artifacts/security/threat-model.md"},
                ]
            }
        ]

        result = artifact_content_handler(_event({"id": "p1"}, {"action": "list"}))
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        artifacts = body["artifacts"]
        assert len(artifacts) == 3
        # Phase Summary should be first
        assert artifacts[0]["name"] == "Phase Summary"
        assert artifacts[0]["path"] == "docs/phase-summaries/architecture.md"

    @patch("src.phases.artifact_handlers.boto3")
    @patch("src.phases.artifact_handlers.SOW_BUCKET", "test-bucket")
    @patch("src.phases.auth_utils.read_ledger")
    def test_excludes_non_allowed_prefixes(
        self,
        mock_read: MagicMock,
        mock_boto3: MagicMock,
    ) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [
            {
                "Contents": [
                    {"Key": "projects/p1/artifacts/docs/sow.md"},
                    {"Key": "projects/p1/artifacts/.git/config"},
                ]
            }
        ]

        result = artifact_content_handler(_event({"id": "p1"}, {"action": "list"}))
        body = json.loads(result["body"])
        # .git/ is not in allowed prefixes — should be excluded
        assert len(body["artifacts"]) == 1
        assert body["artifacts"][0]["path"] == "docs/sow.md"

    @patch("src.phases.artifact_handlers.boto3")
    @patch("src.phases.artifact_handlers.SOW_BUCKET", "test-bucket")
    @patch("src.phases.auth_utils.read_ledger")
    def test_returns_empty_list_when_no_artifacts(
        self,
        mock_read: MagicMock,
        mock_boto3: MagicMock,
    ) -> None:
        from src.phases.artifact_handlers import artifact_content_handler
        from src.state.models import TaskLedger

        mock_read.return_value = TaskLedger(project_id="p1", owner_id=TEST_USER_ID)
        mock_s3 = MagicMock()
        mock_boto3.client.return_value = mock_s3
        mock_paginator = MagicMock()
        mock_s3.get_paginator.return_value = mock_paginator
        mock_paginator.paginate.return_value = [{"Contents": []}]

        result = artifact_content_handler(_event({"id": "p1"}, {"action": "list"}))
        body = json.loads(result["body"])
        assert body["artifacts"] == []


@pytest.mark.unit
class TestPathToDisplayName:
    """Verify _path_to_display_name helper."""

    def test_phase_summary_label(self) -> None:
        from src.phases.artifact_handlers import _path_to_display_name

        assert _path_to_display_name("docs/phase-summaries/architecture.md") == "Phase Summary"
        assert _path_to_display_name("docs/phase-summaries/discovery.md") == "Phase Summary"

    def test_kebab_case(self) -> None:
        from src.phases.artifact_handlers import _path_to_display_name

        assert _path_to_display_name("docs/architecture/system-design.md") == "System Design"

    def test_snake_case(self) -> None:
        from src.phases.artifact_handlers import _path_to_display_name

        assert _path_to_display_name("security/threat_model.md") == "Threat Model"

    def test_simple_filename(self) -> None:
        from src.phases.artifact_handlers import _path_to_display_name

        assert _path_to_display_name("docs/project-plan/sow.md") == "Sow"
