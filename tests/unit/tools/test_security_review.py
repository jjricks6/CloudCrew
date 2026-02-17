"""Tests for src/tools/security_review.py."""

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from src.tools.security_review import _slugify, write_security_review


@pytest.mark.unit
class TestSlugify:
    """Verify _slugify helper."""

    def test_basic_slugify(self) -> None:
        assert _slugify("VPC Security Review") == "vpc-security-review"

    def test_special_characters(self) -> None:
        assert _slugify("Review: S3 (Production)") == "review-s3-production"

    def test_extra_whitespace(self) -> None:
        assert _slugify("  multiple   spaces  ") == "multiple-spaces"


@pytest.mark.unit
class TestWriteSecurityReview:
    """Verify write_security_review tool."""

    def test_creates_review_file(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.security_review.git.Repo", return_value=mock_repo):
            result = write_security_review(
                title="VPC Module Review",
                scope="infra/modules/vpc",
                verdict="CONDITIONAL_PASS",
                critical_count=0,
                high_count=1,
                medium_count=2,
                low_count=3,
                findings="- HIGH: Open SSH port",
                recommendations="- Restrict SSH to VPN CIDR",
                tool_context=mock_context,
            )

        assert "Committed security review" in result
        # Verify file was created
        reviews_dir = tmp_path / "security" / "reviews"
        assert reviews_dir.exists()
        review_files = list(reviews_dir.glob("*.md"))
        assert len(review_files) == 1
        content = review_files[0].read_text()
        assert "VPC Module Review" in content
        assert "CONDITIONAL_PASS" in content
        assert "Open SSH port" in content

    def test_commits_with_correct_message(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.security_review.git.Repo", return_value=mock_repo):
            write_security_review(
                title="S3 Review",
                scope="infra/modules/s3",
                verdict="PASS",
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings="No issues found.",
                recommendations="None.",
                tool_context=mock_context,
            )

        mock_repo.index.commit.assert_called_once()
        commit_msg = mock_repo.index.commit.call_args[0][0]
        assert "S3 Review" in commit_msg

    def test_file_naming_includes_date(self, tmp_path: Path) -> None:
        mock_repo = MagicMock()
        mock_repo.working_dir = str(tmp_path)
        mock_context = MagicMock()
        mock_context.invocation_state = {"git_repo_url": str(tmp_path)}

        with patch("src.tools.security_review.git.Repo", return_value=mock_repo):
            result = write_security_review(
                title="Test Review",
                scope="infra/",
                verdict="PASS",
                critical_count=0,
                high_count=0,
                medium_count=0,
                low_count=0,
                findings="None.",
                recommendations="None.",
                tool_context=mock_context,
            )

        # Filename should match YYYYMMDD-slug.md pattern
        assert re.search(r"\d{8}-test-review\.md", result)
