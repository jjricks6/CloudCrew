"""Tests for src/state/interrupt_response_cache.py."""

import pytest
from src.state.interrupt_response_cache import get_and_clear_response, set_response


@pytest.mark.unit
class TestInterruptResponseCache:
    """Verify in-process interrupt response cache."""

    def setup_method(self) -> None:
        """Clear cache before each test."""
        get_and_clear_response()

    def test_set_and_get_response(self) -> None:
        set_response("About 10,000 users")
        assert get_and_clear_response() == "About 10,000 users"

    def test_get_clears_after_read(self) -> None:
        set_response("Yes, HIPAA compliant")
        assert get_and_clear_response() == "Yes, HIPAA compliant"
        assert get_and_clear_response() == ""

    def test_empty_when_no_response_set(self) -> None:
        assert get_and_clear_response() == ""

    def test_overwrite_replaces_previous(self) -> None:
        set_response("first")
        set_response("second")
        assert get_and_clear_response() == "second"
