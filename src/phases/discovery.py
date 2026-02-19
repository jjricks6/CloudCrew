"""Discovery phase Swarm assembly.

The Discovery phase is where the PM parses the SOW, decomposes requirements,
and collaborates with the SA for initial architecture thinking. PM is the
entry point.

This module imports from agents/ and hooks/ — it is the ONLY module allowed
to import from agents/.
"""

from strands.hooks import HookProvider
from strands.multiagent.swarm import Swarm

from src.agents.pm import create_pm_agent
from src.agents.sa import create_sa_agent
from src.config import EXECUTION_TIMEOUT_DISCOVERY, NODE_TIMEOUT
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.memory_hook import MemoryHook
from src.hooks.resilience_hook import ResilienceHook


def create_discovery_swarm(
    stm_memory_id: str = "",
    ltm_memory_id: str = "",
    project_id: str = "",
    phase: str = "",
) -> Swarm:
    """Create the Discovery phase Swarm.

    Assembles PM (entry) + SA for requirements analysis and initial
    architecture thinking.

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
        nodes=[pm, sa],
        entry_point=pm,
        max_handoffs=10,
        max_iterations=10,
        execution_timeout=EXECUTION_TIMEOUT_DISCOVERY,
        node_timeout=NODE_TIMEOUT,
        repetitive_handoff_detection_window=6,
        repetitive_handoff_min_unique_agents=2,
        hooks=hooks,
        id="discovery-swarm",
    )
