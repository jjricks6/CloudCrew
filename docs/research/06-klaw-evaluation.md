# Klaw Evaluation

Research conducted: 2026-02-16
Source: https://klaw.sh/docs

## What Klaw Is

Klaw is **"kubectl for AI agents"** — an operational platform for deploying, routing, monitoring, and managing AI agents in production. It's a single Go binary (~20MB) that brings Kubernetes-style operations to AI agent management.

**It is NOT an agent framework.** It does not define how agents reason, collaborate, or coordinate on shared goals. It manages the infrastructure around agents.

## Architecture

```
User (CLI/Slack/REST)
    ↓
Orchestrator (Router)
    ↓ routes message to correct agent
Agent (process or Docker container)
    ↓ agent loop: LLM → tools → result → repeat
Workspace (filesystem-based state)
```

### Key Components

| Component | What it does |
|-----------|-------------|
| **Controller** | Central brain managing the cluster (like K8s master) |
| **Nodes** | Worker machines running agents (like K8s workers) |
| **Orchestrator** | Message router — dispatches to correct agent based on rules/AI/hybrid |
| **Namespaces** | Team-based isolation with scoped permissions, tools, secrets |
| **Skills** | Modular capability bundles (tools + prompts + config) — like npm packages |
| **Channels** | Communication interfaces: CLI, Slack, REST API |

### Agent Definition

Agents are defined via config with:
- `name` — unique identifier
- `model` — LLM selection (300+ supported via unified router)
- `task` — purpose description
- `tools` — available capabilities (allowlist)
- `workdir` — filesystem scope
- `runtime` — process or Docker

### Runtime Modes

- **Process mode**: Full filesystem access, direct command execution
- **Docker mode**: Sandboxed containers with resource constraints

## Multi-Agent Capabilities

### What Klaw Offers

1. **Orchestrator routing** — Dispatches messages to the right agent based on:
   - Regex pattern matching (rules-based)
   - LLM-based selection (AI routing)
   - Hybrid (rules first, AI fallback)
   - Manual override (`@agent` syntax)

2. **Agent spawning** — An agent can create sub-agents via `agent_spawn` tool:
   ```json
   {
     "tool": "agent_spawn",
     "input": {
       "name": "frontend-worker",
       "task": "Create React components for auth",
       "model": "claude-sonnet-4-20250514"
     }
   }
   ```

3. **Namespace-based team organization** — Isolate by team/project:
   ```bash
   klaw create namespace frontend --cluster production
   klaw dispatch "Build login form" --namespace frontend
   ```

4. **Task dependencies** — `--depends-on` flag for sequential execution

5. **Distributed mode** — Controller/worker topology, TCP/JSON communication, agent-specific task routing across nodes

### What Klaw Does NOT Offer

- **No graph-based orchestration** — No conditional edges, no branching logic, no cycles
- **No swarm/emergent collaboration** — Agents don't hand off to each other autonomously
- **No shared structured state** — No equivalent of Strands' `invocation_state` or typed state objects
- **No approval gates** — No built-in HITL mechanism for pausing workflows pending human review
- **No output propagation** — Agent outputs don't automatically feed into other agents' inputs
- **No conditional routing within workflows** — The orchestrator is a router, not a workflow engine
- **No semantic memory** — Memory is file-based (MEMORY.md), not vector-searchable

## Memory Model

Klaw's memory is **filesystem-based**, stored in `~/.klaw/workspace/`:

| File | Purpose |
|------|---------|
| `SOUL.md` | Agent identity, values, principles |
| `AGENTS.md` | Registry of available agents |
| `TOOLS.md` | Tool documentation |
| `USER.md` | User preferences, project context |
| `MEMORY.md` | Accumulated patterns, learned solutions |
| `logs/` | Daily interaction records |

**Key characteristics:**
- Workspace files load into system prompt at initialization
- All agents share the workspace by default (can isolate per-agent)
- `auto_memory` lets agents write to MEMORY.md automatically
- Conversation history is thread-aware, per-channel
- No semantic search, no structured state, no vector storage
- No cross-session memory extraction (no LTM strategies)

## Comparison: Klaw vs Strands Agents

| Dimension | Klaw | Strands Agents |
|-----------|------|----------------|
| **Primary purpose** | Agent operations/deployment | Agent reasoning/coordination |
| **Multi-agent pattern** | Message routing | Graph, Swarm, Workflow, A2A |
| **Agent collaboration** | Spawn sub-agents, shared workspace | Autonomous handoffs, shared state, output propagation |
| **State management** | Filesystem (MEMORY.md) | invocation_state, AgentCore Memory (STM/LTM) |
| **HITL/Approval gates** | None | Hooks (custom build needed) |
| **Deployment** | Built-in (process/Docker/distributed) | AgentCore Runtime or self-managed |
| **Monitoring** | Built-in (logs, metrics, CLI) | AgentCore Observability |
| **Model support** | 300+ via unified router | Bedrock models primarily |
| **Namespace isolation** | Yes (K8s-style) | No built-in equivalent |
| **Skill packaging** | Yes (modular bundles) | Tools are Python functions/MCP |

## Assessment for CloudCrew

### Klaw is NOT a replacement for Strands Agents

Klaw solves a different problem. CloudCrew needs agents that:
- **Collaborate on shared goals** (Graph of Swarms pattern) — Klaw doesn't support this
- **Pass structured output between phases** — Klaw's orchestrator is a router, not a workflow engine
- **Maintain semantic memory** across sessions — Klaw uses flat files
- **Support approval gates** for customer review — Klaw has no HITL mechanism
- **Produce real artifacts** through coordinated multi-step workflows — Klaw's coordination is shallow

### Klaw COULD complement Strands Agents

Klaw could serve as the **operational layer** for CloudCrew:

1. **Agent deployment and lifecycle** — Use Klaw to deploy, monitor, and manage agent processes
2. **Namespace isolation** — Separate customer projects into namespaces with isolated secrets and permissions
3. **CLI/Slack interface** — Klaw's CLI and Slack integration could be the customer-facing interface
4. **Distributed scaling** — Klaw's controller/worker topology could distribute agent workloads across machines
5. **Monitoring** — `klaw logs`, `klaw get metrics` for operational visibility

But the actual agent reasoning, collaboration, state management, and workflow orchestration would still be Strands.

### Verdict

**Klaw is interesting but not the right tool for CloudCrew's core problem.** It's an ops platform for agents, not a multi-agent collaboration framework. The agent coordination it provides (routing + spawning) is too shallow for a system where agents need to autonomously collaborate through phased delivery with approval gates.

However, it's worth keeping on the radar as a potential **deployment/operations layer** if the self-managed deployment complexity of Strands agents becomes a pain point. The Kubernetes-style agent management model is compelling for production operations.

For now, AgentCore Runtime serves the same operational purpose with better integration into the Strands/AWS ecosystem.
