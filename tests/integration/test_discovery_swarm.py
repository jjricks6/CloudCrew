#!/usr/bin/env python3
"""Full lifecycle integration test: All 5 phases with live agent logging.

Creates ephemeral AWS resources (DynamoDB table + AgentCore Memory),
runs all 5 delivery phases sequentially through their Swarms with a
sample SOW, then tears down all resources.

Phases executed in order:
    1. DISCOVERY — PM + SA: Parse SOW, create project plan
    2. ARCHITECTURE — SA + Infra + Security: Design target architecture
    3. POC — Dev + Infra + Data + Security + SA: Proof of concept
    4. PRODUCTION — Dev + Infra + Data + Security + QA: Production hardening
    5. HANDOFF — PM + SA: Deliverable packaging and handoff docs

Run directly for live output (all phases):
    source .venv/bin/activate
    python tests/integration/test_discovery_swarm.py

Run specific phases:
    python tests/integration/test_discovery_swarm.py --phases DISCOVERY ARCHITECTURE
    python tests/integration/test_discovery_swarm.py --phases DISCOVERY  # single phase

Resources created (and destroyed after):
    - DynamoDB table: cloudcrew-inttest-{random}
    - AgentCore Memory (STM): cloudcrew_inttest_stm_{random}
    - AgentCore Memory (LTM): cloudcrew_inttest_ltm_{random}
    - Temp git repo: /tmp/cloudcrew-lifecycle-test-{random}
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

# Strands SDK uses recursive event_loop_cycle — each tool call adds ~7 stack
# frames.  Agents making 40+ sequential calls (e.g. Infra validate/fix cycles)
# can exceed Python's default 1000-frame limit.
sys.setrecursionlimit(50000)

# Ensure project root is on sys.path for direct script execution
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
from collections.abc import Callable, Generator  # noqa: E402
from typing import Any  # noqa: E402

import boto3  # noqa: E402
import git  # noqa: E402

# ---------------------------------------------------------------------------
# Terminal colours (for direct script execution)
# ---------------------------------------------------------------------------

BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"
MAGENTA = "\033[95m"

# Phase execution order
ALL_PHASES = ["DISCOVERY", "ARCHITECTURE", "POC", "PRODUCTION", "HANDOFF"]


def _ts() -> str:
    """Short timestamp for log lines."""
    return datetime.now(UTC).strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Sample SOW
# ---------------------------------------------------------------------------

SAMPLE_SOW = """\
# Statement of Work: Cloud-Native Web Platform

## Client
Acme Corp — a mid-size e-commerce company operating a monolithic Ruby on Rails
application on self-managed EC2 instances.

## Project Objective
Migrate Acme Corp's existing web application to a scalable, cloud-native
architecture on AWS that achieves 99.9% uptime and reduces monthly
infrastructure costs by at least 30%.

## Scope of Work

### Phase 1: Discovery & Architecture
- Assess the current application and infrastructure
- Design a target AWS architecture
- Produce architecture decision records (ADRs) for key technology choices

### Phase 2: Proof of Concept
- Implement core infrastructure modules in Terraform
- Deploy a minimal version of the application to validate the architecture

### Phase 3: Production
- Harden infrastructure for production workloads
- Implement CI/CD pipeline
- Security hardening and compliance review

### Phase 4: Handoff
- Package all deliverables
- Create operations runbook
- Knowledge transfer documentation

## Requirements

### Functional Requirements
1. The application must support 10,000 concurrent users during peak hours
2. User sessions must persist across deployments (stateless application tier)
3. Database must support read replicas for reporting workloads
4. Static assets must be served via CDN with <100ms latency globally

### Non-Functional Requirements
1. Multi-AZ deployment for all stateful services
2. All data encrypted at rest (KMS) and in transit (TLS 1.2+)
3. Automated backups with 30-day retention
4. Infrastructure as Code — all resources managed by Terraform
5. CI/CD pipeline for automated testing and deployment

## Constraints
- Budget: Maximum $8,000/month for AWS infrastructure
- Timeline: Architecture phase complete within 2 weeks
- Compliance: SOC 2 Type II controls must be maintained
- Existing database is PostgreSQL 14 — migration to a different engine is not preferred

