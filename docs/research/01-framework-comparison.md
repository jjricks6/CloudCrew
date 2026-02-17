# Multi-Agent Framework Comparison

Research conducted: 2026-02-16

## Purpose

Evaluate frameworks for a system where 5-7 specialized AI agents coordinate autonomously to deliver real software projects (architecture docs, IaC, application code, CI/CD pipelines). The ideal framework must support independent agent toolsets, human-in-the-loop approval gates, artifact production, and strong AWS ecosystem compatibility.

---

## 1. Strands Agents (AWS)

### Overview

Strands Agents is AWS's open-source SDK for building AI agents. It follows a model-driven approach where the LLM is the core decision-maker in an autonomous agent loop. Designed for simplicity and deep AWS integration.

### Multi-Agent Coordination Patterns

Strands supports four distinct patterns:

| Pattern | How it works | Best for |
|---------|-------------|----------|
| **Graph** | Developer defines nodes (agents) and edges (transitions). Conditional edges, cycles, parallel branches supported. Deterministic execution order. | Structured workflows with conditional logic |
| **Swarm** | Agents self-organize via `handoff_to_agent()`. Shared context with full task history. Emergent path. | Collaborative problem-solving where the next agent isn't known in advance |
| **Workflow** | Pre-defined DAG of tasks with dependency resolution, parallel execution, pause/resume | Repeatable, well-defined processes |
| **Agents as Tools** | Orchestrator agent calls sub-agents as tools. Hierarchical delegation. | Simple routing where a manager delegates to specialists |

Additionally supports **A2A (Agent-to-Agent) protocol** for cross-platform agent communication.

### Agent Communication

- **Graph**: Agents communicate through output propagation along edges. Entry points get original task; dependent nodes get original task + results from dependencies.
- **Swarm**: Shared context includes original task, agent history, shared knowledge from previous agents. Agents use `handoff_to_agent()` tool with message and context.
- **Workflow**: Task outputs automatically captured and passed as inputs to dependent tasks.
- **A2A**: HTTP-based protocol with agent cards for discovery. Supports streaming.

### Memory / State Management

- **`invocation_state`**: Dict passed to all agents, accessible in tools via `ToolContext` and in hooks. Not visible in LLM prompts. For config, DB connections, session IDs.
- **Shared context (Swarm)**: Full transcript of agent handoffs and contributed knowledge.
- **Input propagation (Graph)**: Each node receives original task + outputs from completed dependencies.
- **AgentCore Memory integration**: Session manager handles STM and LTM with namespace-based scoping.

### Independent Agent Toolsets

Yes, first-class support. Each `Agent` instance takes its own `tools` list:

```python
architect = Agent(system_prompt="...", tools=[diagram_tool, doc_tool])
developer = Agent(system_prompt="...", tools=[code_tool, test_tool, git_tool])
```

### Human-in-the-Loop

**Native interrupt/resume system** (discovered post-initial-research):
- `event.interrupt(name, reason)` — pauses agent execution, returns interrupts to caller
- `result.stop_reason == "interrupt"` — caller detects pause
- Resume by calling `agent(interrupt_responses)` with `InterruptResponseContent` objects
- Works in hooks (`BeforeToolCallEvent`, `BeforeNodeCallEvent`) and in multi-agent contexts
- Interrupt state is serializable (`to_dict()`/`from_dict()`) for persistence
- Session-managed between interrupt and resume

This closes the gap with LangGraph's `interrupt()`. The remaining difference: LangGraph has built-in checkpointing (persist state across process restarts), while Strands interrupt state lives in-process by default. For long-duration waits (hours/days), external persistence is still needed.

### Artifact Production

Via tools. Agents can write files, execute code, generate diagrams through custom tools. No built-in artifact management.

### Production Readiness

Good, especially for AWS-native:
- Deployable via AgentCore Runtime (serverless, managed)
- Also deployable on Lambda, ECS, EKS, Fargate
- Built-in observability through AgentCore Observability
- Security through AgentCore Identity
- Streaming and async support

### AWS Ecosystem Compatibility

**Best in class:**
- Native Bedrock model integration
- AgentCore Runtime, Memory, Gateway, Code Interpreter
- IAM, Secrets Manager, CloudWatch integration
- First-class CDK/CloudFormation support

### Key Strengths

