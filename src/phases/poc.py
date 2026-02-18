"""POC (Proof of Concept) phase Swarm assembly.

Wires together the Dev, Infra, Data, Security, and SA agents into a Swarm
for the POC phase. Dev is the entry point; agents hand off work using
the auto-generated transfer_to_{name} tools.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging

from strands.hooks import HookProvider
from strands.multiagent.swarm import Swarm

from src.agents.data import create_data_agent
from src.agents.dev import create_dev_agent
from src.agents.infra import create_infra_agent
from src.agents.sa import create_sa_agent
from src.agents.security import create_security_agent
from src.config import EXECUTION_TIMEOUT_POC, NODE_TIMEOUT
from src.hooks.resilience_hook import ResilienceHook

logger = logging.getLogger(__name__)


def create_poc_swarm() -> Swarm:
    """Create the POC phase Swarm.

    Assembles Dev (entry point) -> Infra -> Data -> Security -> SA for
    rapid prototyping and proof-of-concept delivery.

    Configuration:
        - max_handoffs=15: Conservative limit to catch runaway loops
        - max_iterations=15: Matches handoff limit
        - execution_timeout: From config (default 2400s / 40 minutes)
        - node_timeout: From config (default 600s / 10 minutes)
        - repetitive_handoff_detection_window=8: Catches ping-pong patterns
        - repetitive_handoff_min_unique_agents=3: Requires agent diversity

    Returns:
        Configured Swarm ready for invocation with invocation_state.
    """
    dev = create_dev_agent()
    infra = create_infra_agent()
    data = create_data_agent()
    security = create_security_agent()
    sa = create_sa_agent()

    logger.info("Creating POC swarm with agents: dev, infra, data, security, sa")

    hooks: list[HookProvider] = [ResilienceHook()]

    return Swarm(
        nodes=[dev, infra, data, security, sa],
        entry_point=dev,
        max_handoffs=15,
        max_iterations=15,
        execution_timeout=EXECUTION_TIMEOUT_POC,
        node_timeout=NODE_TIMEOUT,
        hooks=hooks,
        repetitive_handoff_detection_window=8,
        repetitive_handoff_min_unique_agents=3,
        id="poc-swarm",
    )
