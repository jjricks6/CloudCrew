---
paths:
  - "src/agents/**"
---

# Agent Definition Rules

- Each agent lives in its own file: `src/agents/{name}.py`
- Shared config (model defs, invocation state builder) lives in `src/agents/base.py`
- Agent construction pattern:

```python
from strands import Agent
from src.agents.base import OPUS  # or SONNET
from src.tools.git_tools import git_read, git_write_{domain}

{name}_agent = Agent(
    name="{name}",
    model=OPUS,  # or SONNET — see agent-specifications.md
    system_prompt={NAME}_SYSTEM_PROMPT,
    tools=[...],  # Only domain-specific tools — see agent-specifications.md
    hooks=[...],  # Memory hook, budget hook
)
```

- System prompts are defined as module-level constants in the same file, NOT loaded from external files
- Every agent MUST have: `name`, `model`, `system_prompt`, `tools`
- Tool lists must match the agent specification in `docs/architecture/agent-specifications.md`
- Do not give an agent tools outside its domain. SA does not get terraform tools. Dev does not get security tools.
- Swarm behavior guidelines are appended to prompts in `src/phases/`, not in agent definitions