- Deepest AWS integration of any framework
- Managed deployment via AgentCore
- Simple, clean API
- MCP tool protocol support
- Multiple well-documented multi-agent patterns
- Nested patterns (Swarm inside Graph)
- Rich hooks system for extensibility

### Key Weaknesses

- Younger framework; smaller community than LangGraph or CrewAI
- Multi-agent patterns less battle-tested at scale
- No built-in checkpointing/time-travel debugging (LangGraph advantage)
- Interrupt state not durably persisted by default (needs external persistence for long waits)
- Documentation still growing

---

## 2. LangGraph (LangChain)

### Overview

LangChain's framework for building stateful, multi-agent applications using graph-based orchestration. Most "engineering-focused" framework.

### Multi-Agent Coordination Patterns

- **Supervisor Pattern**: Supervisor routes work to specialized agent nodes
- **Hierarchical Supervisor**: Multi-level delegation
- **Network/Swarm**: Agents hand off directly using `Command` objects
- **Map-Reduce**: Fan-out to parallel agents, aggregate results
- **Custom Graph Topologies**: Arbitrary graphs with cycles, branches, conditional routing

### Agent Communication

- **Shared state object**: TypedDict or Pydantic model that all agents read/write
- **Conditional edges**: Graph structure determines execution flow
- **`Command` objects**: Simultaneously update state AND specify next node
- **Send API**: Dynamic fan-out at runtime

### Memory / State Management

**This is LangGraph's strongest feature:**
- **Checkpointing**: Every step checkpointed. Rewind, replay, branch from any point
- **Persistence**: Built-in savers for SQLite, PostgreSQL, custom backends
- **Structured typed state**: Not just chat messages — rich typed fields
- **Memory Store**: Key-value store persisting across sessions
- **Cross-thread memory**: Shared across conversation threads
- **Time-travel debugging**: Inspect state at any checkpoint, re-run from that point

### Independent Agent Toolsets

Yes. Each agent node configured with its own tools.

### Human-in-the-Loop

**Best in class:**
- **`interrupt()`**: Pause graph at any node, persist state, resume later
- **Breakpoints**: Before/after any node
- **Dynamic breakpoints**: Agents programmatically decide to pause
- **`Command(resume=...)`**: Resume with human-provided data
- Process can be terminated and restarted — human approval can happen hours/days later

### Production Readiness

**Most production-ready:**
- Deterministic execution paths with conditional routing
- Full state persistence and checkpointing
- Time-travel debugging
- **LangGraph Platform**: Managed deployment with task queues, cron, streaming, REST API
- **LangSmith**: Full observability, tracing, evaluation
- Async, streaming, concurrent execution

### AWS Ecosystem Compatibility

Good:
- Amazon Bedrock via `langchain-aws` package
- Pre-built integrations for DynamoDB, S3, SQS
- Deployable on ECS/EKS/Lambda
- No native AWS managed service (LangGraph Platform is separate)

### Key Strengths

- Most mature state management and persistence
- Production-grade HITL with interrupt/resume
- Time-travel debugging
- Strong observability via LangSmith
- Large tool ecosystem
- Parallel agent execution

### Key Weaknesses

- Not AWS-native. No managed deployment on AWS
- Tightly coupled to LangChain ecosystem
- Steeper learning curve (graph + state machine thinking)
- LangGraph Platform is paid for managed features
- "LangChain tax" — ecosystem complexity

---

## 3. CrewAI

### Overview

Python framework built around "crew" metaphor. Role-based agents with goals and backstories.

### Multi-Agent Coordination Patterns

- **Sequential Process**: Agents execute tasks one after another
- **Hierarchical Process**: Manager agent delegates to workers
- **Consensual Process** (experimental): Agents negotiate

### Agent Communication

Implicit through task context chaining. Manager mediates in hierarchical mode. Delegation tool for explicit handoffs.

### Memory / State Management

- Short-term memory (within execution)
- Long-term memory (SQLite, persisted across runs)
- Entity memory (tracks mentioned entities)
- Text-based, not deeply structured

### Independent Agent Toolsets

Yes. Each agent gets its own `tools` list.

### Human-in-the-Loop

Basic: `human_input=True` per task. Console-based by default. Needs custom webhook integration for production.

### Production Readiness

