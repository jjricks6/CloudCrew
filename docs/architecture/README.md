# CloudCrew Architecture

Architecture and implementation guidance for CloudCrew — an AI-powered ProServe team using 7 specialized agents.

## Documents

| Doc | Contents |
|-----|----------|
| [final-architecture.md](final-architecture.md) | Complete system architecture: two-tier orchestration (Step Functions + Strands Swarm), phase flow, HITL model, agent roster, memory architecture, task ledger schema, phase transition protocol, artifact templates, customer dashboard, full technology stack, design principles, decisions log. |
| [agent-specifications.md](agent-specifications.md) | Detailed specs for all 7 agents: PM, SA, Infra, Dev, Data, Security, QA. Includes role descriptions, model assignments, active phases, scoped tools, review responsibilities, full system prompts, and Swarm behavior guidelines. |
| [implementation-guide.md](implementation-guide.md) | 5-milestone build plan: M1 (single agent foundation), M2 (two-agent Swarm), M3 (task ledger + memory), M4 (Step Functions + approval gates), M5 (customer dashboard). Includes project structure, testing strategy, configuration, development workflow, risk mitigation. |

## Quick Reference

- **Framework:** Strands Agents SDK
- **Phase Orchestration:** AWS Step Functions (`waitForTaskToken`)
- **Within-Phase Coordination:** Strands Swarm
- **Models:** Opus 4.6 (PM, SA, Security) + Sonnet (Dev, Infra, Data, QA)
- **Memory:** AgentCore Memory (STM/LTM) + DynamoDB (task ledger) + Git (artifacts) + Bedrock KB (search)
- **Customer UI:** React SPA (chat + kanban + artifact browser)

See [../research/](../research/) for the research that led to these decisions.
