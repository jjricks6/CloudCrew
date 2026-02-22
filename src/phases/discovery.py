"""Discovery phase Swarm assembly.

The Discovery phase is where the PM parses the SOW, decomposes requirements,
and collaborates with specialists for initial analysis. PM is the entry
point. All agents are available so PM can consult any specialist
(e.g., Data Engineer for data requirements, Security for compliance needs).

This module imports from agents/ and hooks/ — it is the ONLY module allowed
to import from agents/.
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
from src.config import EXECUTION_TIMEOUT_DISCOVERY, NODE_TIMEOUT
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.memory_hook import MemoryHook
from src.hooks.resilience_hook import ResilienceHook

logger = logging.getLogger(__name__)


def create_discovery_swarm(
    stm_memory_id: str = "",
    ltm_memory_id: str = "",
    project_id: str = "",
    phase: str = "",
) -> Swarm:
    """Create the Discovery phase Swarm.

    All agents are available so PM can consult any specialist during
    requirements analysis. PM drives the SOW decomposition and delegates
    to SA for architecture thinking, Data for data requirements, etc.

    Args:
        stm_memory_id: AgentCore Memory ID for STM. Empty to disable.
        ltm_memory_id: AgentCore Memory ID for LTM. Empty to disable.
        project_id: Project ID for activity tracking. Empty to disable.
        phase: Phase name for activity tracking.

    Returns:
        Configured Swarm ready for invocation.
    """
    pm = create_pm_agent()
    sa = create_sa_agent()
    dev = create_dev_agent()
    infra = create_infra_agent()
    data = create_data_agent()
    security = create_security_agent()
    qa = create_qa_agent()

    logger.info("Creating discovery swarm with agents: pm, sa, dev, infra, data, security, qa")

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
        max_handoffs=15,
        max_iterations=15,
        execution_timeout=EXECUTION_TIMEOUT_DISCOVERY,
        node_timeout=NODE_TIMEOUT,
        repetitive_handoff_detection_window=8,
        repetitive_handoff_min_unique_agents=3,
        hooks=hooks,
        id="discovery-swarm",
    )
