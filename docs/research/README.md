# CloudCrew Research

Research conducted 2026-02-16 to evaluate frameworks, patterns, and technologies for building an AI-powered ProServe team.

## Documents

| Doc | Contents |
|-----|----------|
| [01-framework-comparison.md](01-framework-comparison.md) | Comparison of Strands Agents, LangGraph, CrewAI, AutoGen. Includes matrix and recommendation. |
| [02-strands-agents-deep-dive.md](02-strands-agents-deep-dive.md) | Detailed Strands patterns: Graph, Swarm, Workflow, Agents-as-Tools, A2A protocol. Code examples for each. Hooks system. Shared state. |
| [03-memory-and-state.md](03-memory-and-state.md) | Layered memory model. AgentCore Memory (STM/LTM). Git as shared workspace. DynamoDB for state. Knowledge Bases. Step Functions alternative. |
| [04-architecture-recommendation.md](04-architecture-recommendation.md) | Graph-of-Swarms pattern. Agent roster with roles/tools/prompts. Approval gate mechanism. Customer interaction model. Technology stack. Open questions. |
| [05-prior-art-and-coordination-patterns.md](05-prior-art-and-coordination-patterns.md) | Prior art survey across 7 domains: academic MAS, swarm intelligence, distributed computing, software automation, game AI, BPM, and recent multi-agent AI projects. Cross-domain synthesis with 10 key patterns and 6 new recommendations. |
| [06-klaw-evaluation.md](06-klaw-evaluation.md) | Evaluation of Klaw ("kubectl for AI agents"). Architecture, multi-agent capabilities, memory model, comparison with Strands. Verdict: ops platform, not a coordination framework. Potentially complementary. |

## Key Decisions

- **Framework:** Strands Agents (AWS-native, flexible multi-agent patterns, native interrupt/resume, team familiarity)
- **Phase Orchestration:** Step Functions (`waitForTaskToken` for durable HITL approval gates)
- **Within-Phase Coordination:** Strands Swarm (emergent agent collaboration with explicit handoffs)
- **Within-Phase HITL:** Strands native interrupts (for clarifying questions mid-phase)
- **Memory:** AgentCore Memory (STM/LTM) + Git repo (artifacts) + DynamoDB (task ledger) + Bedrock KB (semantic search)
- **Models:** Opus 4.6 (PM, SA, Security) + Sonnet (Dev, Infra, Data, QA)
- **Customer UI:** React SPA dashboard (chat with PM, kanban board, artifact browser)

See [docs/architecture/](../architecture/) for the final architecture and implementation guide.
