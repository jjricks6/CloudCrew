"""Architecture phase Swarm assembly.

Wires together all specialist agents into a Swarm for the Architecture phase.
SA is the entry point and hub — it consults specialists as needed (Data
Engineer for data model, Security for auth review, Developer for API
contracts, QA for test strategy, Infra for infrastructure design).

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging

from strands.hooks import HookProvider
from strands.multiagent.swarm import Swarm

from src.agents.data import create_data_agent
from src.agents.dev import create_dev_agent
from src.agents.infra import create_infra_agent
from src.agents.qa import create_qa_agent
from src.agents.sa import create_sa_agent
from src.agents.security import create_security_agent
from src.config import EXECUTION_TIMEOUT_ARCHITECTURE, NODE_TIMEOUT
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.resilience_hook import ResilienceHook

logger = logging.getLogger(__name__)


def create_architecture_swarm(
    project_id: str = "",
    phase: str = "",
) -> Swarm:
    """Create the Architecture phase Swarm.

    All specialist agents are available so SA can consult any expert as
    needed. The Swarm auto-creates handoff tools (transfer_to_{name})
    so agents can transfer work to each other organically.

    Configuration:
        - max_handoffs=20: Room for SA to consult multiple specialists
        - max_iterations=20: Matches handoff limit
        - execution_timeout: From config (default 2400s / 40 minutes)
        - node_timeout: From config (default 1800s / 30 minutes)
        - repetitive_handoff_detection_window=8: Catches ping-pong patterns
        - repetitive_handoff_min_unique_agents=3: Requires agent diversity

    Returns:
        Configured Swarm ready for invocation with invocation_state.
    """
    sa = create_sa_agent()
    dev = create_dev_agent()
    infra = create_infra_agent()
    data = create_data_agent()
    security = create_security_agent()
    qa = create_qa_agent()

    logger.info("Creating architecture swarm with agents: sa, dev, infra, data, security, qa")

    hooks: list[HookProvider] = [
        ResilienceHook(),
        MaxTokensRecoveryHook(),
        ActivityHook(project_id=project_id, phase=phase),
    ]

    return Swarm(
        nodes=[sa, dev, infra, data, security, qa],
        entry_point=sa,
        max_handoffs=20,
        max_iterations=20,
        execution_timeout=EXECUTION_TIMEOUT_ARCHITECTURE,
        node_timeout=NODE_TIMEOUT,
        hooks=hooks,
        repetitive_handoff_detection_window=8,
        repetitive_handoff_min_unique_agents=3,
        id="architecture-swarm",
    )
