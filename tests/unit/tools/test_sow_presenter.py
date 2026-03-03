"""Tests for src/tools/sow_presenter.py.

Uses the real interrupt_response_cache to verify the full lifecycle:
set_response → present_sow_for_approval reads and clears → cache is empty.
"""

from unittest.mock import MagicMock

import pytest
from src.state.interrupt_response_cache import get_and_clear_response, set_response
from src.tools.sow_presenter import present_sow_for_approval


@pytest.mark.unit
class TestPresentSowForApproval:
    """Verify present_sow_for_approval tool behavior with real cache lifecycle."""

    def setup_method(self) -> None:
        """Clear any stale cache state before each test."""
        get_and_clear_response()

    def test_returns_approved_response(self) -> None:
        """Tool reads 'Approved' from the real cache."""
        set_response("Approved")
        result = present_sow_for_approval(sow_content="# SOW\nDetails", tool_context=MagicMock())
        assert result == "Approved"

    def test_returns_revision_feedback(self) -> None:
        """Tool reads revision feedback from the real cache."""
        set_response("Please add a compliance section")
        result = present_sow_for_approval(sow_content="# SOW\nDetails", tool_context=MagicMock())
        assert result == "Please add a compliance section"

    def test_clears_cache_after_read(self) -> None:
        """Cache is empty after tool reads the response."""
        set_response("Approved")
        present_sow_for_approval(sow_content="# SOW\nDetails", tool_context=MagicMock())
        assert get_and_clear_response() == ""

    def test_returns_fallback_when_cache_empty(self) -> None:
        """Tool returns fallback message when no response is cached."""
        result = present_sow_for_approval(sow_content="# SOW\nDetails", tool_context=MagicMock())
        assert "No response" in result
