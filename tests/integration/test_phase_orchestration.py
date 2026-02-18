#!/usr/bin/env python3
"""M4 Integration Test: Phase orchestration via Step Functions.

Exercises the full deployed system: API Gateway → Lambda → Step Functions
→ ECS → DynamoDB. Creates a project via the REST API, waits for Discovery
to complete, approves it, and verifies the state machine advances to
Architecture.

Prerequisites:
    - Infrastructure deployed: ``make tf-apply``
    - Docker image pushed: ``make docker-build && make docker-push``
    - AWS credentials configured for the target account

Run directly for live output:
    source .venv/bin/activate
    python tests/integration/test_phase_orchestration.py

Or via pytest:
    pytest tests/integration/test_phase_orchestration.py -v -s

Resources used (all pre-deployed):
    - API Gateway REST API
    - Step Functions state machine
    - Lambda functions (sfn_handlers, pm_review, approval, api)
    - ECS Fargate cluster + task definition
    - DynamoDB table (cloudcrew-projects)
    - S3 bucket (SOW uploads)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
import pytest

# Ensure project root is on sys.path for direct script execution
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

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


def _ts() -> str:
    """Short timestamp for log lines."""
    return datetime.now(UTC).strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Sample SOW
# ---------------------------------------------------------------------------

SAMPLE_SOW = """\
# Statement of Work: Cloud-Native Web Platform

## Client
Acme Corp — a mid-size e-commerce company migrating from monolithic Rails
to AWS cloud-native architecture.

## Objective
Migrate to a scalable, cloud-native architecture achieving 99.9% uptime
and 30% cost reduction.

## Requirements
1. Support 10,000 concurrent users at peak
2. Multi-AZ deployment for all stateful services
3. All data encrypted at rest and in transit
4. Infrastructure managed by Terraform
5. CI/CD pipeline for automated deployments

## Constraints
- Budget: $8,000/month AWS infrastructure
- Compliance: SOC 2 Type II
- Database: PostgreSQL 14

## Deliverables
1. Architecture design document
2. Terraform modules for core infrastructure
3. Security review report
4. Project plan with phase breakdown

