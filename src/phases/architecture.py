"""Architecture phase Swarm assembly.

Wires together the SA, Infra, and Security agents into a Swarm for the
Architecture phase. SA is the entry point; agents hand off work using
the auto-generated transfer_to_{name} tools.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging

from strands.multiagent.swarm import Swarm

from src.agents.infra import create_infra_agent
from src.agents.sa import create_sa_agent
from src.agents.security import create_security_agent

logger = logging.getLogger(__name__)


def create_architecture_swarm() -> Swarm:
    """Create the Architecture phase Swarm.

    Assembles SA (entry point) -> Infra -> Security with review cycle support.
    The Swarm auto-creates handoff tools so agents can transfer work to each
    other using transfer_to_sa, transfer_to_infra, transfer_to_security.

    Configuration:
        - max_handoffs=15: Conservative limit to catch runaway loops
        - max_iterations=15: Matches handoff limit
        - execution_timeout=1200s: 20 minutes total for the phase
        - node_timeout=300s: 5 minutes per agent turn
        - repetitive_handoff_detection_window=8: Catches ping-pong patterns
        - repetitive_handoff_min_unique_agents=3: Requires agent diversity

    Returns:
        Configured Swarm ready for invocation with invocation_state.
    """
    sa = create_sa_agent()
    infra = create_infra_agent()
    security = create_security_agent()

    logger.info("Creating architecture swarm with agents: sa, infra, security")

    return Swarm(
        nodes=[sa, infra, security],
        entry_point=sa,
        max_handoffs=15,
        max_iterations=15,
        execution_timeout=1200.0,
        node_timeout=300.0,
        repetitive_handoff_detection_window=8,
        repetitive_handoff_min_unique_agents=3,
        id="architecture-swarm",
    )
