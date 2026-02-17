# Strands Agents Deep Dive

Research conducted: 2026-02-16

## Multi-Agent Patterns in Detail

### Graph Pattern

The Graph is a deterministic directed graph where agents (or nested multi-agent systems) are nodes. Execution follows edge dependencies with output propagation.

**Key capabilities:**
- Conditional edges based on runtime state
- Cyclic graphs with execution limits
- Parallel branch execution
- Nested patterns (Swarm as a node in a Graph)
- Custom node types for deterministic business logic
- Multi-modal input support

**Graph construction:**

```python
from strands import Agent
from strands.multiagent import GraphBuilder

researcher = Agent(name="researcher", system_prompt="...")
analyst = Agent(name="analyst", system_prompt="...")
report_writer = Agent(name="report_writer", system_prompt="...")

builder = GraphBuilder()
builder.add_node(researcher, "research")
builder.add_node(analyst, "analysis")
builder.add_node(report_writer, "report")

builder.add_edge("research", "analysis")
builder.add_edge("analysis", "report")
builder.set_entry_point("research")
builder.set_execution_timeout(600)

graph = builder.build()
result = graph("Research the impact of AI on healthcare")
```

**Conditional edges:**

```python
def only_if_successful(state):
    research_node = state.results.get("research")
    if not research_node:
        return False
    result_text = str(research_node.result)
    return "successful" in result_text.lower()

builder.add_edge("research", "analysis", condition=only_if_successful)
```

**Wait for ALL dependencies (not just any):**

```python
from strands.multiagent.graph import GraphState
from strands.multiagent.base import Status

def all_dependencies_complete(required_nodes: list[str]):
    def check(state: GraphState) -> bool:
        return all(
            node_id in state.results and state.results[node_id].status == Status.COMPLETED
            for node_id in required_nodes
        )
    return check

builder.add_edge("A", "Z", condition=all_dependencies_complete(["A", "B", "C"]))
builder.add_edge("B", "Z", condition=all_dependencies_complete(["A", "B", "C"]))
builder.add_edge("C", "Z", condition=all_dependencies_complete(["A", "B", "C"]))
```

**Nested Swarm inside Graph:**

```python
from strands.multiagent import GraphBuilder, Swarm

research_agents = [
    Agent(name="medical_researcher", system_prompt="..."),
    Agent(name="tech_researcher", system_prompt="..."),
]
research_swarm = Swarm(research_agents)
analyst = Agent(system_prompt="Analyze the research.")

builder = GraphBuilder()
builder.add_node(research_swarm, "research_team")
builder.add_node(analyst, "analysis")
builder.add_edge("research_team", "analysis")
graph = builder.build()
```

**Custom nodes for deterministic logic:**

```python
from strands.multiagent.base import MultiAgentBase, NodeResult, Status, MultiAgentResult

class FunctionNode(MultiAgentBase):
    def __init__(self, func, name=None):
        super().__init__()
        self.func = func
        self.name = name or func.__name__

    async def invoke_async(self, task, invocation_state, **kwargs):
        result = self.func(task if isinstance(task, str) else str(task))
        # ... wrap in MultiAgentResult
```

**Common topologies:**
1. Sequential Pipeline: A → B → C → D
2. Parallel Processing with Aggregation: A → [B, C, D] → E
3. Branching Logic: A → conditional → B or C
4. Feedback Loop: Writer → Reviewer → (needs revision?) → Writer again

**Graph results:**

```python
result = graph("task")
result.status          # COMPLETED, FAILED, etc.
result.execution_order # ordered list of executed nodes
result.results["analysis"].result  # specific node result
result.execution_time  # milliseconds
result.accumulated_usage  # token usage
```

---

### Swarm Pattern

A collaborative system where agents autonomously hand off to each other with shared context.

