#!/usr/bin/env python3
"""M3 Integration Test: Discovery Swarm with live agent logging.

Creates ephemeral AWS resources (DynamoDB table + AgentCore Memory),
runs PM + SA through the Discovery Swarm with a sample SOW, then
tears down all resources.

Run directly for live output:
    source .venv/bin/activate
    python tests/integration/test_discovery_swarm.py

Resources created (and destroyed after):
    - DynamoDB table: cloudcrew-inttest-{random}
    - AgentCore Memory (STM): cloudcrew_inttest_stm_{random}
    - AgentCore Memory (LTM): cloudcrew_inttest_ltm_{random}
    - Temp git repo: /tmp/cloudcrew-discovery-test-{random}
"""

from __future__ import annotations

import json
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

# Ensure project root is on sys.path for direct script execution
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
from collections.abc import Generator  # noqa: E402
from typing import Any  # noqa: E402

import boto3  # noqa: E402
import git  # noqa: E402

# ---------------------------------------------------------------------------
# 1. LIVE OBSERVABILITY HOOK
# ---------------------------------------------------------------------------
# Must be defined before importing src modules, since those trigger model
# singleton creation (which needs env vars set).


BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"


def _ts() -> str:
    """Short timestamp for log lines."""
    return datetime.now(UTC).strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# 2. SAMPLE SOW DOCUMENT
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
5. Project plan with phase breakdown

