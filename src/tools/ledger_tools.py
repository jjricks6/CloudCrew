"""Task ledger tools for reading and updating project state.

All agents get read_task_ledger. Only the PM agent gets update_task_ledger.
This module imports from state/ — NEVER from agents/.
"""

import json
import logging
from typing import Any

from strands import tool
from strands.types.tools import ToolContext

from src.state.ledger import (
    append_to_section,
    format_ledger,
    read_ledger,
    update_deliverables,
)

logger = logging.getLogger(__name__)


@tool(context=True)
def read_task_ledger(tool_context: ToolContext) -> str:
    """Read the current project task ledger.

    Returns the full task ledger formatted as structured text including
    facts, assumptions, decisions, blockers, and deliverables.

    Args:
        tool_context: Strands tool context (injected by framework).

    Returns:
        Formatted task ledger text, or an error message.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    table_name = tool_context.invocation_state.get("task_ledger_table", "")

    if not project_id or not table_name:
        return "Error: project_id or task_ledger_table not set in invocation state."

    try:
        ledger = read_ledger(table_name, project_id)
        return format_ledger(ledger)
    except Exception as e:
        logger.exception("Failed to read task ledger for project %s", project_id)
        return f"Error reading task ledger: {e}"


@tool(context=True)
def update_task_ledger(section: str, entry: str, tool_context: ToolContext) -> str:
    """Update a section of the task ledger. PM agent only.

    Appends an entry to one of the ledger sections or updates deliverables.

    Args:
        section: One of 'facts', 'assumptions', 'decisions',
            'blockers', 'deliverables'.
        entry: JSON string of the entry. Required fields per section:
            facts: description, source, timestamp (ISO8601).
            assumptions: description, confidence (HIGH/MEDIUM/LOW),
            timestamp.
            decisions: description, rationale, made_by (pm/sa/infra/
            security), timestamp. Optional: adr_path.
            blockers: description, assigned_to, status (OPEN/RESOLVED),
            timestamp.
            deliverables: phase, items (list of objects with name,
            git_path, status: IN_PROGRESS/COMPLETE/NEEDS_REVISION).
        tool_context: Strands tool context (injected by framework).

    Returns:
        Confirmation message or error.
    """
    project_id = tool_context.invocation_state.get("project_id", "")
    table_name = tool_context.invocation_state.get("task_ledger_table", "")

    if not project_id or not table_name:
        return "Error: project_id or task_ledger_table not set in invocation state."

    valid_sections = {"facts", "assumptions", "decisions", "blockers", "deliverables"}
    if section not in valid_sections:
        return f"Error: Invalid section '{section}'. Must be one of: {', '.join(sorted(valid_sections))}"

    try:
        parsed: dict[str, Any] = json.loads(entry)
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON in entry: {e}"

    try:
        if section == "deliverables":
            phase = parsed.get("phase", "")
            items = parsed.get("items", [])
            if not phase:
                return "Error: deliverables entry must include 'phase' key."
            update_deliverables(table_name, project_id, phase, items)
            return f"Updated deliverables for phase '{phase}'."

        append_to_section(table_name, project_id, section, parsed)
        return f"Added entry to {section}."
    except Exception as e:
        logger.exception("Failed to update %s for project %s", section, project_id)
        return f"Error updating {section}: {e}"
