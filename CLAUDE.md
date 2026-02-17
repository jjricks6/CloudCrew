# CloudCrew

AI-powered ProServe team: 7 specialized agents (PM, SA, Infra, Dev, Data, Security, QA) collaborate via Strands Agents SDK to deliver real software projects.

## Architecture

- **Phase orchestration**: Step Functions (`waitForTaskToken` for durable approval gates)
- **Within-phase collaboration**: Strands Swarm (agent handoffs)
- **Memory**: AgentCore Memory (STM/LTM) + DynamoDB (task ledger) + Git (artifacts) + Bedrock KB (search)
- **Phase execution**: ECS Fargate (not Lambda — Swarms exceed 15-min limit)
- **Dashboard**: React SPA (chat, kanban, artifact browser)

See `docs/architecture/` for full architecture, agent specs, and implementation guide.

## Mandatory Commands

After making ANY code changes, you MUST run:

```bash
make check
```

This runs format + lint + typecheck + test. Do NOT skip this. Do NOT commit code that fails `make check`.

If `make check` fails, fix the issue and re-run. If a test doesn't pass after 3 attempts, stop and ask for help.

## Module Boundaries

```
src/
├── agents/     # Agent definitions (imports: tools/, hooks/, templates/, state/, config)
├── tools/      # Strands tool functions (imports: state/, config — NEVER agents/)
├── hooks/      # Strands hook providers (imports: state/, config — NEVER agents/, tools/)
├── templates/  # Artifact templates (imports: NOTHING — pure data)
├── state/      # DynamoDB operations, Pydantic models (imports: config — NEVER agents/, tools/)
├── phases/     # Phase Swarm setup (imports: agents/, config)
└── config.py   # Configuration constants (imports: NOTHING from src/)
```

Import rules:
- `tools/` NEVER imports from `agents/` — tools are agent-agnostic
- `hooks/` NEVER imports from `agents/` or `tools/` — hooks are generic
- `state/` NEVER imports from `agents/` or `tools/` — state layer is independent
- `templates/` imports NOTHING — it contains only template strings/data
- `config.py` imports NOTHING from `src/` — it reads from env vars only
- `phases/` is the ONLY module that imports from `agents/` (to assemble Swarms)
- No circular imports. Ever. If you need shared types, put them in `state/models.py`.

## Domain Ownership

| If you need to change... | The owner is... | Files live in... |
|--------------------------|----------------|-----------------|
| Agent definitions, system prompts | Agent specs | `src/agents/` |
| Tool implementations | Tool module | `src/tools/` |
| DynamoDB operations, data models | State module | `src/state/` |
| Swarm configuration per phase | Phase module | `src/phases/` |
| Hook behaviors (memory, approval, budget) | Hooks module | `src/hooks/` |
| Artifact output formats | Templates | `src/templates/` |
| Model IDs, env vars, constants | Config | `src/config.py` |
| CloudCrew infrastructure | Terraform | `infra/terraform/` |
| Customer dashboard | React app | `dashboard/` |
| Architecture decisions | ADR | `docs/architecture/` |

Do NOT create new top-level directories in `src/` without architectural justification.

## Code Standards

- Python 3.12+, type hints on ALL functions (mypy strict)
- Use Pydantic models for data structures (not raw dicts)
- One class per file for agents. One function per file for tools is OK if small.
- Max file length: 500 lines. If longer, split it.
- Use `logging` (not `print`). Structured logging with context (project_id, phase, agent_name).
- Use `pathlib.Path` (not `os.path`).
- Env-based configuration via `src/config.py`. NEVER hardcode secrets, ARNs, or endpoints.
- Docstrings on all public functions and classes.

## NEVER Rules

- NEVER import from `agents/` in `tools/`, `hooks/`, or `state/` — see module boundaries
- NEVER use `print()` — use `logging`
- NEVER hardcode AWS credentials, ARNs, endpoints, or secrets
- NEVER use `# type: ignore` without a comment explaining why
- NEVER use `Any` type without a comment explaining why
- NEVER create workaround code for upstream issues — fix the root cause or file an issue
- NEVER use `git commit --no-verify`
- NEVER skip `make check` before committing
- NEVER create a new module that duplicates functionality of an existing one — enhance the existing module
- NEVER put business logic in hooks — hooks are for cross-cutting concerns (logging, memory, auth)
- NEVER modify generated files directly — modify the source and regenerate
- NEVER use bare `except:` — always catch specific exceptions
- NEVER use mutable default arguments

