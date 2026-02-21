"""Production phase Swarm assembly.

Wires together the Dev, Infra, Data, Security, and QA agents into a Swarm
for the Production phase. Dev is the entry point; QA replaces SA from the POC
phase to enforce quality gates before approval.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

import logging

from strands.hooks import HookProvider
from strands.multiagent.swarm import Swarm

from src.agents.data import create_data_agent
from src.agents.dev import create_dev_agent
from src.agents.infra import create_infra_agent
from src.agents.qa import create_qa_agent
from src.agents.security import create_security_agent
from src.config import EXECUTION_TIMEOUT_PRODUCTION, NODE_TIMEOUT
from src.hooks.activity_hook import ActivityHook
from src.hooks.max_tokens_recovery_hook import MaxTokensRecoveryHook
from src.hooks.resilience_hook import ResilienceHook

logger = logging.getLogger(__name__)


def create_production_swarm(
    project_id: str = "",
    phase: str = "",
) -> Swarm:
    """Create the Production phase Swarm.

    Assembles Dev (entry point) -> Infra -> Data -> Security -> QA for
    production-ready code delivery with quality gates.

    Configuration:
        - max_handoffs=25: High enough for per-module Infra->Security cycles
        - max_iterations=25: Matches handoff limit
        - execution_timeout: From config (default 3600s / 60 minutes)
        - node_timeout: From config (default 1800s / 30 minutes)
        - repetitive_handoff_detection_window=8: Catches ping-pong patterns
        - repetitive_handoff_min_unique_agents=3: Requires agent diversity

    Returns:
        Configured Swarm ready for invocation with invocation_state.
    """
    dev = create_dev_agent()
    infra = create_infra_agent()
    data = create_data_agent()
    security = create_security_agent()
    qa = create_qa_agent()

    logger.info("Creating production swarm with agents: dev, infra, data, security, qa")

    hooks: list[HookProvider] = [
        ResilienceHook(),
        MaxTokensRecoveryHook(),
        ActivityHook(project_id=project_id, phase=phase),
    ]

    return Swarm(
        nodes=[dev, infra, data, security, qa],
        entry_point=dev,
        max_handoffs=25,
        max_iterations=25,
        execution_timeout=EXECUTION_TIMEOUT_PRODUCTION,
        node_timeout=NODE_TIMEOUT,
        hooks=hooks,
        repetitive_handoff_detection_window=8,
        repetitive_handoff_min_unique_agents=3,
        id="production-swarm",
    )
