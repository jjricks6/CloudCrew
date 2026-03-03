"""Tests for src/phases/review_utils.py."""

import pytest


@pytest.mark.unit
class TestBuildReviewContext:
    """Verify build_review_context returns correct messages per phase."""

    def test_known_phase(self) -> None:
        from src.phases.review_utils import build_review_context

        result = build_review_context("ARCHITECTURE")
        assert "Architecture" in result["opening_message"]
        assert "closing_message" in result
        assert result["summary_path"] == "docs/phase-summaries/architecture.md"

    def test_unknown_phase_fallback(self) -> None:
        from src.phases.review_utils import build_review_context

        result = build_review_context("UNKNOWN")
        assert "UNKNOWN" in result["opening_message"]
        assert result["summary_path"] == "docs/phase-summaries/unknown.md"

    def test_all_known_phases(self) -> None:
        from src.phases.review_utils import build_review_context

        for phase in ["DISCOVERY", "ARCHITECTURE", "POC", "PRODUCTION", "HANDOFF"]:
            result = build_review_context(phase)
            assert result["opening_message"]
            assert result["closing_message"]
            assert result["summary_path"] == f"docs/phase-summaries/{phase.lower()}.md"