## Testing

- Every new function needs a test. No exceptions.
- Tests go in `tests/` mirroring the `src/` structure: `tests/unit/tools/test_git_tools.py`
- Use `pytest` markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- Mock external services (Bedrock, DynamoDB, Git) in unit tests
- Architecture tests in `tests/architecture/` enforce module boundaries — don't break them
- **Coverage ratchet**: `fail_under` in pyproject.toml starts at 0 (no code yet). When the first module lands, raise it to match actual coverage. It must never decrease — only stay the same or go up. If your PR drops coverage below the threshold, add tests until it passes.

## Documentation Lockstep

| If you changed... | Then update... |
|-------------------|---------------|
| Agent tools or system prompts | `docs/architecture/agent-specifications.md` |
| Phase composition or Swarm config | `docs/architecture/final-architecture.md` |
| Build steps, project structure, or config | `docs/architecture/implementation-guide.md` |
| A significant technical decision | Add an ADR in the project repo |

## Git Workflow

**Strategy**: Trunk-based development. `main` is the production branch. All changes go through short-lived feature branches and pull requests. Direct pushes to `main` are blocked.

### Branch Naming

Format: `<type>/<short-kebab-description>`

| Type | Use when... | Example |
|------|-------------|---------|
| `feat/` | Adding new functionality | `feat/pm-agent-system-prompt` |
| `fix/` | Fixing a bug | `fix/dynamo-ttl-overflow` |
| `refactor/` | Restructuring without behavior change | `refactor/extract-tool-registry` |
| `test/` | Adding or fixing tests only | `test/swarm-handoff-coverage` |
| `docs/` | Documentation changes only | `docs/update-phase-diagram` |
| `chore/` | Config, deps, CI, infra tooling | `chore/upgrade-strands-sdk` |
| `infra/` | Terraform/IaC changes | `infra/ecs-fargate-cluster` |

Rules:
- All lowercase, kebab-case. No underscores, no camelCase.
- Keep it under 50 characters total.
- NEVER use your name or a date in a branch name.
- NEVER reuse a branch name after it's merged. Create a new one.
- Delete branches after merge.

### Commit Messages

Format: **single-line conventional commit**, enforced by pre-commit hook. No body — all context goes in the PR description.

```
<type>(<optional scope>): <short imperative description>
```

**Types**: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`, `perf`, `build`

**Scopes** (optional, match src/ modules): `agents`, `tools`, `hooks`, `state`, `templates`, `phases`, `config`, `infra`, `dashboard`

Examples:
```
feat(agents): add PM agent with SOW review tool
fix(state): handle missing TTL on task ledger items
refactor(tools): extract common git operations to base
test(phases): add Swarm handoff integration tests
docs: update architecture for ECS Fargate decision
chore(ci): add coverage threshold to quality gate
```

Rules:
- **Single line only** — max 72 characters. No body, no bullet lists.
- Imperative mood: "add feature" not "added feature" or "adding feature".
- No period at the end.
- One logical change per commit. If you need "and" in the message, it's two commits.
- **AI attribution**: Always include a `Co-Authored-By` trailer when committing AI-generated code:
  ```
  Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
  ```
- NEVER use `git commit --no-verify`.
- NEVER amend commits that have been pushed.

### Pull Request Workflow

1. Create a feature branch from `main`.
2. Make focused commits. Run `make check` before each commit.
3. Push the branch and open a PR against `main`.
4. PR must pass CI (lint, typecheck, test, security, architecture tests).
5. PR gets reviewed, then merged (squash merge preferred for feature branches).
6. Delete the branch after merge.

PR title follows the same conventional commit format as the commit message subject.

### NEVER Rules (Git-specific)

- NEVER push directly to `main` — always use a PR.
- NEVER force-push to `main`. Force-push to feature branches is OK if you're the only one on it.
- NEVER commit secrets, credentials, `.env` files, or private keys.
- NEVER commit generated files (`.pyc`, `__pycache__/`, `.terraform/`, `node_modules/`).
- NEVER create merge commits on feature branches — rebase onto `main` instead.
- NEVER leave a branch open for more than a few days — keep branches short-lived.