**Key capabilities:**
- Self-organizing teams with shared working memory
- Each agent sees: full task context, agent history, shared knowledge from previous agents
- Tool-based coordination via `handoff_to_agent()`
- Safety mechanisms: max handoffs, max iterations, execution timeout, node timeout, repetitive handoff detection
- Multi-modal input support

**Swarm construction:**

```python
from strands import Agent
from strands.multiagent import Swarm

researcher = Agent(name="researcher", system_prompt="...")
coder = Agent(name="coder", system_prompt="...")
reviewer = Agent(name="reviewer", system_prompt="...")
architect = Agent(name="architect", system_prompt="...")

swarm = Swarm(
    [coder, researcher, reviewer, architect],
    entry_point=researcher,
    max_handoffs=20,
    max_iterations=20,
    execution_timeout=900.0,  # 15 minutes
    node_timeout=300.0,       # 5 min per agent
    repetitive_handoff_detection_window=8,
    repetitive_handoff_min_unique_agents=3
)

result = swarm("Design and implement a REST API for a todo app")
```

**Shared context format (what each agent sees):**

```
Handoff Message: [message from previous agent]
User Request: [original task]
Previous agents who worked on this: data_analyst → code_reviewer
Shared knowledge from previous agents:
  - data_analyst: {"issue_location": "line 42", ...}
  - code_reviewer: {"code_quality": "good", ...}
Other agents available for collaboration:
  Agent name: security_specialist. Description: ...
```

**Configuration:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `entry_point` | First agent | Starting agent |
| `max_handoffs` | 20 | Max agent-to-agent transfers |
| `max_iterations` | 20 | Max total iterations |
| `execution_timeout` | 900s (15m) | Total timeout |
| `node_timeout` | 300s (5m) | Per-agent timeout |
| `repetitive_handoff_detection_window` | 0 (disabled) | Check window for ping-pong |
| `repetitive_handoff_min_unique_agents` | 0 (disabled) | Min unique agents in window |

---

### Workflow Pattern

Pre-defined task DAG with dependency resolution, parallel execution, pause/resume.

**Key capabilities:**
- Task-level dependency management
- Parallel execution of independent tasks
- Built-in pause/resume
- Status monitoring with progress percentage
- Automatic retries for failed tasks
- Priority-based execution

**Workflow construction (via tool):**

```python
from strands import Agent
from strands_tools import workflow

agent = Agent(tools=[workflow])

agent.tool.workflow(
    action="create",
    workflow_id="data_analysis",
    tasks=[
        {"task_id": "extract", "description": "Extract data...", "priority": 5},
        {"task_id": "analyze", "description": "Analyze...", "dependencies": ["extract"], "priority": 3},
        {"task_id": "report", "description": "Generate report...", "dependencies": ["analyze"], "priority": 2}
    ]
)

agent.tool.workflow(action="start", workflow_id="data_analysis")
agent.tool.workflow(action="status", workflow_id="data_analysis")
```

**Workflow is a tool from strands-agents-tools, not core SDK.**

---

### Agents as Tools Pattern

Orchestrator agent calls sub-agents as tools. Simple hierarchical delegation.

```python
from strands import Agent, tool

@tool
def research_assistant(query: str) -> str:
    """Process research-related queries."""
    agent = Agent(
        system_prompt="You are a research specialist...",
        tools=[retrieve, http_request]
    )
    response = agent(query)
    return str(response)

@tool
def developer_assistant(task: str) -> str:
    """Handle development tasks."""
    agent = Agent(
        system_prompt="You are a developer...",
        tools=[code_gen, test_runner, git_tool]
    )
    response = agent(task)
    return str(response)

orchestrator = Agent(
    system_prompt="Route queries to the right specialist...",
    tools=[research_assistant, developer_assistant]
)
```

---

### A2A (Agent-to-Agent) Protocol

Open standard for cross-platform agent communication.

**Server:**

