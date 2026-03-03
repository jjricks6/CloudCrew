"""POC (Proof of Concept) phase Swarm assembly.

Wires together all specialist agents into a Swarm for the POC phase.
PM is the entry point — it reads the task ledger, delegates to specialists,
and coordinates the build→review→security cycle. All agents are available
for handoffs so the team can collaborate organically.

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
from src.config import EXECUTION_TIMEOUT_POC, NODE_TIMEOUT
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.resilience_hook import ResilienceHook

logger = logging.getLogger(__name__)


def create_poc_swarm(
    project_id: str = "",
    phase: str = "",
) -> Swarm:
    """Create the POC phase Swarm.

    PM is the entry point — it reviews the task ledger and architecture
    from prior phases, then delegates to specialists. Dev builds,
    QA validates, Security scans, Infra provisions, and SA/Data consult.

    Configuration:
        - max_handoffs=25: High enough for per-module build->review cycles
        - max_iterations=25: Matches handoff limit
        - execution_timeout: From config (default 2400s / 40 minutes)
        - node_timeout: From config (default 1800s / 30 minutes)
        - repetitive_handoff_detection_window=8: Catches ping-pong patterns
        - repetitive_handoff_min_unique_agents=3: Requires agent diversity

    Returns:
        Configured Swarm ready for invocation with invocation_state.
    """
    pm = create_pm_agent()
    dev = create_dev_agent()
    infra = create_infra_agent()
    data = create_data_agent()
    security = create_security_agent()
    sa = create_sa_agent()
    qa = create_qa_agent()

    logger.info("Creating POC swarm with agents: pm, dev, infra, data, security, sa, qa")

    hooks: list[HookProvider] = [
        ResilienceHook(),
        MaxTokensRecoveryHook(),
        ActivityHook(project_id=project_id, phase=phase),
    ]

    return Swarm(
        nodes=[pm, dev, infra, data, security, sa, qa],
        entry_point=pm,
        max_handoffs=25,
        max_iterations=25,
        execution_timeout=EXECUTION_TIMEOUT_POC,
        node_timeout=NODE_TIMEOUT,
        hooks=hooks,
        repetitive_handoff_detection_window=8,
        repetitive_handoff_min_unique_agents=3,
        id="poc-swarm",
    )
