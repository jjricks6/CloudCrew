"""Tests for src/tools/security_tools.py."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.tools.security_tools import _format_checkov_results, checkov_scan


@pytest.mark.unit
class TestFormatCheckovResults:
    """Verify Checkov output parsing."""

    def test_valid_json_with_failures(self) -> None:
        data = {
            "summary": {"passed": 5, "failed": 2, "skipped": 0},
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_18",
                        "name": "Ensure S3 bucket has access logging",
                        "severity": "HIGH",
                        "resource": "aws_s3_bucket.data",
                        "file_path": "/main.tf",
                    },
                    {
                        "check_id": "CKV_AWS_19",
                        "name": "Ensure S3 bucket has encryption",
                        "severity": "CRITICAL",
                        "resource": "aws_s3_bucket.data",
                        "file_path": "/main.tf",
                    },
                ]
            },
        }
        result = _format_checkov_results(json.dumps(data))
        assert "Passed: 5" in result
        assert "Failed: 2" in result
        assert "CKV_AWS_18" in result
        assert "HIGH" in result
        assert "CRITICAL" in result

    def test_valid_json_no_failures(self) -> None:
        data = {
            "summary": {"passed": 10, "failed": 0, "skipped": 1},
            "results": {"failed_checks": []},
        }
        result = _format_checkov_results(json.dumps(data))
        assert "Passed: 10" in result
        assert "Failed: 0" in result

    def test_unparseable_output(self) -> None:
        result = _format_checkov_results("not valid json")
        assert "Could not parse" in result
        assert "not valid json" in result

    def test_list_format(self) -> None:
        data = [
            {
                "summary": {"passed": 3, "failed": 1, "skipped": 0},
                "results": {
                    "failed_checks": [
                        {
                            "check_id": "CKV_AWS_1",
                            "name": "Test check",
                            "severity": "MEDIUM",
                            "resource": "aws_vpc.main",
                            "file_path": "/vpc.tf",
                        }
                    ]
                },
            }
        ]
        result = _format_checkov_results(json.dumps(data))
        assert "Passed: 3" in result
        assert "CKV_AWS_1" in result


@pytest.mark.unit
class TestCheckovScan:
    """Verify checkov_scan tool."""

    def test_missing_repo_url(self) -> None:
        mock_context = MagicMock()
        mock_context.invocation_state = {}

        result = checkov_scan("infra/", mock_context)
        assert "Error" in result

    def test_missing_directory(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.security_tools._get_repo", return_value=mock_repo):
            result = checkov_scan("nonexistent/", mock_context)

        assert "Error" in result

    def test_checkov_not_found(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with (
            patch("src.tools.security_tools._get_repo", return_value=mock_repo),
            patch("src.tools.security_tools.subprocess.run", side_effect=FileNotFoundError),
        ):
            result = checkov_scan("infra", mock_context)

        assert "checkov CLI not found" in result

    def test_checkov_timeout(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with (
            patch("src.tools.security_tools._get_repo", return_value=mock_repo),
            patch(
                "src.tools.security_tools.subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd="checkov", timeout=120),
            ),
        ):
            result = checkov_scan("infra", mock_context)

        assert "timed out" in result

    def test_successful_scan(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        checkov_output = json.dumps(
            {
                "summary": {"passed": 8, "failed": 1, "skipped": 0},
                "results": {
                    "failed_checks": [
                        {
                            "check_id": "CKV_AWS_18",
                            "name": "S3 access logging",
                            "severity": "HIGH",
                            "resource": "aws_s3_bucket.data",
                            "file_path": "/main.tf",
                        }
                    ]
                },
            }
        )
        mock_result = MagicMock()
        mock_result.stdout = checkov_output
        mock_result.returncode = 1

        with (
            patch("src.tools.security_tools._get_repo", return_value=mock_repo),
            patch("src.tools.security_tools.subprocess.run", return_value=mock_result),
        ):
            result = checkov_scan("infra", mock_context)

        assert "Passed: 8" in result
        assert "CKV_AWS_18" in result

    def test_no_output(self, tmp_path: Path) -> None:
        tf_dir = tmp_path / "infra"
        tf_dir.mkdir()
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        with (
            patch("src.tools.security_tools._get_repo", return_value=mock_repo),
            patch("src.tools.security_tools.subprocess.run", return_value=mock_result),
        ):
            result = checkov_scan("infra", mock_context)

        assert "no output" in result.lower()