```python
from strands import Agent
from strands.multiagent.a2a import A2AServer

agent = Agent(name="Calculator Agent", description="...", tools=[calculator])
a2a_server = A2AServer(agent=agent, host="0.0.0.0", port=9000)
a2a_server.serve()
```

**Client tool:**

```python
from strands_tools.a2a_client import A2AClientToolProvider

provider = A2AClientToolProvider(known_agent_urls=["http://research-agent:9000"])
orchestrator = Agent(tools=provider.tools)
```

**Supports:** Agent discovery via agent cards, streaming, path-based mounting for load balancers, custom task stores.

---

## Shared State Across Patterns

Both Graph and Swarm support `invocation_state` — a dict passed to all agents, accessible in tools and hooks but NOT in LLM prompts:

```python
shared_state = {
    "user_id": "user123",
    "session_id": "sess456",
    "database_connection": db_conn  # non-serializable objects OK
}

result = graph("task", invocation_state=shared_state)
# or
result = swarm("task", invocation_state=shared_state)
```

Access in tools:

```python
@tool(context=True)
def query_data(query: str, tool_context: ToolContext) -> str:
    user_id = tool_context.invocation_state.get("user_id")
    db = tool_context.invocation_state.get("database_connection")
```

Access in hooks:

```python
def log_with_context(event: BeforeToolCallEvent) -> None:
    user_id = event.invocation_state.get("user_id")
```

---

## Hooks System

Lifecycle callbacks for extending agent and orchestrator behavior.

### Single-Agent Events

| Event | Description |
|-------|-------------|
| `AgentInitializedEvent` | Agent constructor complete |
| `BeforeInvocationEvent` | Start of agent invocation |
| `AfterInvocationEvent` | End of agent invocation |
| `MessageAddedEvent` | Message added to history |
| `BeforeModelCallEvent` | Before LLM inference |
| `AfterModelCallEvent` | After LLM inference |
| `BeforeToolCallEvent` | Before tool execution (can cancel) |
| `AfterToolCallEvent` | After tool execution (can modify result) |

### Multi-Agent Events (Python only)

| Event | Description |
|-------|-------------|
| `MultiAgentInitializedEvent` | Orchestrator initialized |
| `BeforeMultiAgentInvocationEvent` | Before orchestrator execution |
| `AfterMultiAgentInvocationEvent` | After orchestrator execution |
| `BeforeNodeCallEvent` | Before individual node execution |
| `AfterNodeCallEvent` | After individual node execution |

### Modifiable event properties

- `BeforeToolCallEvent.cancel_tool` — Cancel tool with message
- `BeforeToolCallEvent.selected_tool` — Replace tool
- `BeforeToolCallEvent.tool_use` — Modify parameters
- `AfterToolCallEvent.result` — Modify tool result
- `AfterModelCallEvent.retry` — Request model retry

### HookProvider pattern

```python
class ApprovalGateHook(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(AfterNodeCallEvent, self.check_approval)

    def check_approval(self, event: AfterNodeCallEvent) -> None:
        if event.node_id in ["architecture", "poc", "production"]:
            # Signal external system for approval
            # Could write to DynamoDB, send SQS message, etc.
            pass
```

### Layered hooks

Individual agents can have their own hooks AND the orchestrator has separate hooks:

```python
agent1 = Agent(tools=[tool1], hooks=[AgentLevelHook()])
agent2 = Agent(tools=[tool2], hooks=[AgentLevelHook()])

orchestrator = Graph(
    agents={"agent1": agent1, "agent2": agent2},
    hooks=[OrchestratorLevelHook()]
)
```

---

## Streaming and Async

Both Graph and Swarm support:
- `invoke_async()` for async execution
- `stream_async()` for real-time event streaming

Event types during streaming:
- `multiagent_node_start` — agent taking control
- `multiagent_node_stream` — agent producing output
- `multiagent_handoff` — control transfer between agents
- `multiagent_node_stop` — node completed
- `multiagent_result` — final result