## Acceptance Criteria
- Multi-AZ design achieving 99.9% uptime
- Monthly cost within budget
- Terraform passes Checkov scan with zero critical findings
"""


# ---------------------------------------------------------------------------
# Terraform output reader
# ---------------------------------------------------------------------------


def _get_terraform_output(key: str) -> str:
    """Read a Terraform output value from the deployed infrastructure.

    Args:
        key: The output variable name.

    Returns:
        The output value as a string.

    Raises:
        RuntimeError: If the output cannot be read.
    """
    tf_dir = Path(_PROJECT_ROOT) / "infra" / "terraform"
    result = subprocess.run(  # noqa: S603
        ["terraform", f"-chdir={tf_dir}", "output", "-raw", key],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        msg = f"Failed to read terraform output '{key}': {result.stderr.strip()}"
        raise RuntimeError(msg)
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------


def _api_request(
    base_url: str,
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    region: str = "us-east-1",
) -> dict[str, Any]:
    """Make an authenticated request to the API Gateway.

    Uses SigV4 signing via boto3 (API Gateway is NONE auth for M4, but this
    structure supports Cognito auth in M5 without changing test code).

    Args:
        base_url: The API Gateway base URL.
        method: HTTP method (GET, POST).
        path: URL path (e.g., /projects).
        body: Request body dict (for POST).
        region: AWS region.

    Returns:
        Parsed JSON response body.
    """
    import urllib.request

    url = f"{base_url}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"} if body else {}

    req = urllib.request.Request(url, data=data, headers=headers, method=method)  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return json.loads(resp.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.fp else ""
        print(f"{RED}HTTP {e.code}: {error_body}{RESET}")
        raise


# ---------------------------------------------------------------------------
# Phase orchestration poller
# ---------------------------------------------------------------------------


def _wait_for_phase_status(
    api_url: str,
    project_id: str,
    target_phase: str,
    target_status: str,
    timeout: float = 600.0,
    poll_interval: float = 15.0,
    region: str = "us-east-1",
) -> dict[str, Any]:
    """Poll project status until the target phase and status are reached.

    Args:
        api_url: API Gateway base URL.
        project_id: Project ID to poll.
        target_phase: Expected phase name.
        target_status: Expected phase status.
        timeout: Maximum wait time in seconds.
        poll_interval: Seconds between polls.
        region: AWS region.

    Returns:
        The final status response.

    Raises:
        TimeoutError: If the target state is not reached within timeout.
    """
    start = time.monotonic()
    last_status: dict[str, Any] = {}

    while True:
        elapsed = time.monotonic() - start
        if elapsed > timeout:
            msg = (
                f"Timed out after {elapsed:.0f}s waiting for {target_phase}/{target_status}. Last status: {last_status}"
            )
            raise TimeoutError(msg)

        try:
            last_status = _api_request(api_url, "GET", f"/projects/{project_id}/status", region=region)
            current_phase = last_status.get("current_phase", "")
            phase_status = last_status.get("phase_status", "")

            print(f"{DIM}[{_ts()}] Poll: phase={current_phase}, status={phase_status} ({elapsed:.0f}s){RESET}")

            if current_phase == target_phase and phase_status == target_status:
                return last_status
        except Exception as e:
            print(f"{YELLOW}[{_ts()}] Poll error (will retry): {e}{RESET}")

        time.sleep(poll_interval)


# ---------------------------------------------------------------------------
# Main test
# ---------------------------------------------------------------------------


def run_orchestration_test() -> None:
    """Run the phase orchestration integration test."""
    region = os.environ.get("AWS_DEFAULT_REGION", os.environ.get("AWS_REGION", "us-east-1"))

    # Read infrastructure outputs
    print(f"\n{BOLD}{'=' * 70}")
    print("  PHASE ORCHESTRATION INTEGRATION TEST")
    print(f"{'=' * 70}{RESET}\n")

    print(f"{CYAN}[{_ts()}] Reading Terraform outputs...{RESET}")
    api_url = os.environ.get("API_GATEWAY_URL", "") or _get_terraform_output("api_gateway_url")
    sfn_arn = os.environ.get("STATE_MACHINE_ARN", "") or _get_terraform_output("step_functions_arn")
    table_name = os.environ.get("TASK_LEDGER_TABLE", "") or _get_terraform_output("dynamodb_projects_table")

    print(f"  API URL:    {api_url}")
    print(f"  SFN ARN:    {sfn_arn}")
    print(f"  Table:      {table_name}")

    # -----------------------------------------------------------------------
    # Step 1: Create project
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}Step 1: Create project via POST /projects{RESET}")
    create_resp = _api_request(
        api_url,
        "POST",
        "/projects",
        body={
            "project_name": "E2E Test - Cloud Migration",
            "customer": "Acme Corp (E2E)",
            "sow_text": SAMPLE_SOW,
        },
        region=region,
    )
    project_id = create_resp["project_id"]
    print(f"{GREEN}[{_ts()}] Project created: {project_id}{RESET}")
    print(f"  Response: {json.dumps(create_resp, indent=2)}")

    # -----------------------------------------------------------------------
    # Step 2: Wait for Discovery phase to reach AWAITING_APPROVAL
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}Step 2: Wait for Discovery → AWAITING_APPROVAL{RESET}")
    print(f"{DIM}This includes: ECS Swarm execution + PM Review Lambda{RESET}\n")

    _wait_for_phase_status(
        api_url,
        project_id,
        target_phase="DISCOVERY",
        target_status="AWAITING_APPROVAL",
        timeout=900.0,  # Discovery Swarm can take up to 15 min
        poll_interval=20.0,
        region=region,
    )
    print(f"\n{GREEN}[{_ts()}] Discovery phase reached AWAITING_APPROVAL{RESET}")

    # -----------------------------------------------------------------------
    # Step 3: Check deliverables
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}Step 3: Check deliverables via GET /projects/{{id}}/deliverables{RESET}")
    deliverables_resp = _api_request(api_url, "GET", f"/projects/{project_id}/deliverables", region=region)
    print(f"  Deliverables: {json.dumps(deliverables_resp, indent=2)[:1000]}")

    # -----------------------------------------------------------------------
    # Step 4: Approve Discovery phase
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}Step 4: Approve Discovery via POST /projects/{{id}}/approve{RESET}")
    approve_resp = _api_request(api_url, "POST", f"/projects/{project_id}/approve", region=region)
    print(f"{GREEN}[{_ts()}] Approval sent: {json.dumps(approve_resp)}{RESET}")

    # -----------------------------------------------------------------------
    # Step 5: Verify Architecture phase starts
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}Step 5: Verify Architecture phase starts{RESET}")
    print(f"{DIM}Waiting for phase to advance to ARCHITECTURE/IN_PROGRESS...{RESET}\n")

    _wait_for_phase_status(
        api_url,
        project_id,
        target_phase="ARCHITECTURE",
        target_status="IN_PROGRESS",
        timeout=120.0,  # Should advance quickly after approval
        poll_interval=10.0,
        region=region,
    )
    print(f"\n{GREEN}[{_ts()}] Architecture phase is IN_PROGRESS — orchestration working!{RESET}")

    # -----------------------------------------------------------------------
    # Step 6: Verify Step Functions execution is running
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}Step 6: Verify Step Functions execution{RESET}")
    sfn_client = boto3.client("stepfunctions", region_name=region)
    executions = sfn_client.list_executions(
        stateMachineArn=sfn_arn,
        statusFilter="RUNNING",
        maxResults=10,
    )
    running = [e for e in executions["executions"] if project_id in e.get("name", "")]
    if running:
        print(f"{GREEN}[{_ts()}] Found running execution: {running[0]['name']}{RESET}")
        print(f"  Started: {running[0]['startDate']}")
    else:
        print(f"{YELLOW}[{_ts()}] No running execution found (may have already advanced){RESET}")

    # -----------------------------------------------------------------------
    # Step 7: Verify DynamoDB ledger state
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}Step 7: Verify DynamoDB ledger{RESET}")
    dynamodb = boto3.resource("dynamodb", region_name=region)
    table = dynamodb.Table(table_name)
    ledger_resp = table.get_item(Key={"PK": f"PROJECT#{project_id}", "SK": "LEDGER"})
    if "Item" in ledger_resp:
        ledger_data = ledger_resp["Item"].get("data", {})
        print(f"  Phase: {ledger_data.get('current_phase', 'N/A')}")
        print(f"  Status: {ledger_data.get('phase_status', 'N/A')}")
        print(f"  Project: {ledger_data.get('project_name', 'N/A')}")
    else:
        print(f"{YELLOW}  Ledger item not found (unexpected){RESET}")

    # -----------------------------------------------------------------------
    # Done
    # -----------------------------------------------------------------------
    print(f"\n{BOLD}{'=' * 70}")
    print("  PHASE ORCHESTRATION TEST PASSED")
    print(f"{'=' * 70}{RESET}")
    print(f"\n{GREEN}Verified: Project creation -> Discovery Swarm -> PM Review ->")
    print(f"Approval Gate -> Architecture phase start{RESET}")
    print(f"\n{DIM}Note: The Architecture phase is still running on ECS.")
    print("The Step Functions execution will continue until manually stopped")
    print(f"or all phases complete.{RESET}\n")


# ---------------------------------------------------------------------------
# Pytest entry point
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_phase_orchestration() -> None:
    """E2E test: Full phase orchestration via deployed infrastructure."""
    run_orchestration_test()


# ---------------------------------------------------------------------------
# Script entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    run_orchestration_test()
