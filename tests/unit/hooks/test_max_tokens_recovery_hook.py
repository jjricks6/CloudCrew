"""Tests for src/hooks/max_tokens_recovery_hook.py."""

import logging
from unittest.mock import MagicMock

import pytest
from src.hooks.max_tokens_recovery_hook import (
    _RETRY_GUIDANCE,
    MAX_RETRIES,
    MaxTokensRecoveryHook,
)


@pytest.mark.unit
class TestRegister:
    """Verify hook registration."""

    def test_registers_one_callback(self) -> None:
        hook = MaxTokensRecoveryHook()
        registry = MagicMock()
        hook.register_hooks(registry)
        assert registry.add_callback.call_count == 1


@pytest.mark.unit
class TestMaxTokensRecovery:
    """Verify the max_tokens recovery behaviour."""

    def _make_event(self, stop_reason: str = "max_tokens", agent_name: str = "infra") -> MagicMock:
        """Create a mock AfterModelCallEvent."""
        event = MagicMock()
        event.stop_response.stop_reason = stop_reason
        event.agent.name = agent_name
        event.agent.messages = []
        event.retry = False
        return event

    def test_retry_on_first_max_tokens(self) -> None:
        hook = MaxTokensRecoveryHook()
        event = self._make_event()

        hook._on_after_model_call(event)

        assert event.retry is True
        # Should have injected 2 messages: assistant + user guidance
        assert len(event.agent.messages) == 2
        assert event.agent.messages[0]["role"] == "assistant"
        assert event.agent.messages[1]["role"] == "user"
        assert _RETRY_GUIDANCE in event.agent.messages[1]["content"][0]["text"]

    def test_retry_up_to_max_retries(self) -> None:
        hook = MaxTokensRecoveryHook()

        for i in range(MAX_RETRIES):
            event = self._make_event()
            hook._on_after_model_call(event)
            assert event.retry is True, f"Expected retry on attempt {i + 1}"

    def test_stops_retrying_after_max_retries(self) -> None:
        hook = MaxTokensRecoveryHook()

        # Exhaust retries
        for _ in range(MAX_RETRIES):
            event = self._make_event()
            hook._on_after_model_call(event)

        # Next attempt should NOT retry
        event = self._make_event()
        hook._on_after_model_call(event)
        assert event.retry is False

    def test_success_resets_retry_counter(self) -> None:
        hook = MaxTokensRecoveryHook()

        # Use one retry
        event = self._make_event()
        hook._on_after_model_call(event)
        assert event.retry is True

        # Successful call (stop_reason != "max_tokens")
        success_event = self._make_event(stop_reason="end_turn")
        hook._on_after_model_call(success_event)
        assert success_event.retry is False

        # Should have full retries available again
        for _ in range(MAX_RETRIES):
            event = self._make_event()
            hook._on_after_model_call(event)
            assert event.retry is True

    def test_per_agent_retry_tracking(self) -> None:
        hook = MaxTokensRecoveryHook()

        # Exhaust retries for "infra"
        for _ in range(MAX_RETRIES):
            event = self._make_event(agent_name="infra")
            hook._on_after_model_call(event)

        # "infra" is exhausted
        event = self._make_event(agent_name="infra")
        hook._on_after_model_call(event)
        assert event.retry is False

        # "data" agent still has retries
        event = self._make_event(agent_name="data")
        hook._on_after_model_call(event)
        assert event.retry is True

    def test_no_action_when_stop_response_is_none(self) -> None:
        hook = MaxTokensRecoveryHook()
        event = MagicMock()
        event.stop_response = None
        event.retry = False

        hook._on_after_model_call(event)
        assert event.retry is False

    def test_no_action_on_end_turn(self) -> None:
        hook = MaxTokensRecoveryHook()
        event = self._make_event(stop_reason="end_turn")

        hook._on_after_model_call(event)
        assert event.retry is False
        assert len(event.agent.messages) == 0

    def test_logs_warning_on_retry(self, caplog: pytest.LogCaptureFixture) -> None:
        hook = MaxTokensRecoveryHook()
        event = self._make_event()

        with caplog.at_level(logging.WARNING, logger="src.hooks.max_tokens_recovery_hook"):
            hook._on_after_model_call(event)

        assert "max_tokens_recovery" in caplog.text
        assert "retry 1" in caplog.text

    def test_logs_error_when_exhausted(self, caplog: pytest.LogCaptureFixture) -> None:
        hook = MaxTokensRecoveryHook()

        # Exhaust retries
        for _ in range(MAX_RETRIES):
            event = self._make_event()
            hook._on_after_model_call(event)

        # Final attempt should log error
        event = self._make_event()
        with caplog.at_level(logging.ERROR, logger="src.hooks.max_tokens_recovery_hook"):
            hook._on_after_model_call(event)

        assert "exhausted" in caplog.text
