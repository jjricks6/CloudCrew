"""DynamoDB task ledger operations.

Reads and writes the structured project task ledger to DynamoDB.
This module imports from config and state/models — NEVER from agents/ or tools/.
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import boto3

from src.config import AWS_REGION
from src.state.models import (
    Assumption,
    Blocker,
    Decision,
    DeliverableItem,
    Fact,
    TaskLedger,
)

logger = logging.getLogger(__name__)

# Maps section names to their Pydantic model classes for validation.
SECTION_MODELS: dict[str, type[Fact | Assumption | Decision | Blocker]] = {
    "facts": Fact,
    "assumptions": Assumption,
    "decisions": Decision,
    "blockers": Blocker,
}


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def _get_table(table_name: str) -> Any:
    """Get a DynamoDB Table resource.

    Args:
        table_name: Name of the DynamoDB table.

    Returns:
        A boto3 DynamoDB Table resource.
    """
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    return dynamodb.Table(table_name)


def read_ledger(table_name: str, project_id: str) -> TaskLedger:
    """Read the task ledger for a project from DynamoDB.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.

    Returns:
        TaskLedger populated from DynamoDB, or an empty ledger if not found.
    """
    table = _get_table(table_name)
    response = table.get_item(
        Key={"PK": f"PROJECT#{project_id}", "SK": "LEDGER"},
    )
    item = response.get("Item")
    if not item:
        logger.info("No ledger found for project %s, returning empty", project_id)
        return TaskLedger(project_id=project_id)
    return TaskLedger.model_validate(item.get("data", {}))


def write_ledger(table_name: str, project_id: str, ledger: TaskLedger) -> None:
    """Write the full task ledger to DynamoDB.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        ledger: The TaskLedger to persist.
    """
    table = _get_table(table_name)
    # Convert to JSON-safe dict (handles enums, nested models)
    data = json.loads(ledger.model_dump_json())
    table.put_item(
        Item={
            "PK": f"PROJECT#{project_id}",
            "SK": "LEDGER",
            "data": data,
        },
    )
    logger.info("Wrote ledger for project %s", project_id)


def append_to_section(
    table_name: str,
    project_id: str,
    section: str,
    entry: dict[str, Any],
) -> TaskLedger:
    """Append an entry to a ledger section.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        section: One of 'facts', 'assumptions', 'decisions', 'blockers'.
        entry: Dict matching the section's Pydantic model.

    Returns:
        The updated TaskLedger.

    Raises:
        ValueError: If the section name is invalid.
    """
    if section not in SECTION_MODELS:
        valid = ", ".join(sorted(SECTION_MODELS.keys()))
        msg = f"Invalid section '{section}'. Must be one of: {valid}"
        raise ValueError(msg)

    ledger = read_ledger(table_name, project_id)
    model_cls = SECTION_MODELS[section]
    validated = model_cls.model_validate(entry)
    section_list: list[Any] = getattr(ledger, section)
    section_list.append(validated)
    ledger.updated_at = _now_iso()
    write_ledger(table_name, project_id, ledger)
    logger.info("Appended entry to %s for project %s", section, project_id)
    return ledger


def update_deliverables(
    table_name: str,
    project_id: str,
    phase: str,
    deliverables: list[dict[str, Any]],
) -> TaskLedger:
    """Update deliverables for a specific phase.

    Args:
        table_name: DynamoDB table name.
        project_id: The project identifier.
        phase: The phase to update deliverables for.
        deliverables: List of deliverable dicts.

    Returns:
        The updated TaskLedger.
    """
    ledger = read_ledger(table_name, project_id)
    ledger.deliverables[phase] = [DeliverableItem.model_validate(d) for d in deliverables]
    ledger.updated_at = _now_iso()
    write_ledger(table_name, project_id, ledger)
    logger.info("Updated deliverables for phase %s, project %s", phase, project_id)
    return ledger


def format_ledger(ledger: TaskLedger) -> str:
    """Format a TaskLedger as a human-readable string for LLM consumption.

    Args:
        ledger: The TaskLedger to format.

    Returns:
        Structured text representation of the ledger.
    """
    lines = [
        f"# Task Ledger: {ledger.project_name or ledger.project_id}",
        f"**Customer:** {ledger.customer or 'Not set'}",
        f"**Phase:** {ledger.current_phase} ({ledger.phase_status})",
        "",
    ]

    if ledger.facts:
        lines.append("## Facts")
        for f in ledger.facts:
            lines.append(f"- {f.description} (source: {f.source})")
        lines.append("")

    if ledger.assumptions:
        lines.append("## Assumptions")
        for a in ledger.assumptions:
            lines.append(f"- [{a.confidence}] {a.description}")
        lines.append("")

    if ledger.decisions:
        lines.append("## Decisions")
        for d in ledger.decisions:
            adr_ref = f" (ADR: {d.adr_path})" if d.adr_path else ""
            lines.append(f"- {d.description} — {d.rationale}{adr_ref}")
        lines.append("")

    if ledger.blockers:
        lines.append("## Blockers")
        for b in ledger.blockers:
            lines.append(f"- [{b.status}] {b.description} (assigned: {b.assigned_to})")
        lines.append("")

    if ledger.deliverables:
        lines.append("## Deliverables")
        for phase, items in ledger.deliverables.items():
            lines.append(f"### {phase}")
            for item in items:
                lines.append(f"- {item.name} {item.version} ({item.git_path}) — {item.created_at}")
        lines.append("")

    if not any([ledger.facts, ledger.assumptions, ledger.decisions, ledger.blockers]):
        lines.append("*No entries yet.*")

    return "\n".join(lines)
