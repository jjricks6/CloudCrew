"""Tests for src/hooks/memory_hook.py."""

from unittest.mock import MagicMock, patch

import pytest
from src.hooks.memory_hook import MemoryHook, _extract_record_text


@pytest.mark.unit
class TestMemoryHookInit:
    """Verify MemoryHook initialization."""

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_creates_clients_when_ids_provided(self, mock_client_cls: MagicMock) -> None:
        hook = MemoryHook(stm_memory_id="stm-001", ltm_memory_id="ltm-001")

        assert hook._stm is not None
        assert hook._ltm is not None
        assert mock_client_cls.call_count == 2

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_no_clients_when_empty_ids(self, mock_client_cls: MagicMock) -> None:
        hook = MemoryHook()

        assert hook._stm is None
        assert hook._ltm is None
        mock_client_cls.assert_not_called()


@pytest.mark.unit
class TestMemoryHookRegister:
    """Verify hook registration."""

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_registers_callbacks(self, _mock_client_cls: MagicMock) -> None:
        hook = MemoryHook()
        mock_registry = MagicMock()

        hook.register_hooks(mock_registry)

        assert mock_registry.add_callback.call_count == 2


@pytest.mark.unit
class TestLoadContext:
    """Verify load_context hook."""

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_skips_when_no_ltm(self, _mock_client_cls: MagicMock) -> None:
        hook = MemoryHook()
        event = MagicMock()
        event.invocation_state = {"project_id": "proj-001"}

        # Should not raise
        hook.load_context(event)

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_skips_when_no_project_id(self, mock_client_cls: MagicMock) -> None:
        mock_ltm = MagicMock()
        mock_client_cls.return_value = mock_ltm

        hook = MemoryHook(ltm_memory_id="ltm-001")
        event = MagicMock()
        event.invocation_state = {}

        hook.load_context(event)

        mock_ltm.retrieve.assert_not_called()

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_loads_and_injects_context(self, mock_client_cls: MagicMock) -> None:
        mock_ltm = MagicMock()
        mock_ltm.retrieve.return_value = [
            {"content": {"text": "Decision: Use DynamoDB"}},
        ]
        mock_client_cls.return_value = mock_ltm

        hook = MemoryHook(ltm_memory_id="ltm-001")
        event = MagicMock()
        event.invocation_state = {"project_id": "proj-001"}
        event.messages = []

        hook.load_context(event)

        assert len(event.messages) == 1
        assert "Previous Phases" in event.messages[0]["content"][0]["text"]

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_handles_retrieve_error_gracefully(self, mock_client_cls: MagicMock) -> None:
        mock_ltm = MagicMock()
        mock_ltm.retrieve.side_effect = Exception("Connection failed")
        mock_client_cls.return_value = mock_ltm

        hook = MemoryHook(ltm_memory_id="ltm-001")
        event = MagicMock()
        event.invocation_state = {"project_id": "proj-001"}
        event.messages = []

        # Should not raise
        hook.load_context(event)

        # Messages should be unchanged
        assert len(event.messages) == 0


@pytest.mark.unit
class TestSaveContext:
    """Verify save_context hook."""

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_skips_when_no_stm(self, _mock_client_cls: MagicMock) -> None:
        hook = MemoryHook()
        event = MagicMock()
        event.invocation_state = {"session_id": "sess-001"}

        # Should not raise
        hook.save_context(event)

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_skips_when_no_session_id(self, mock_client_cls: MagicMock) -> None:
        mock_stm = MagicMock()
        mock_client_cls.return_value = mock_stm

        hook = MemoryHook(stm_memory_id="stm-001")
        event = MagicMock()
        event.invocation_state = {}

        hook.save_context(event)

        mock_stm.save_events.assert_not_called()

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_saves_result_content(self, mock_client_cls: MagicMock) -> None:
        mock_stm = MagicMock()
        mock_client_cls.return_value = mock_stm

        hook = MemoryHook(stm_memory_id="stm-001")
        event = MagicMock()
        event.invocation_state = {"session_id": "sess-001"}
        event.result.message = {"content": [{"text": "Agent response text"}]}
        event.agent.name = "pm"

        hook.save_context(event)

        mock_stm.save_events.assert_called_once()

    @patch("src.hooks.memory_hook.MemoryClient")
    def test_handles_save_error_gracefully(self, mock_client_cls: MagicMock) -> None:
        mock_stm = MagicMock()
        mock_stm.save_events.side_effect = Exception("Save failed")
        mock_client_cls.return_value = mock_stm

        hook = MemoryHook(stm_memory_id="stm-001")
        event = MagicMock()
        event.invocation_state = {"session_id": "sess-001"}
        event.result.message = {"content": [{"text": "text"}]}
        event.agent.name = "pm"

        # Should not raise
        hook.save_context(event)


@pytest.mark.unit
class TestExtractRecordText:
    """Verify _extract_record_text helper."""

    def test_dict_content(self) -> None:
        assert _extract_record_text({"content": {"text": "Hello"}}) == "Hello"

    def test_string_content(self) -> None:
        assert _extract_record_text({"content": "Hello"}) == "Hello"

    def test_missing_content(self) -> None:
        assert _extract_record_text({}) == ""

    def test_other_content_type(self) -> None:
        assert _extract_record_text({"content": 123}) == ""
