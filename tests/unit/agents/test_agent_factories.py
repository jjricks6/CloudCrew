"""Parametrized tests for all 7 agent factory functions.

Each agent factory is tested against a declarative spec that defines the
expected name, model, system prompt keyword, tool identities, hook types,
and prompt sections.  Tool verification is by function __name__ (not count),
so swapping the wrong tool into an agent will fail the test.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from unittest.mock import patch

import pytest
from src.hooks.interrupt_hook import CustomerInterruptHook

# ---------------------------------------------------------------------------
# Agent specification dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentSpec:
    """Declarative specification for one agent factory."""

    module: str
    factory: str
    prompt_constant: str
    name: str
    model_name: str  # "OPUS" or "SONNET"
    prompt_keyword: str
    expected_tools: frozenset[str]
    expected_hook_types: tuple[type, ...]
    required_prompt_sections: tuple[str, ...]


# ---------------------------------------------------------------------------
# Shared tool set — every agent gets these 8
# ---------------------------------------------------------------------------

_COMMON_TOOLS: frozenset[str] = frozenset(
    {
        "git_read",
        "git_list",
        "read_task_ledger",
        "create_board_task",
        "update_board_task",
        "add_task_comment",
        "report_activity",
        "web_search",
    }
)

# ---------------------------------------------------------------------------
# Agent specs (one row per agent, verified against source in src/agents/)
# ---------------------------------------------------------------------------

AGENT_SPECS: list[AgentSpec] = [
    AgentSpec(
        module="src.agents.pm",
        factory="create_pm_agent",
        prompt_constant="PM_SYSTEM_PROMPT",
        name="pm",
        model_name="OPUS",
        prompt_keyword="Project Manager",
        expected_tools=_COMMON_TOOLS
        | {
            "generate_sow",
            "parse_sow",
            "present_sow_for_approval",
            "update_task_ledger",
            "git_write_project_plan",
            "git_write_phase_summary",
            "store_git_credentials",
            "verify_git_access",
            "store_aws_credentials_tool",
            "verify_aws_access",
            "ask_customer",
        },
        expected_hook_types=(CustomerInterruptHook,),
        required_prompt_sections=(
            "Your Role",
            "Task Ledger",
            "Decision Framework",
            "Communication Style",
            "Handoff Guidance",
            "Standalone Mode",
            "Recovery Awareness",
        ),
    ),
    AgentSpec(
        module="src.agents.sa",
        factory="create_sa_agent",
        prompt_constant="SA_SYSTEM_PROMPT",
        name="sa",
        model_name="OPUS",
        prompt_keyword="Solutions Architect",
        expected_tools=_COMMON_TOOLS | {"git_write_architecture", "write_adr"},
        expected_hook_types=(),
        required_prompt_sections=(
            "Your Role",
            "Architecture Principles",
            "ADR Format",
            "Decision Framework",
            "Handoff Guidance",
            "Review Triggers",
            "Recovery Awareness",
        ),
    ),
    AgentSpec(
        module="src.agents.security",
        factory="create_security_agent",
        prompt_constant="SECURITY_SYSTEM_PROMPT",
        name="security",
        model_name="OPUS",
        prompt_keyword="Security Engineer",
        expected_tools=_COMMON_TOOLS | {"git_write_security", "checkov_scan", "write_security_review"},
        expected_hook_types=(),
        required_prompt_sections=(
            "Your Role",
            "Security Standards",
            "Severity Classification",
            "Review Process",
            "Handoff Guidance",
            "Approval Criteria",
            "Recovery Awareness",
        ),
    ),
    AgentSpec(
        module="src.agents.infra",
        factory="create_infra_agent",
        prompt_constant="INFRA_SYSTEM_PROMPT",
        name="infra",
        model_name="SONNET",
        prompt_keyword="Infrastructure Engineer",
        expected_tools=_COMMON_TOOLS
        | {
            "git_write_infra",
            "git_write_infra_batch",
            "terraform_validate",
            "terraform_plan",
            "terraform_apply",
            "terraform_output",
            "terraform_destroy",
            "checkov_scan",
        },
        expected_hook_types=(),
        required_prompt_sections=(
            "Your Role",
            "Terraform Standards",
            "Security Requirements",
            "Self-Validation Workflow",
            "Handoff Guidance",
            "Review Triggers",
            "Recovery Awareness",
        ),
    ),
    AgentSpec(
        module="src.agents.dev",
        factory="create_dev_agent",
        prompt_constant="DEV_SYSTEM_PROMPT",
        name="dev",
        model_name="SONNET",
        prompt_keyword="Application Developer",
        expected_tools=_COMMON_TOOLS | {"git_write_app", "git_write_app_batch"},
        expected_hook_types=(),
        required_prompt_sections=(
            "Your Role",
            "Code Standards",
            "Self-Validation Workflow",
            "Handoff Guidance",
            "Review Triggers",
            "Recovery Awareness",
        ),
    ),
    AgentSpec(
        module="src.agents.data",
        factory="create_data_agent",
        prompt_constant="DATA_SYSTEM_PROMPT",
        name="data",
        model_name="SONNET",
        prompt_keyword="Data Engineer",
        expected_tools=_COMMON_TOOLS | {"git_write_data", "git_write_data_batch"},
        expected_hook_types=(),
        required_prompt_sections=(
            "Your Role",
            "Data Standards",
            "Handoff Guidance",
            "Recovery Awareness",
        ),
    ),
    AgentSpec(
        module="src.agents.qa",
        factory="create_qa_agent",
        prompt_constant="QA_SYSTEM_PROMPT",
        name="qa",
        model_name="SONNET",
        prompt_keyword="Quality Assurance",
        expected_tools=_COMMON_TOOLS | {"git_write_tests", "git_write_tests_batch"},
        expected_hook_types=(),
        required_prompt_sections=(
            "Your Role",
            "Testing Standards",
            "Quality Gates",
            "Handoff Guidance",
            "Recovery Awareness",
        ),
    ),
]


def _spec_id(spec: AgentSpec) -> str:
    """Return the agent name for parametrize IDs."""
    return spec.name


# ---------------------------------------------------------------------------
# Parametrized factory tests (7 methods x 7 agents = 49 cases)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAgentFactories:
    """Verify every agent factory wires the correct name, model, tools, and hooks."""

    @pytest.mark.parametrize("spec", AGENT_SPECS, ids=_spec_id)
    def test_system_prompt_defined(self, spec: AgentSpec) -> None:
        """System prompt constant exists, is substantial, and contains role keyword."""
        mod = importlib.import_module(spec.module)
        prompt: str = getattr(mod, spec.prompt_constant)
        assert isinstance(prompt, str)
        assert len(prompt) > 100, f"{spec.prompt_constant} is too short ({len(prompt)} chars)"
        assert spec.prompt_keyword in prompt, f"{spec.prompt_constant} missing keyword '{spec.prompt_keyword}'"

    @pytest.mark.parametrize("spec", AGENT_SPECS, ids=_spec_id)
    def test_system_prompt_has_required_sections(self, spec: AgentSpec) -> None:
        """System prompt contains all required section headings."""
        mod = importlib.import_module(spec.module)
        prompt: str = getattr(mod, spec.prompt_constant)
        for section in spec.required_prompt_sections:
            assert section in prompt, f"{spec.name} prompt missing section: '{section}'"

    @pytest.mark.parametrize("spec", AGENT_SPECS, ids=_spec_id)
    def test_factory_passes_correct_name(self, spec: AgentSpec) -> None:
        """Factory passes expected agent name to Agent()."""
        with (
            patch(f"{spec.module}.Agent") as mock_agent,
            patch(f"{spec.module}.{spec.model_name}"),
        ):
            factory_fn = getattr(importlib.import_module(spec.module), spec.factory)
            factory_fn()
            assert mock_agent.call_args.kwargs["name"] == spec.name

    @pytest.mark.parametrize("spec", AGENT_SPECS, ids=_spec_id)
    def test_factory_passes_correct_model(self, spec: AgentSpec) -> None:
        """Factory passes the expected model singleton to Agent()."""
        with (
            patch(f"{spec.module}.Agent") as mock_agent,
            patch(f"{spec.module}.{spec.model_name}") as mock_model,
        ):
            factory_fn = getattr(importlib.import_module(spec.module), spec.factory)
            factory_fn()
            assert mock_agent.call_args.kwargs["model"] is mock_model

    @pytest.mark.parametrize("spec", AGENT_SPECS, ids=_spec_id)
    def test_factory_wires_exact_tools(self, spec: AgentSpec) -> None:
        """Factory passes exactly the expected tools (by function name, not count)."""
        with (
            patch(f"{spec.module}.Agent") as mock_agent,
            patch(f"{spec.module}.{spec.model_name}"),
        ):
            factory_fn = getattr(importlib.import_module(spec.module), spec.factory)
            factory_fn()
            actual_tools = mock_agent.call_args.kwargs["tools"]
            actual_names = {t.__name__ for t in actual_tools}
            assert actual_names == spec.expected_tools, (
                f"{spec.name}: tool mismatch.\n"
                f"  Missing: {spec.expected_tools - actual_names}\n"
                f"  Extra:   {actual_names - spec.expected_tools}"
            )

    @pytest.mark.parametrize("spec", AGENT_SPECS, ids=_spec_id)
    def test_factory_wires_correct_hooks(self, spec: AgentSpec) -> None:
        """Factory passes correct hook types (PM gets CustomerInterruptHook, others none)."""
        with (
            patch(f"{spec.module}.Agent") as mock_agent,
            patch(f"{spec.module}.{spec.model_name}"),
        ):
            factory_fn = getattr(importlib.import_module(spec.module), spec.factory)
            factory_fn()
            call_kwargs = mock_agent.call_args.kwargs

            if spec.expected_hook_types:
                actual_hooks = call_kwargs.get("hooks", [])
                assert len(actual_hooks) == len(spec.expected_hook_types), (
                    f"{spec.name}: expected {len(spec.expected_hook_types)} hook(s), got {len(actual_hooks)}"
                )
                for hook, expected_type in zip(actual_hooks, spec.expected_hook_types, strict=True):
                    assert isinstance(hook, expected_type), (
                        f"{spec.name}: expected hook {expected_type.__name__}, got {type(hook).__name__}"
                    )
            else:
                hooks = call_kwargs.get("hooks")
                assert hooks is None or hooks == [], f"{spec.name}: expected no hooks but got {hooks}"

    @pytest.mark.parametrize("spec", AGENT_SPECS, ids=_spec_id)
    def test_factory_returns_agent_instance(self, spec: AgentSpec) -> None:
        """Factory returns the Agent instance created by Agent()."""
        with (
            patch(f"{spec.module}.Agent") as mock_agent,
            patch(f"{spec.module}.{spec.model_name}"),
        ):
            factory_fn = getattr(importlib.import_module(spec.module), spec.factory)
            result = factory_fn()
            assert result is mock_agent.return_value


# ---------------------------------------------------------------------------
# Cross-agent invariant tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAgentRosterInvariants:
    """Verify structural invariants across the entire agent roster."""

    def test_all_agents_share_common_tools(self) -> None:
        """Every agent includes all 8 common tools."""
        for spec in AGENT_SPECS:
            missing = _COMMON_TOOLS - spec.expected_tools
            assert not missing, f"{spec.name} missing common tools: {missing}"

    def test_agent_names_are_unique(self) -> None:
        """No two agents share a name."""
        names = [s.name for s in AGENT_SPECS]
        assert len(names) == len(set(names))

    def test_all_seven_agents_covered(self) -> None:
        """Spec table covers all 7 expected agents."""
        expected = {"pm", "sa", "security", "infra", "dev", "data", "qa"}
        actual = {s.name for s in AGENT_SPECS}
        assert actual == expected

    def test_only_pm_has_hooks(self) -> None:
        """Only the PM agent should have hooks; all others must have none."""
        for spec in AGENT_SPECS:
            if spec.name == "pm":
                assert len(spec.expected_hook_types) > 0
            else:
                assert len(spec.expected_hook_types) == 0, f"{spec.name} unexpectedly has hooks"
