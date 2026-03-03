"""Tests for src/tools/interrupt_tools.py.

Uses the real interrupt_response_cache to verify the full lifecycle:
set_response → ask_customer reads and clears → cache is empty.
"""

import pytest
from src.state.interrupt_response_cache import get_and_clear_response, set_response
from src.tools.interrupt_tools import ask_customer


@pytest.mark.unit
class TestAskCustomer:
    """Verify ask_customer tool behavior with real cache lifecycle."""

    def setup_method(self) -> None:
        """Clear any stale cache state before each test."""
        get_and_clear_response()

    def test_returns_cached_response(self) -> None:
        """Tool reads from real cache and returns the stored response."""
        set_response("About 10,000 users")
        result = ask_customer(question="How many users?")
        assert result == "About 10,000 users"

    def test_clears_cache_after_read(self) -> None:
        """Cache is empty after tool reads the response."""
        set_response("HIPAA required")
        ask_customer(question="Compliance?")
        assert get_and_clear_response() == ""

    def test_returns_fallback_when_cache_empty(self) -> None:
        """Tool returns fallback message when no response is cached."""
        result = ask_customer(question="What budget?")
        assert "No response" in result