Moderate:
- Agent loops and reliability issues in complex workflows
- Limited observability in open-source version
- CrewAI Enterprise adds monitoring (paid)

### AWS Ecosystem Compatibility

Neutral. Works with Bedrock via LiteLLM. No native AWS integrations.

### Key Strengths

- Intuitive role-based abstraction
- Low barrier to entry
- Good documentation
- Growing community

### Key Weaknesses

- Agent loops and reliability issues
- Shallow memory system
- No graph-based routing
- Basic HITL
- No native AWS integration

---

## 4. AutoGen (Microsoft)

### Overview

Microsoft's multi-agent conversation framework. Redesigned in 0.4 with event-driven architecture.

### Multi-Agent Coordination Patterns

- Two-Agent Chat, Sequential Chat, Group Chat
- Selector Group Chat (LLM-based speaker selection)
- Nested Chat, Swarm Pattern
- Magentic-One reference architecture

### Agent Communication

Conversation-based message passing. Event-driven in 0.4 with message bus. GroupChatManager manages turn-taking.

### Memory / State Management

- Chat history in `ChatCompletionContext`
- State serialization for checkpoint/resume
- No built-in persistent memory (must implement)

### Human-in-the-Loop

Good:
- `UserProxyAgent` represents human
- `Handoff` mechanism
- Configurable termination conditions

### Production Readiness

Moderate-Good:
- Event-driven architecture (0.4) is robust
- Microsoft-backed
- AutoGen Studio provides UI
- 0.2 → 0.4 transition fragmenting docs/community

### AWS Ecosystem Compatibility

Weak. Azure/OpenAI-first. Bedrock via LiteLLM only.

### Key Strengths

- Mature conversation-based coordination
- Strong code execution sandboxing
- Microsoft backing
- Magentic-One reference architecture

### Key Weaknesses

- Azure/OpenAI-centric
- Architecture transition fragmenting community
- Group chat can be noisy with many agents
- No built-in persistent memory
- Steep complexity curve

---

## 5. Comparative Matrix

| Dimension | Strands Agents | LangGraph | CrewAI | AutoGen |
|---|---|---|---|---|
| **Multi-agent patterns** | Graph, Swarm, Workflow, Tools, A2A | Supervisor, Hierarchy, Network, Map-Reduce, Custom | Sequential, Hierarchical, Consensual | Group Chat, Swarm, Nested, Selector |
| **State management** | invocation_state + AgentCore Memory | Checkpointing, typed state, time-travel | SQLite-based, text-oriented | Chat history, serializable |
| **HITL support** | Native interrupt/resume (good) | interrupt/resume + checkpointing (best) | human_input=True (basic) | UserProxyAgent (good) |
| **AWS compatibility** | Best (native) | Good (langchain-aws) | Neutral (LiteLLM) | Weak (Azure-first) |
| **Production readiness** | Good (AgentCore managed) | Best (Platform + LangSmith) | Moderate | Moderate-Good |
| **Independent toolsets** | Yes | Yes | Yes | Yes |
| **Learning curve** | Low-Medium | Medium-High | Low | Medium-High |
| **Community** | Growing (AWS-backed) | Very large | Large, growing fast | Large (Microsoft) |

---

## 6. Recommendation

**Strands Agents** is the recommended framework for CloudCrew:

1. **AWS-native** — AgentCore Memory, Gateway, Runtime eliminate the need to build custom infrastructure for memory, tool connectivity, and deployment
2. **Flexible multi-agent patterns** — Graph for phased delivery, Swarm for within-phase collaboration, Agents-as-Tools for simple delegation
3. **Each agent gets independent tools** — first-class design principle
4. **Hooks system** — mechanism for building custom approval gates, logging, guardrails
5. **A2A protocol** — future-proof for connecting to external agents
6. **Team familiarity** — existing Strands experience

**Update (2026-02-17):** Strands now has native `interrupt()` support via hooks, closing the main gap with LangGraph. For long-duration waits (customer approval over hours/days), we pair this with Step Functions `waitForTaskToken` for durable persistence. For short-duration within-phase HITL (clarifying questions), Strands interrupts handle it natively.

**Frameworks deprioritized:**
- **CrewAI**: Reliability concerns for production software delivery
- **AutoGen**: Azure-first orientation creates friction in AWS environment
