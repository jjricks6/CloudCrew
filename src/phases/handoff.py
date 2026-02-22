"""Handoff phase Swarm assembly.

Wires together all agents into a Swarm for the Handoff phase.
PM is the entry point and drives the final deliverable packaging,
knowledge transfer documentation, and customer handoff process. All
specialists are available for ops runbooks, API docs, compliance, etc.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging

from strands.hooks import HookProvider
from strands.multiagent.swarm import Swarm

from src.agents.data import create_data_agent
from src.agents.dev import create_dev_agent
from src.agents.infra import create_infra_agent
from src.agents.pm import create_pm_agent
from src.agents.qa import create_qa_agent
from src.agents.sa import create_sa_agent
from src.agents.security import create_security_agent
from src.config import EXECUTION_TIMEOUT_HANDOFF, NODE_TIMEOUT
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.memory_hook import MemoryHook
from src.hooks.resilience_hook import ResilienceHook

logger = logging.getLogger(__name__)


def create_handoff_swarm(
    stm_memory_id: str = "",
    ltm_memory_id: str = "",
    project_id: str = "",
    phase: str = "",
) -> Swarm:
    """Create the Handoff phase Swarm.

    All agents are available so PM can delegate deliverable authoring
    to the right specialist: Infra for ops runbooks, Dev for API docs,
    Security for compliance reports, SA for knowledge transfer.

    Args:
        stm_memory_id: AgentCore Memory ID for STM. Empty to disable.
        ltm_memory_id: AgentCore Memory ID for LTM. Empty to disable.

    Configuration:
        - max_handoffs=20: Room for PM to delegate across specialists
        - max_iterations=20: Matches handoff limit
        - execution_timeout: From config (default 1800s / 30 minutes)
        - node_timeout: From config (default 1800s / 30 minutes)
        - repetitive_handoff_detection_window=8: Catches ping-pong patterns
        - repetitive_handoff_min_unique_agents=3: Requires agent diversity

    Returns:
        Configured Swarm ready for invocation with invocation_state.
    """
    pm = create_pm_agent()
    sa = create_sa_agent()
    dev = create_dev_agent()
    infra = create_infra_agent()
    data = create_data_agent()
    security = create_security_agent()
    qa = create_qa_agent()

    logger.info("Creating handoff swarm with agents: pm, sa, dev, infra, data, security, qa")

    hooks: list[HookProvider] = [
        ResilienceHook(),
        MaxTokensRecoveryHook(),
        ActivityHook(project_id=project_id, phase=phase),
    ]
    if stm_memory_id or ltm_memory_id:
        hooks.append(
            MemoryHook(
                stm_memory_id=stm_memory_id,
                ltm_memory_id=ltm_memory_id,
            ),
        )

    return Swarm(
        nodes=[pm, sa, dev, infra, data, security, qa],
        entry_point=pm,
        max_handoffs=20,
        max_iterations=20,
        execution_timeout=EXECUTION_TIMEOUT_HANDOFF,
        node_timeout=NODE_TIMEOUT,
        repetitive_handoff_detection_window=8,
        repetitive_handoff_min_unique_agents=3,
        hooks=hooks,
        id="handoff-swarm",
    )
