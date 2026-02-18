"""Tests for src/state/models.py."""

import pytest
from pydantic import ValidationError
from src.state.models import (
    Assumption,
    Blocker,
    Decision,
    DeliverableItem,
    Fact,
    InvocationState,
    ParsedSOW,
    Phase,
    PhaseStatus,
    TaskLedger,
)


@pytest.mark.unit
class TestPhaseEnum:
    """Verify Phase enum."""

    def test_all_phases_defined(self) -> None:
        expected = {"DISCOVERY", "ARCHITECTURE", "POC", "PRODUCTION", "HANDOFF", "RETROSPECTIVE"}
        assert {p.value for p in Phase} == expected

    def test_str_value(self) -> None:
        assert str(Phase.DISCOVERY) == "DISCOVERY"
        assert Phase.DISCOVERY == "DISCOVERY"


@pytest.mark.unit
class TestPhaseStatusEnum:
    """Verify PhaseStatus enum."""

    def test_all_statuses_defined(self) -> None:
        expected = {"IN_PROGRESS", "AWAITING_APPROVAL", "APPROVED", "REVISION_REQUESTED"}
        assert {s.value for s in PhaseStatus} == expected

    def test_str_value(self) -> None:
        assert str(PhaseStatus.IN_PROGRESS) == "IN_PROGRESS"


@pytest.mark.unit
class TestFactModel:
    """Verify Fact model."""

    def test_valid_construction(self) -> None:
        fact = Fact(description="Uses DynamoDB", source="SOW", timestamp="2025-01-01T00:00:00Z")
        assert fact.description == "Uses DynamoDB"
        assert fact.source == "SOW"

    def test_missing_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            Fact(description="fact")  # type: ignore[call-arg]


@pytest.mark.unit
class TestAssumptionModel:
    """Verify Assumption model."""

    def test_valid_construction(self) -> None:
        assumption = Assumption(description="Low traffic", confidence="HIGH", timestamp="2025-01-01T00:00:00Z")
        assert assumption.confidence == "HIGH"


@pytest.mark.unit
class TestDecisionModel:
    """Verify Decision model."""

    def test_valid_construction(self) -> None:
        decision = Decision(
            description="Use Aurora",
            rationale="Managed service",
            made_by="sa",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert decision.made_by == "sa"
        assert decision.adr_path == ""

    def test_optional_adr_path(self) -> None:
        decision = Decision(
            description="d",
            rationale="r",
            made_by="sa",
            timestamp="t",
            adr_path="docs/architecture/adr-001.md",
        )
        assert decision.adr_path == "docs/architecture/adr-001.md"


@pytest.mark.unit
class TestBlockerModel:
    """Verify Blocker model."""

    def test_valid_construction(self) -> None:
        blocker = Blocker(
            description="VPN access needed",
            assigned_to="infra",
            status="OPEN",
            timestamp="2025-01-01T00:00:00Z",
        )
        assert blocker.status == "OPEN"


@pytest.mark.unit
class TestDeliverableItemModel:
    """Verify DeliverableItem model."""

    def test_valid_construction(self) -> None:
        item = DeliverableItem(name="VPC module", git_path="infra/modules/vpc", status="IN_PROGRESS")
        assert item.name == "VPC module"


@pytest.mark.unit
class TestTaskLedger:
    """Verify TaskLedger model."""

    def test_minimal_construction(self) -> None:
        ledger = TaskLedger(project_id="proj-001")
        assert ledger.project_id == "proj-001"
        assert ledger.current_phase == Phase.DISCOVERY
        assert ledger.phase_status == PhaseStatus.IN_PROGRESS
        assert ledger.facts == []
        assert ledger.assumptions == []
        assert ledger.decisions == []
        assert ledger.blockers == []
        assert ledger.deliverables == {}

    def test_full_construction(self) -> None:
        ledger = TaskLedger(
            project_id="proj-001",
            project_name="Acme Cloud",
            customer="Acme Corp",
            current_phase=Phase.ARCHITECTURE,
            phase_status=PhaseStatus.APPROVED,
            facts=[Fact(description="d", source="s", timestamp="t")],
            deliverables={"ARCHITECTURE": [DeliverableItem(name="n", git_path="p", status="COMPLETE")]},
        )
        assert ledger.current_phase == Phase.ARCHITECTURE
        assert len(ledger.facts) == 1
        assert len(ledger.deliverables["ARCHITECTURE"]) == 1


@pytest.mark.unit
class TestParsedSOW:
    """Verify ParsedSOW model."""

    def test_empty_construction(self) -> None:
        sow = ParsedSOW()
        assert sow.objectives == []
        assert sow.requirements == []
        assert sow.constraints == []
        assert sow.deliverables == []
        assert sow.acceptance_criteria == []
        assert sow.timeline == ""

    def test_full_construction(self) -> None:
        sow = ParsedSOW(
            objectives=["Migrate to cloud"],
            requirements=["Multi-AZ"],
            constraints=["Budget < $10k/mo"],
            deliverables=["Terraform modules"],
            acceptance_criteria=["99.9% uptime"],
            timeline="Q1 2025",
        )
        assert len(sow.objectives) == 1
        assert sow.timeline == "Q1 2025"


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
            "stm_memory_id",
            "ltm_memory_id",
        }
        assert set(dumped.keys()) == expected_keys

    def test_memory_id_defaults(self) -> None:
        state = InvocationState(
            project_id="p",
            phase="ph",
            session_id="s",
            task_ledger_table="t",
            git_repo_url="g",
            knowledge_base_id="k",
            patterns_bucket="pb",
        )
        assert state.stm_memory_id == ""
        assert state.ltm_memory_id == ""

    def test_memory_ids_set(self) -> None:
        state = InvocationState(
            project_id="p",
            phase="ph",
            session_id="s",
            task_ledger_table="t",
            git_repo_url="g",
            knowledge_base_id="k",
            patterns_bucket="pb",
            stm_memory_id="stm-001",
            ltm_memory_id="ltm-001",
        )
        assert state.stm_memory_id == "stm-001"
        assert state.ltm_memory_id == "ltm-001"