## Deliverables
1. Architecture design document with component diagrams
2. ADRs for all significant technology decisions
3. Terraform modules for core infrastructure (VPC, compute, database, CDN)
4. Security review report
5. CI/CD pipeline configuration
6. Operations runbook
7. Project plan with phase breakdown

## Acceptance Criteria
- Architecture achieves 99.9% uptime via multi-AZ design
- Estimated monthly cost is within budget ($8,000/month)
- All Terraform modules pass Checkov security scan with zero critical findings
- Documentation is complete and reviewed by the customer
"""

# ---------------------------------------------------------------------------
# Phase task prompts
# ---------------------------------------------------------------------------

PHASE_TASKS: dict[str, str] = {
    # ------------------------------------------------------------------
    # DISCOVERY: PM-only deliverables.  SA is available if PM needs to
    # ask a quick architectural clarification, but SA produces nothing.
    # ------------------------------------------------------------------
    "DISCOVERY": (
        "We have a new engagement for Acme Corp. The Statement of Work is at "
        "docs/sow.md in the project repository.\n\n"
        "Your tasks:\n"
        "1. Read the SOW using git_read\n"
        "2. Parse it with parse_sow to extract structured requirements\n"
        "3. Update the task ledger with ALL key facts, assumptions, requirements, "
        "constraints, and deliverables extracted from the SOW\n"
        "4. Create a project plan document at docs/project-plan/plan.md that "
        "outlines the phased delivery approach\n\n"
        "IMPORTANT: This is the Discovery phase ONLY. Do NOT produce architecture "
        "design documents, ADRs, or Terraform code. Those are deliverables for "
        "later phases. Discovery output is strictly: parsed SOW data in the task "
        "ledger + a project plan document."
    ),
    # ------------------------------------------------------------------
    # ARCHITECTURE: SA writes design docs and ADRs.  Do NOT hand off to
    # Infra or Security — there is no code to validate or scan yet.
    # Infra and Security are in the swarm but should not be invoked.
    # ------------------------------------------------------------------
    "ARCHITECTURE": (
        "Continue the Acme Corp engagement. Discovery is complete — the SOW has "
        "been parsed and a project plan exists in docs/project-plan/.\n\n"
        "BEFORE creating any files, check what already exists:\n"
        "- Use git_list to see all files under docs/architecture/\n"
        "- Use read_task_ledger to see recorded deliverables and decisions\n"
        "- If architecture docs or ADRs already exist from a prior attempt, "
        "READ them and build on them — do NOT recreate from scratch\n\n"
        "Your tasks (SA only — do NOT hand off to Infra or Security):\n"
        "1. Read the task ledger, SOW, and project plan to understand requirements\n"
        "2. Design a target AWS architecture that meets the requirements\n"
        "3. Write an architecture design document in docs/architecture/\n"
        "4. Create ADRs for key technology decisions in docs/architecture/adr/\n"
        "5. Update the task ledger with architecture decisions and deliverables\n\n"
        "IMPORTANT: This phase produces design documents ONLY. No Terraform code, "
        "no security scans, no infrastructure implementation. Those happen in POC."
    ),
    # ------------------------------------------------------------------
    # POC: The heavy implementation phase.  Dev leads, Infra writes TF,
    # Data writes schemas.  Key rule: Infra must hand off to Security
    # AFTER EACH MODULE so the recursion stack resets between modules.
    # ------------------------------------------------------------------
    "POC": (
        "Continue the Acme Corp engagement. Architecture design is complete — "
        "check docs/architecture/ for the design document and ADRs.\n\n"
        "BEFORE creating any files, check what already exists:\n"
        "- Use git_list to see existing files in infra/, app/, data/\n"
        "- Use read_task_ledger to see recorded deliverables\n"
        "- If modules or code exist from a prior attempt, build on them\n\n"
        "Your tasks:\n"
        "1. Dev: Read the architecture design and task ledger, then create "
        "application scaffolding under app/\n"
        "2. Dev: Hand off to Infra for Terraform implementation\n"
        "3. Infra: Implement ONE Terraform module (start with VPC under "
        "infra/modules/vpc/), run terraform_validate, then hand off to "
        "Security for review BEFORE starting the next module\n"
        "4. Security: Review the module, hand back to Infra for the next one\n"
        "5. Infra: Implement the next module (compute under "
        "infra/modules/compute/), validate, hand off to Security again\n"
        "6. Data: Create initial database schema under data/\n"
        "7. SA: Validate alignment with the architecture design\n\n"
        "CRITICAL: Infra must hand off to Security after EACH module — do NOT "
        "write multiple modules in a single turn. This keeps each turn focused "
        "and manageable."
    ),
    # ------------------------------------------------------------------
    # PRODUCTION: Harden existing POC code.  Same per-module handoff
    # pattern.  QA validates acceptance criteria at the end.
    # ------------------------------------------------------------------
    "PRODUCTION": (
        "Continue the Acme Corp engagement. The POC phase is complete — core "
        "infrastructure modules exist in infra/ and data/.\n\n"
        "BEFORE creating any files, check what already exists:\n"
        "- Use git_list to see existing files in infra/, app/, data/\n"
        "- Use read_task_ledger to see recorded deliverables\n\n"
        "Your tasks:\n"
        "1. Dev: Read existing code and architecture docs, then harden "
        "application code and create a CI/CD pipeline config at app/ci/pipeline.yml\n"
        "2. Dev: Hand off to Infra for infrastructure hardening\n"
        "3. Infra: Harden existing Terraform modules ONE AT A TIME — add "
        "encryption, backups, monitoring. After each module, run "
        "terraform_validate and hand off to Security for review\n"
        "4. Security: Perform security review of each module, hand back to Infra "
        "or write the final security review report at docs/security/review.md\n"
        "5. QA: Create a test plan, validate acceptance criteria from the SOW, "
        "and write test suites under app/tests/\n\n"
        "CRITICAL: Infra must hand off to Security after EACH module — do NOT "
        "harden multiple modules in a single turn."
    ),
    # ------------------------------------------------------------------
    # HANDOFF: PM packages deliverables, SA signs off on architecture.
    # ------------------------------------------------------------------
    "HANDOFF": (
        "Continue the Acme Corp engagement. Production hardening is complete — "
        "all infrastructure is production-ready with security review.\n\n"
        "BEFORE creating any files, check what already exists:\n"
        "- Use git_list to see all project deliverables\n"
        "- Use read_task_ledger to see deliverable status\n\n"
        "Your tasks:\n"
        "1. PM: Read the task ledger and all project deliverables\n"
        "2. PM: Create an operations runbook at docs/handoff/runbook.md\n"
        "3. PM: Create a knowledge transfer document at "
        "docs/handoff/knowledge-transfer.md\n"
        "4. PM: Compile a final deliverables summary at "
        "docs/handoff/deliverables-summary.md\n"
        "5. PM: Update the task ledger with final deliverable status\n"
        "6. PM: Hand off to SA for a final architecture sign-off statement"
    ),
}


# ---------------------------------------------------------------------------
# AWS resource management
# ---------------------------------------------------------------------------


def create_dynamodb_table(table_name: str, region: str) -> None:
    """Create a DynamoDB table for the task ledger."""
    client = boto3.client("dynamodb", region_name=region)
    print(f"{CYAN}[{_ts()}] Creating DynamoDB table: {table_name}{RESET}")
    client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
        Tags=[{"Key": "environment", "Value": "integration-test"}],
    )
    waiter = client.get_waiter("table_exists")
    waiter.wait(TableName=table_name)
    print(f"{GREEN}[{_ts()}] DynamoDB table ACTIVE: {table_name}{RESET}")


def delete_dynamodb_table(table_name: str, region: str) -> None:
    """Delete a DynamoDB table."""
    client = boto3.client("dynamodb", region_name=region)
    try:
        client.delete_table(TableName=table_name)
        print(f"{YELLOW}[{_ts()}] DynamoDB table deleted: {table_name}{RESET}")
    except Exception as e:
        print(f"{RED}[{_ts()}] Failed to delete DynamoDB table: {e}{RESET}")


def create_memory_resource(
    control_client: Any,
    name: str,
    with_semantic_ltm: bool = False,
) -> str:
    """Create an AgentCore Memory resource and wait for it to become ACTIVE."""
    print(f"{CYAN}[{_ts()}] Creating AgentCore Memory: {name} (LTM={with_semantic_ltm}){RESET}")
    kwargs: dict[str, Any] = {
        "name": name,
        "description": f"Integration test memory - {name}",
        "eventExpiryDuration": 3,
        "tags": {"environment": "integration-test"},
    }
    if with_semantic_ltm:
        kwargs["memoryStrategies"] = [
            {
                "semanticMemoryStrategy": {
                    "name": "ProjectKnowledge",
                    "description": "Extract project decisions and architectural context",
                },
            },
        ]

    response = control_client.create_memory(**kwargs)
    memory_id = response["memory"]["id"]
    print(f"{CYAN}[{_ts()}]   Memory ID: {memory_id} (status: {response['memory']['status']}){RESET}")

    for _ in range(60):
        time.sleep(5)
        status_resp = control_client.get_memory(memoryId=memory_id)
        status = status_resp["memory"]["status"]
        if status == "ACTIVE":
            print(f"{GREEN}[{_ts()}] Memory ACTIVE: {memory_id}{RESET}")
            return memory_id
        if status == "FAILED":
            reason = status_resp["memory"].get("failureReason", "unknown")
            raise RuntimeError(f"Memory creation failed: {reason}")
        print(f"{DIM}[{_ts()}]   Waiting for memory... status={status}{RESET}")

    raise TimeoutError(f"Memory {memory_id} did not become ACTIVE within 5 minutes")


def delete_memory_resource(control_client: Any, memory_id: str) -> None:
    """Delete an AgentCore Memory resource."""
    try:
        control_client.delete_memory(memoryId=memory_id)
        print(f"{YELLOW}[{_ts()}] Memory deletion initiated: {memory_id}{RESET}")
    except Exception as e:
        print(f"{RED}[{_ts()}] Failed to delete memory {memory_id}: {e}{RESET}")


@contextmanager
def ephemeral_resources(region: str) -> Generator[dict[str, str], None, None]:
    """Context manager that creates and destroys all test resources.

    Yields a dict with keys: table_name, stm_memory_id, ltm_memory_id, repo_path
    """
    suffix = uuid.uuid4().hex[:8]
    table_name = f"cloudcrew-inttest-{suffix}"
    stm_name = f"cloudcrew_inttest_stm_{suffix}"
    ltm_name = f"cloudcrew_inttest_ltm_{suffix}"
    repo_path = tempfile.mkdtemp(prefix="cloudcrew-lifecycle-test-")

    stm_memory_id = ""
    ltm_memory_id = ""
    control_client = boto3.client("bedrock-agentcore-control", region_name=region)

    try:
        print(f"\n{BOLD}{'=' * 70}")
        print("  CREATING TEST RESOURCES")
        print(f"{'=' * 70}{RESET}\n")

        create_dynamodb_table(table_name, region)

        try:
            stm_memory_id = create_memory_resource(control_client, stm_name, with_semantic_ltm=False)
            ltm_memory_id = create_memory_resource(control_client, ltm_name, with_semantic_ltm=True)
        except Exception as e:
            print(f"{YELLOW}[{_ts()}] AgentCore Memory unavailable — running without memory: {e}{RESET}")
            stm_memory_id = ""
            ltm_memory_id = ""

        # Initialize git repo with SOW
        print(f"{CYAN}[{_ts()}] Initializing git repo: {repo_path}{RESET}")
        repo = git.Repo.init(repo_path)
        docs_dir = Path(repo_path) / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        sow_path = docs_dir / "sow.md"
        sow_path.write_text(SAMPLE_SOW)
        repo.index.add(["docs/sow.md"])
        repo.index.commit("Initial commit: add SOW document")
        print(f"{GREEN}[{_ts()}] Git repo ready with SOW at docs/sow.md{RESET}")

        print(f"\n{BOLD}Resources ready:{RESET}")
        print(f"  DynamoDB table: {table_name}")
        print(f"  STM Memory ID:  {stm_memory_id or '(disabled)'}")
        print(f"  LTM Memory ID:  {ltm_memory_id or '(disabled)'}")
        print(f"  Git repo:       {repo_path}")
        print()

        yield {
            "table_name": table_name,
            "stm_memory_id": stm_memory_id,
            "ltm_memory_id": ltm_memory_id,
            "repo_path": repo_path,
        }

    finally:
        print(f"\n{BOLD}{'=' * 70}")
        print("  DESTROYING TEST RESOURCES")
        print(f"{'=' * 70}{RESET}\n")

        delete_dynamodb_table(table_name, region)
        if stm_memory_id:
            delete_memory_resource(control_client, stm_memory_id)
        if ltm_memory_id:
            delete_memory_resource(control_client, ltm_memory_id)

        shutil.rmtree(repo_path, ignore_errors=True)
        print(f"{GREEN}[{_ts()}] Temp repo cleaned: {repo_path}{RESET}")
        print(f"\n{GREEN}All test resources destroyed.{RESET}\n")


# ---------------------------------------------------------------------------
# Live observability hook
# ---------------------------------------------------------------------------


def _create_live_hook() -> Any:
    """Create a LiveObservabilityHook for console output during Swarm execution.

    Defined as a factory to defer imports until after env vars are set.
    """
    from strands.hooks import HookProvider, HookRegistry
    from strands.hooks.events import (
        AfterNodeCallEvent,
        AfterToolCallEvent,
        BeforeNodeCallEvent,
        BeforeToolCallEvent,
    )

    class LiveObservabilityHook(HookProvider):
        """Prints live agent activity to stdout during Swarm execution."""

        def __init__(self) -> None:
            self._node_start_time: float = 0.0

        def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:  # noqa: ARG002
            registry.add_callback(BeforeNodeCallEvent, self._on_node_start)
            registry.add_callback(AfterNodeCallEvent, self._on_node_end)
            registry.add_callback(BeforeToolCallEvent, self._on_tool_call)
            registry.add_callback(AfterToolCallEvent, self._on_tool_done)

        def _on_node_start(self, event: BeforeNodeCallEvent) -> None:
            self._node_start_time = time.time()
            print(f"\n{BOLD}{BLUE}{'~' * 70}")
            print(f"  AGENT: {event.node_id.upper()}")
            print(f"{'~' * 70}{RESET}\n")

        def _on_node_end(self, event: AfterNodeCallEvent) -> None:
            elapsed = time.time() - self._node_start_time
            print(f"\n{DIM}[{_ts()}] Agent {event.node_id} finished ({elapsed:.1f}s){RESET}")

        def _on_tool_call(self, event: BeforeToolCallEvent) -> None:
            tool_name = event.tool_use.get("name", "unknown")
            tool_input = event.tool_use.get("input", {})
            summary_parts = []
            if isinstance(tool_input, dict):
                for k, v in tool_input.items():
                    val_str = str(v)
                    if len(val_str) > 80:
                        val_str = val_str[:77] + "..."
                    summary_parts.append(f"{k}={val_str}")
            summary = ", ".join(summary_parts) if summary_parts else ""
            print(f"{YELLOW}[{_ts()}]   tool: {tool_name}({summary}){RESET}")

        def _on_tool_done(self, event: AfterToolCallEvent) -> None:
            tool_name = event.tool_use.get("name", "unknown")
            if event.exception:
                print(f"{RED}[{_ts()}]   FAIL: {tool_name}: {event.exception}{RESET}")
            else:
                result_content = ""
                if event.result and "content" in event.result:
                    for block in event.result["content"]:
                        if isinstance(block, dict) and "text" in block:
                            result_content = block["text"]
                            break
                if len(result_content) > 120:
                    result_content = result_content[:117] + "..."
                print(f"{GREEN}[{_ts()}]   done: {tool_name} -> {result_content}{RESET}")

    return LiveObservabilityHook()


# ---------------------------------------------------------------------------
# Swarm factory builders
# ---------------------------------------------------------------------------

# Maps phase name to (factory_module, factory_func, accepts_memory_args)
_SWARM_REGISTRY: dict[str, tuple[str, str, bool]] = {
    "DISCOVERY": ("src.phases.discovery", "create_discovery_swarm", True),
    "ARCHITECTURE": ("src.phases.architecture", "create_architecture_swarm", False),
    "POC": ("src.phases.poc", "create_poc_swarm", False),
    "PRODUCTION": ("src.phases.production", "create_production_swarm", False),
    "HANDOFF": ("src.phases.handoff", "create_handoff_swarm", True),
}


def _get_swarm_factory_for_phase(
    phase: str,
    stm_memory_id: str,
    ltm_memory_id: str,
) -> Callable[..., Any]:
    """Build a zero-arg swarm factory for the given phase.

    Wraps the phase's create_*_swarm() so run_phase can call it with no args.
    Memory-enabled phases (Discovery, Handoff) get memory IDs passed through.
    """
    import importlib

    module_path, func_name, accepts_memory = _SWARM_REGISTRY[phase]
    module = importlib.import_module(module_path)
    factory = getattr(module, func_name)

    if accepts_memory and (stm_memory_id or ltm_memory_id):

        def wrapped() -> Any:
            return factory(stm_memory_id=stm_memory_id, ltm_memory_id=ltm_memory_id)

        return wrapped
    return factory


def _make_hooked_factory(
    inner_factory: Callable[..., Any],
    hook: Any,
) -> Callable[[], Any]:
    """Wrap a swarm factory to inject a live observability hook."""

    def hooked_factory() -> Any:
        swarm = inner_factory()
        if hasattr(swarm, "_hooks") and isinstance(swarm._hooks, list):
            swarm._hooks.append(hook)
        return swarm

    return hooked_factory


# ---------------------------------------------------------------------------
# Phase execution and reporting
# ---------------------------------------------------------------------------


def _print_phase_result(
    phase: str,
    phase_result: Any,
    elapsed: float,
    phase_num: int,
    total: int,
) -> dict[str, Any]:
    """Print results for a completed phase and return summary dict."""
    result = phase_result.result

    print(f"\n{BOLD}{GREEN}{'=' * 70}")
    print(f"  PHASE {phase_num}/{total}: {phase} COMPLETE")
    print(f"{'=' * 70}{RESET}\n")
    print(f"  Duration:    {elapsed:.1f}s")
    print(f"  Attempts:    {phase_result.attempts}")
    print(f"  Status:      {result.status}")
    print(f"  Exec count:  {result.execution_count}")

    if phase_result.retry_history:
        print(f"\n{BOLD}  Retry history:{RESET}")
        for entry in phase_result.retry_history:
            err = entry.get("error", None)
            err_str = f" error={err}" if err else ""
            print(f"    attempt {entry['attempt']}: {entry['duration_s']}s{err_str}")

    tokens_in = 0
    tokens_out = 0
    if result.accumulated_usage:
        usage = result.accumulated_usage
        tokens_in = usage.get("inputTokens", 0)
        tokens_out = usage.get("outputTokens", 0)
        print(f"  Tokens in:   {tokens_in:,}")
        print(f"  Tokens out:  {tokens_out:,}")

    return {
        "phase": phase,
        "duration_s": round(elapsed, 1),
        "attempts": phase_result.attempts,
        "status": str(result.status),
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
    }


def _print_repo_state(repo_path: str) -> None:
    """Print current git repo state (commits + files)."""
    repo = git.Repo(repo_path)

    print(f"\n{BOLD}Git commits:{RESET}")
    for commit in repo.iter_commits():
        msg = commit.message.strip().split("\n")[0]
        if len(msg) > 80:
            msg = msg[:77] + "..."
        print(f"  {DIM}{commit.hexsha[:8]}{RESET} {msg}")

    print(f"\n{BOLD}Repository files:{RESET}")
    for item in repo.tree().traverse():
        if item.type == "blob":
            print(f"  {item.path}")


def _print_ledger_state(table_name: str, project_id: str, region: str) -> None:
    """Print current task ledger contents from DynamoDB."""
    print(f"\n{BOLD}Task Ledger (DynamoDB):{RESET}")
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        table = dynamodb.Table(table_name)
        response = table.get_item(
            Key={"PK": f"PROJECT#{project_id}", "SK": "LEDGER"},
        )
        if "Item" in response:
            ledger_data = response["Item"].get("data", {})
            # Show key fields
            print(f"  Phase:    {ledger_data.get('current_phase', 'N/A')}")
            print(f"  Status:   {ledger_data.get('phase_status', 'N/A')}")
            facts = ledger_data.get("facts", [])
            decisions = ledger_data.get("decisions", [])
            deliverables = ledger_data.get("deliverables", {})
            print(f"  Facts:    {len(facts)}")
            print(f"  Decisions: {len(decisions)}")
            total_deliverables = sum(len(v) for v in deliverables.values())
            print(f"  Deliverables: {total_deliverables} across {len(deliverables)} phases")
            if deliverables:
                for phase_name, items in deliverables.items():
                    print(f"    {phase_name}: {[d.get('name', '?') for d in items]}")
        else:
            print("  (empty -- no ledger written yet)")
    except Exception as e:
        print(f"  Error reading ledger: {e}")


def _print_final_summary(
    phase_summaries: list[dict[str, Any]],
    total_elapsed: float,
) -> None:
    """Print the final run summary across all phases."""
    total_in = sum(s["tokens_in"] for s in phase_summaries)
    total_out = sum(s["tokens_out"] for s in phase_summaries)

    print(f"\n{BOLD}{MAGENTA}{'=' * 70}")
    print("  FULL LIFECYCLE TEST SUMMARY")
    print(f"{'=' * 70}{RESET}\n")

    # Per-phase table
    print(f"  {'Phase':<15} {'Status':<12} {'Duration':>10} {'Attempts':>9} {'Tokens In':>12} {'Tokens Out':>12}")
    print(f"  {'─' * 15} {'─' * 12} {'─' * 10} {'─' * 9} {'─' * 12} {'─' * 12}")
    for s in phase_summaries:
        print(
            f"  {s['phase']:<15} {s['status']:<12} {s['duration_s']:>9.1f}s {s['attempts']:>9} "
            f"{s['tokens_in']:>12,} {s['tokens_out']:>12,}"
        )
    print(f"  {'─' * 15} {'─' * 12} {'─' * 10} {'─' * 9} {'─' * 12} {'─' * 12}")
    print(f"  {'TOTAL':<15} {'':<12} {total_elapsed:>9.1f}s {'':<9} {total_in:>12,} {total_out:>12,}")

    print(f"\n  Total wall time: {total_elapsed:.1f}s ({total_elapsed / 60:.1f} min)")
    print(f"  Total tokens:    {total_in + total_out:,} ({total_in:,} in / {total_out:,} out)")

    failed = [s for s in phase_summaries if "COMPLETED" not in s["status"]]
    if failed:
        print(f"\n{RED}  FAILED PHASES: {[s['phase'] for s in failed]}{RESET}")
    else:
        print(f"\n{GREEN}  ALL PHASES COMPLETED SUCCESSFULLY{RESET}")


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------


def run_test(phases: list[str] | None = None) -> None:
    """Run the full lifecycle integration test with live output.

    Args:
        phases: List of phase names to run. Defaults to all 5 phases.
    """
    target_phases = phases or ALL_PHASES

    # Validate phase names
    for p in target_phases:
        if p not in ALL_PHASES:
            valid = ", ".join(ALL_PHASES)
            print(f"{RED}Unknown phase '{p}'. Valid phases: {valid}{RESET}")
            sys.exit(1)

    region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1"))
    project_id = f"inttest-lifecycle-{uuid.uuid4().hex[:6]}"

    print(f"\n{BOLD}{MAGENTA}{'=' * 70}")
    print("  CLOUDCREW FULL LIFECYCLE INTEGRATION TEST")
    print(f"{'=' * 70}{RESET}")
    print(f"\n  Project ID: {project_id}")
    print(f"  Phases:     {' -> '.join(target_phases)}")
    print(f"  Region:     {region}\n")

    with ephemeral_resources(region) as resources:
        # Set environment variables BEFORE importing src modules
        os.environ["TASK_LEDGER_TABLE"] = resources["table_name"]
        os.environ["STM_MEMORY_ID"] = resources["stm_memory_id"]
        os.environ["LTM_MEMORY_ID"] = resources["ltm_memory_id"]
        os.environ["PROJECT_REPO_PATH"] = resources["repo_path"]
        os.environ["AWS_REGION"] = region

        # Force-reload config so it picks up the new env vars
        import importlib

        import src.config

        importlib.reload(src.config)

        # Import run_phase and build_invocation_state
        from src.agents.base import build_invocation_state
        from src.phases.runner import run_phase

        # Create the live observability hook (shared across all phases)
        live_hook = _create_live_hook()

        phase_summaries: list[dict[str, Any]] = []
        total_start = time.time()

        for phase_idx, phase in enumerate(target_phases, 1):
            print(f"\n{BOLD}{CYAN}{'#' * 70}")
            print(f"  PHASE {phase_idx}/{len(target_phases)}: {phase}")
            print(f"  Agents: {_phase_agents(phase)}")
            print(f"{'#' * 70}{RESET}\n")

            # Build invocation state for this phase
            invocation_state = build_invocation_state(
                project_id=project_id,
                phase=phase.lower(),
            )

            # Get the swarm factory
            base_factory = _get_swarm_factory_for_phase(
                phase,
                stm_memory_id=resources["stm_memory_id"],
                ltm_memory_id=resources["ltm_memory_id"],
            )

            # Wrap the factory to inject our live observability hook
            hooked_factory = _make_hooked_factory(base_factory, live_hook)

            task = PHASE_TASKS[phase]
            print(f"{DIM}Task: {task[:120]}...{RESET}\n")

            phase_start = time.time()

            phase_result = run_phase(
                hooked_factory,
                task,
                invocation_state,
                max_retries=1,
                retry_delay=5.0,
            )

            phase_elapsed = time.time() - phase_start

            # Print phase results
            summary = _print_phase_result(phase, phase_result, phase_elapsed, phase_idx, len(target_phases))
            phase_summaries.append(summary)

            # Print repo and ledger state between phases
            _print_repo_state(resources["repo_path"])
            _print_ledger_state(resources["table_name"], project_id, region)

            # Check if phase failed — stop early
            if "COMPLETED" not in summary["status"]:
                print(f"\n{RED}Phase {phase} did not complete successfully. Stopping.{RESET}")
                break

        total_elapsed = time.time() - total_start

        # Final summary
        _print_final_summary(phase_summaries, total_elapsed)

        # Final repo state
        print(f"\n{BOLD}Final repository state:{RESET}")
        _print_repo_state(resources["repo_path"])
        _print_ledger_state(resources["table_name"], project_id, region)

        print(f"\n{GREEN}Integration test completed.{RESET}\n")


def _phase_agents(phase: str) -> str:
    """Return a human-readable agent list for a phase."""
    agents = {
        "DISCOVERY": "PM (entry) + SA",
        "ARCHITECTURE": "SA (entry) + Infra + Security",
        "POC": "Dev (entry) + Infra + Data + Security + SA",
        "PRODUCTION": "Dev (entry) + Infra + Data + Security + QA",
        "HANDOFF": "PM (entry) + SA",
    }
    return agents.get(phase, "unknown")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="CloudCrew full lifecycle integration test",
    )
    parser.add_argument(
        "--phases",
        nargs="+",
        choices=ALL_PHASES,
        default=None,
        help="Phases to run (default: all 5). Example: --phases DISCOVERY ARCHITECTURE",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    logging.getLogger("strands").setLevel(logging.INFO)
    logging.getLogger("strands.multiagent").setLevel(logging.INFO)
    logging.getLogger("src").setLevel(logging.INFO)

    run_test(phases=args.phases)
