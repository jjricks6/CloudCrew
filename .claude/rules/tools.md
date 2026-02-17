---
paths:
  - "src/tools/**"
---

# Tool Implementation Rules

- Tools are Strands tool functions decorated with `@tool` or `@tool(context=True)`
- Tools NEVER import from `src/agents/` — tools are agent-agnostic
- One tool per function. Group related tools in one file (e.g., `git_tools.py` has all git tools)
- Every tool MUST have a docstring — this becomes the tool description the LLM sees

```python
from strands import tool

@tool
def my_tool(param: str) -> str:
    """One-line description of what this tool does.

    Args:
        param: What this parameter means.
    """
    ...
```

- For tools that need project context (project_id, phase, etc.), use `@tool(context=True)`:

```python
@tool(context=True)
def read_task_ledger(tool_context: ToolContext) -> str:
    """Read the current project task ledger."""
    project_id = tool_context.invocation_state.get("project_id")
    ...
```

- Scoped git write tools MUST validate the file path prefix before writing
- Tools should return strings (the LLM reads the output). For structured data, return JSON strings.
- Handle errors gracefully — return error messages as strings, don't raise exceptions that crash the agent
- Log tool invocations with project_id and agent context for observability
