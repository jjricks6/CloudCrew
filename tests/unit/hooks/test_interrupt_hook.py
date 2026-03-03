"""Tests for src/hooks/interrupt_hook.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.interrupt_hook import CustomerInterruptHook


@pytest.mark.unit
class TestRegister:
    """Verify hook registration."""

    def test_registers_one_callback(self) -> None:
        hook = CustomerInterruptHook()
        registry = MagicMock()
        hook.register_hooks(registry)
        assert registry.add_callback.call_count == 1


@pytest.mark.unit
class TestHandleAskCustomer:
    """Verify ask_customer tool interception."""

    def _make_event(self, tool_name: str = "ask_customer", question: str = "How many users?") -> MagicMock:
        event = MagicMock()
        event.tool_use = {
            "name": tool_name,
            "input": {"question": question},
        }
        return event

    def test_ignores_non_ask_customer_tools(self) -> None:
        hook = CustomerInterruptHook()
        event = self._make_event(tool_name="git_read")

        # Should not call event.interrupt
        hook._on_before_tool_call(event)
        event.interrupt.assert_not_called()

    def test_calls_interrupt_with_question(self) -> None:
        hook = CustomerInterruptHook()
        event = self._make_event(question="What compliance requirements?")
        event.interrupt.return_value = "SOC2 and HIPAA"

        with patch("src.hooks.interrupt_hook.set_response") as mock_set:
            hook._on_before_tool_call(event)

        event.interrupt.assert_called_once_with("ask_customer", reason="What compliance requirements?")
        mock_set.assert_called_once_with("SOC2 and HIPAA")

    def test_caches_response_on_resume(self) -> None:
        hook = CustomerInterruptHook()
        event = self._make_event(question="Budget range?")
        event.interrupt.return_value = "$50k-100k"

        with patch("src.hooks.interrupt_hook.set_response") as mock_set:
            hook._on_before_tool_call(event)

        mock_set.assert_called_once_with("$50k-100k")

    def test_handles_empty_question(self) -> None:
        hook = CustomerInterruptHook()
        event = self._make_event(question="")
        event.interrupt.return_value = "Some response"

        with patch("src.hooks.interrupt_hook.set_response") as mock_set:
            hook._on_before_tool_call(event)

        event.interrupt.assert_called_once_with("ask_customer", reason="")
        mock_set.assert_called_once_with("Some response")


@pytest.mark.unit
class TestHandlePresentSowForApproval:
    """Verify present_sow_for_approval tool interception."""

    def _make_event(
        self,
        tool_name: str = "present_sow_for_approval",
        sow_content: str = "# SOW\nProject details",
    ) -> MagicMock:
        event = MagicMock()
        event.tool_use = {"name": tool_name, "input": {"sow_content": sow_content}}
        return event

    def test_intercepts_sow_tool_with_content(self) -> None:
        hook = CustomerInterruptHook()
        event = self._make_event(sow_content="# My SOW")
        event.interrupt.return_value = "Approved"

        with patch("src.hooks.interrupt_hook.set_response") as mock_set:
            hook._on_before_tool_call(event)

        event.interrupt.assert_called_once_with(
            "present_sow_for_approval",
            reason="sow_review:# My SOW",
        )
        mock_set.assert_called_once_with("Approved")

    def test_intercepts_sow_tool_without_content(self) -> None:
        hook = CustomerInterruptHook()
        event = self._make_event(sow_content="")
        event.interrupt.return_value = "Approved"

        with patch("src.hooks.interrupt_hook.set_response") as mock_set:
            hook._on_before_tool_call(event)

        event.interrupt.assert_called_once_with(
            "present_sow_for_approval",
            reason="sow_review:",
        )
        mock_set.assert_called_once_with("Approved")

    def test_caches_revision_feedback(self) -> None:
        hook = CustomerInterruptHook()
        event = self._make_event()
        event.interrupt.return_value = "Add compliance section"

        with patch("src.hooks.interrupt_hook.set_response") as mock_set:
            hook._on_before_tool_call(event)

        mock_set.assert_called_once_with("Add compliance section")