## Acceptance Criteria
- Architecture achieves 99.9% uptime via multi-AZ design
- Estimated monthly cost is within budget ($8,000/month)
- All Terraform modules pass Checkov security scan with zero critical findings
- Documentation is complete and reviewed by the customer
"""

# ---------------------------------------------------------------------------
# 3. AWS RESOURCE MANAGEMENT
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
    # Wait for table to become ACTIVE
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
        "eventExpiryDuration": 3,  # minimum: 3 days
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

    # Poll until ACTIVE
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
    repo_path = tempfile.mkdtemp(prefix="cloudcrew-discovery-test-")

    stm_memory_id = ""
    ltm_memory_id = ""
    control_client = boto3.client("bedrock-agentcore-control", region_name=region)

    try:
        # --- Create resources ---
        print(f"\n{BOLD}{'=' * 70}")
        print("  CREATING TEST RESOURCES")
        print(f"{'=' * 70}{RESET}\n")

        # DynamoDB table
        create_dynamodb_table(table_name, region)

        # AgentCore Memory (STM + LTM)
        try:
            stm_memory_id = create_memory_resource(control_client, stm_name, with_semantic_ltm=False)
            ltm_memory_id = create_memory_resource(control_client, ltm_name, with_semantic_ltm=True)
        except Exception as e:
            print(f"{YELLOW}[{_ts()}] AgentCore Memory unavailable — running without memory: {e}{RESET}")
            stm_memory_id = ""
            ltm_memory_id = ""

        # Git repo
        print(f"{CYAN}[{_ts()}] Initializing git repo: {repo_path}{RESET}")
        repo = git.Repo.init(repo_path)
        # Create SOW file
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
        # --- Tear down resources ---
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
# 4. MAIN TEST
# ---------------------------------------------------------------------------


def run_test() -> None:
    """Run the Discovery Swarm integration test with live output."""
    region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1"))

    with ephemeral_resources(region) as resources:
        # Set environment variables BEFORE importing src modules
        # (config.py reads them at import time)
        os.environ["TASK_LEDGER_TABLE"] = resources["table_name"]
        os.environ["STM_MEMORY_ID"] = resources["stm_memory_id"]
        os.environ["LTM_MEMORY_ID"] = resources["ltm_memory_id"]
        os.environ["PROJECT_REPO_PATH"] = resources["repo_path"]
        os.environ["AWS_REGION"] = region

        # Force-reload config so it picks up the new env vars
        import importlib

        import src.config

        importlib.reload(src.config)

        # Now import the discovery swarm (this triggers agent creation)
        from src.agents.base import build_invocation_state
        from strands.hooks import HookProvider, HookRegistry
        from strands.hooks.events import (
            AfterNodeCallEvent,
            AfterToolCallEvent,
            BeforeNodeCallEvent,
            BeforeToolCallEvent,
        )

        # Define live observability hook
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
                print(f"\n{BOLD}{BLUE}{'─' * 70}")
                print(f"  AGENT: {event.node_id.upper()}")
                print(f"{'─' * 70}{RESET}\n")

            def _on_node_end(self, event: AfterNodeCallEvent) -> None:
                elapsed = time.time() - self._node_start_time
                print(f"\n{DIM}[{_ts()}] Agent {event.node_id} finished ({elapsed:.1f}s){RESET}")

            def _on_tool_call(self, event: BeforeToolCallEvent) -> None:
                tool_name = event.tool_use.get("name", "unknown")
                tool_input = event.tool_use.get("input", {})
                # Summarize input (truncate long values)
                summary_parts = []
                if isinstance(tool_input, dict):
                    for k, v in tool_input.items():
                        val_str = str(v)
                        if len(val_str) > 80:
                            val_str = val_str[:77] + "..."
                        summary_parts.append(f"{k}={val_str}")
                summary = ", ".join(summary_parts) if summary_parts else ""
                print(f"{YELLOW}[{_ts()}] 🔧 {tool_name}({summary}){RESET}")

            def _on_tool_done(self, event: AfterToolCallEvent) -> None:
                tool_name = event.tool_use.get("name", "unknown")
                if event.exception:
                    print(f"{RED}[{_ts()}] ✗ {tool_name} FAILED: {event.exception}{RESET}")
                else:
                    # Summarize result
                    result_content = ""
                    if event.result and "content" in event.result:
                        for block in event.result["content"]:
                            if isinstance(block, dict) and "text" in block:
                                result_content = block["text"]
                                break
                    if len(result_content) > 120:
                        result_content = result_content[:117] + "..."
                    print(f"{GREEN}[{_ts()}] ✓ {tool_name} → {result_content}{RESET}")

        # Import and patch the discovery swarm creation to include our hook
        from src.agents.pm import create_pm_agent
        from src.agents.sa import create_sa_agent
        from src.config import EXECUTION_TIMEOUT_DISCOVERY, NODE_TIMEOUT
        from src.hooks.memory_hook import MemoryHook
        from src.hooks.resilience_hook import ResilienceHook
        from src.phases.runner import run_phase
        from strands.multiagent.swarm import Swarm

        # Build invocation state
        invocation_state = build_invocation_state(
            project_id="inttest-discovery",
            phase="discovery",
        )

        # Build hooks list (ResilienceHook for structured logging + LiveObservabilityHook for console)
        hooks: list[HookProvider] = [ResilienceHook(), LiveObservabilityHook()]
        if resources["stm_memory_id"] or resources["ltm_memory_id"]:
            hooks.append(
                MemoryHook(
                    stm_memory_id=resources["stm_memory_id"],
                    ltm_memory_id=resources["ltm_memory_id"],
                ),
            )

        # Swarm factory for run_phase (creates a fresh swarm per attempt)
        def swarm_factory() -> Swarm:
            fresh_pm = create_pm_agent()
            fresh_sa = create_sa_agent()
            return Swarm(
                nodes=[fresh_pm, fresh_sa],
                entry_point=fresh_pm,
                max_handoffs=10,
                max_iterations=10,
                execution_timeout=EXECUTION_TIMEOUT_DISCOVERY,
                node_timeout=NODE_TIMEOUT,
                repetitive_handoff_detection_window=6,
                repetitive_handoff_min_unique_agents=2,
                hooks=hooks,
                id="discovery-swarm-inttest",
            )

        # --- Run the Swarm via run_phase (with automatic retry) ---
        task = (
            "We have a new engagement for Acme Corp. The Statement of Work is at "
            "docs/sow.md in the project repository.\n\n"
            "Your tasks:\n"
            "1. Read the SOW using git_read\n"
            "2. Parse it with parse_sow to extract structured requirements\n"
            "3. Update the task ledger with key facts and assumptions from the SOW\n"
            "4. Create a project plan document at docs/project-plan/plan.md\n"
            "5. Hand off to the SA for initial architecture thinking based on the requirements"
        )

        print(f"\n{BOLD}{'=' * 70}")
        print("  RUNNING DISCOVERY SWARM (with run_phase retry)")
        print(f"{'=' * 70}{RESET}")
        print(f"\n{DIM}Task: {task[:100]}...{RESET}\n")

        start_time = time.time()

        phase_result = run_phase(
            swarm_factory,
            task,
            invocation_state,
            max_retries=1,
            retry_delay=5.0,
        )

        elapsed = time.time() - start_time
        result = phase_result.result

        # --- Print results ---
        print(f"\n{BOLD}{'=' * 70}")
        print("  DISCOVERY SWARM COMPLETE")
        print(f"{'=' * 70}{RESET}\n")
        print(f"  Duration:    {elapsed:.1f}s")
        print(f"  Attempts:    {phase_result.attempts}")
        print(f"  Status:      {result.status}")
        print(f"  Exec count:  {result.execution_count}")

        if phase_result.retry_history:
            print(f"\n{BOLD}Retry history:{RESET}")
            for entry in phase_result.retry_history:
                err = entry.get("error", None)
                err_str = f" error={err}" if err else ""
                print(f"  attempt {entry['attempt']}: {entry['duration_s']}s{err_str}")

        # Show accumulated token usage
        if result.accumulated_usage:
            usage = result.accumulated_usage
            print(f"  Tokens in:   {usage.get('inputTokens', 'N/A')}")
            print(f"  Tokens out:  {usage.get('outputTokens', 'N/A')}")

        # Show node execution history
        if hasattr(result, "node_history") and result.node_history:
            print(f"\n{BOLD}Node history:{RESET}")
            for node in result.node_history:
                print(f"  → {node.name if hasattr(node, 'name') else node}")

        # Show what was committed to the repo
        print(f"\n{BOLD}Git commits:{RESET}")
        repo = git.Repo(resources["repo_path"])
        for commit in repo.iter_commits():
            print(f"  {DIM}{commit.hexsha[:8]}{RESET} {commit.message.strip()}")

        print(f"\n{BOLD}Repository files:{RESET}")
        for item in repo.tree().traverse():
            if item.type == "blob":
                print(f"  {item.path}")

        # Show DynamoDB ledger contents
        print(f"\n{BOLD}Task Ledger (DynamoDB):{RESET}")
        try:
            dynamodb = boto3.resource("dynamodb", region_name=region)
            table = dynamodb.Table(resources["table_name"])
            response = table.get_item(
                Key={"PK": "PROJECT#inttest-discovery", "SK": "LEDGER"},
            )
            if "Item" in response:
                ledger_data = response["Item"].get("data", {})
                print(json.dumps(ledger_data, indent=2, default=str)[:2000])
            else:
                print("  (empty — PM did not write to ledger)")
        except Exception as e:
            print(f"  Error reading ledger: {e}")

        print(f"\n{GREEN}Integration test completed successfully.{RESET}\n")


if __name__ == "__main__":
    # Configure logging — show strands activity at INFO level
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    # Enable strands loggers for visibility
    logging.getLogger("strands").setLevel(logging.INFO)
    logging.getLogger("strands.multiagent").setLevel(logging.INFO)
    # Keep our own modules at INFO
    logging.getLogger("src").setLevel(logging.INFO)

    run_test()
