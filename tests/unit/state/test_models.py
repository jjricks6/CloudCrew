"""Tests for src/state/models.py."""

import pytest
from pydantic import ValidationError
from src.state.models import InvocationState


@pytest.mark.unit
class TestInvocationState:
    """Verify InvocationState model validation and serialization."""

    def test_valid_construction(self) -> None:
        state = InvocationState(
            project_id="proj-001",
            phase="architecture",
            session_id="proj-001-architecture",
            task_ledger_table="cloudcrew-projects",
            git_repo_url="/tmp/repo",
            knowledge_base_id="kb-123",
            patterns_bucket="cloudcrew-patterns",
        )
        assert state.project_id == "proj-001"
        assert state.phase == "architecture"

    def test_model_dump(self) -> None:
        state = InvocationState(
            project_id="proj-001",
            phase="discovery",
            session_id="sess-001",
            task_ledger_table="projects",
            git_repo_url="/repo",
            knowledge_base_id="",
            patterns_bucket="",
        )
        dumped = state.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["project_id"] == "proj-001"
        assert dumped["phase"] == "discovery"
        assert dumped["session_id"] == "sess-001"

    def test_missing_required_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            InvocationState(  # type: ignore[call-arg]
                project_id="proj-001",
                # missing phase, session_id, etc.
            )

    def test_all_fields_present_in_dump(self) -> None:
        state = InvocationState(
            project_id="p",
            phase="ph",
            session_id="s",
            task_ledger_table="t",
            git_repo_url="g",
            knowledge_base_id="k",
            patterns_bucket="pb",
        )
        dumped = state.model_dump()
        expected_keys = {
            "project_id",
            "phase",
            "session_id",
            "task_ledger_table",
            "git_repo_url",
            "knowledge_base_id",
            "patterns_bucket",
        }
        assert set(dumped.keys()) == expected_keys
