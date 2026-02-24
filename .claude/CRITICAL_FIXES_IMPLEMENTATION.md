# Critical Fixes Implementation Guide

This document provides step-by-step implementation details for the 4 critical gaps identified in the retrospective.

---

## FIX #1: Authorization Checks on APIs (SECURITY CRITICAL)

**Status:** Blocking all production use
**Effort:** 2-3 hours
**Files to Modify:** `src/phases/api_handlers.py`

### Problem

Currently, any authenticated user can:
- Approve/revise any project (not just their own)
- Access any project's artifacts
- Submit interrupt responses for any project
- Access chat for any project

This is a **CRITICAL SECURITY ISSUE** in multi-tenant deployments.

### Solution

Add authorization checks using Cognito claims from API Gateway Lambda Authorizer.

#### Step 1: Add Authorization Verification Function

```python
# File: src/phases/api_handlers.py

def _verify_project_access(
    event: dict[str, Any],
    project_id: str,
) -> tuple[bool, str]:
    """Verify that the authenticated user owns this project.

    Args:
        event: API Gateway Lambda event (contains authorizer claims)
        project_id: The project being accessed

    Returns:
        (is_authorized, user_id) tuple. is_authorized is True if user owns project.
    """
    # Extract user from Cognito claims
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    claims = authorizer.get("claims", {})
    user_id = claims.get("sub", "")  # Cognito subject (unique user ID)

    if not user_id:
        return False, ""

    # Read project from ledger to verify ownership
    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
        # Assuming ProjectStatus has owner_id field (or read from separate table)
        # Current: project_id doesn't track owner, only customer name
        # WORKAROUND: Check if user is in project's authorized users
        # (implementation depends on your user/project model)

        # For now, assume all authenticated users can access all projects
        # (This needs your project ownership model)
        # TODO: Implement project ownership check

        return True, user_id
    except Exception:
        return False, ""
```

**Issue:** The current data model doesn't track project ownership. Need to either:
- Add owner_id to task ledger
- Create separate project_access table
- Use a project_owners DynamoDB table

#### Step 2: Update All Approval Endpoints

```python
def approve_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Approve a phase.

    POST /projects/{id}/approve
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    # NEW: Verify user owns this project
    is_authorized, user_id = _verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized approval attempt for project=%s", project_id)
        return _response(403, {"error": "Forbidden"})

    # Rest of implementation unchanged
    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    # ... (existing code)
```

#### Step 3: Update Artifact Endpoint

```python
def artifact_content_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Fetch artifact file content from project repository.

    GET /projects/{id}/artifacts?path={file_path}
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    # NEW: Verify user owns this project
    is_authorized, user_id = _verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized artifact access for project=%s", project_id)
        return _response(403, {"error": "Forbidden"})

    # Rest of implementation unchanged
    params = event.get("queryStringParameters") or {}
    # ... (existing code)
```

#### Step 4: Update Interrupt Endpoint

```python
def interrupt_respond_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Submit response to an interrupt.

    POST /projects/{id}/interrupt/{interrupt_id}/respond
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    # NEW: Verify user owns this project
    is_authorized, user_id = _verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized interrupt response for project=%s", project_id)
        return _response(403, {"error": "Forbidden"})

    # Rest of implementation unchanged
    # ... (existing code)
```

#### Step 5: Update Chat Endpoint (When Implemented)

```python
def chat_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Chat with PM during phase review.

    POST /projects/{id}/chat
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    # NEW: Verify user owns this project
    is_authorized, user_id = _verify_project_access(event, project_id)
    if not is_authorized:
        logger.warning("Unauthorized chat for project=%s", project_id)
        return _response(403, {"error": "Forbidden"})

    # Rest of implementation
    # ... (new code)
```

### Testing

```python
# tests/unit/phases/test_api_handlers_auth.py

def test_approve_forbidden_for_different_user():
    """Verify approval fails if user doesn't own project."""
    event = {
        "pathParameters": {"id": "other-user-project"},
        "requestContext": {
            "authorizer": {
                "claims": {"sub": "user123"}
            }
        }
    }
    result = approve_handler(event)
    assert result["statusCode"] == 403
    assert "Forbidden" in result["body"]

def test_approve_succeeds_for_owner():
    """Verify approval succeeds for project owner."""
    # Mock ledger to show user owns project
    # Implement project ownership check
    # Verify approval proceeds
```

---

## FIX #2: Phase Summary Generation Handler (FEATURE CRITICAL)

**Status:** Blocking phase review experience
**Effort:** 1-2 hours
**Files to Modify/Create:** `src/phases/api_handlers.py` (new handler)

### Problem

Phase summaries are never generated. PM has the tool but it's never invoked. After a phase completes, PM review skips summary generation.

### Solution

Create a new Lambda handler that invokes PM to generate phase summaries.

#### Step 1: Create Phase Summary Handler

```python
# File: src/phases/api_handlers.py

def pm_generate_summary_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Invoke PM agent to generate a phase summary document.

    Called by Step Functions after a phase Swarm completes and before
    PM review. The PM generates a comprehensive Phase Summary synthesizing
    work accomplished, key decisions, and deliverables.

    Args:
        event: Contains project_id, phase.
        context: Lambda context (unused).

    Returns:
        Dict with generation results (project_id, phase, summary_path, status).
    """
    from src.agents.pm import create_pm_agent
    from src.agents.base import build_invocation_state

    project_id: str = event["project_id"]
    phase: str = event["phase"]

    logger.info(
        "PM generating phase summary for project=%s, phase=%s",
        project_id,
        phase,
    )

    # Build invocation state
    invocation_state = build_invocation_state(
        project_id=project_id,
        phase=phase.lower(),
    )

    # Create PM agent
    pm = create_pm_agent()

    # Task for PM to generate summary
    summary_task = (
        f"Generate a comprehensive Phase Summary document for the {phase} phase.\n\n"
        f"The summary should:\n"
        f"1. Synthesize all work accomplished during this phase\n"
        f"2. Highlight key technical decisions and their rationale\n"
        f"3. Summarize all major deliverables and their outcomes\n"
        f"4. Note any blockers or risks identified\n"
        f"5. List next steps for the upcoming phase\n\n"
        f"Write in executive-friendly language focused on value delivered.\n"
        f"Use the git_write_phase_summary tool to save to "
        f"docs/phase-summaries/{phase.lower()}.md\n\n"
        f"Respond with 'SUMMARY_COMPLETE: {phase}' when done."
    )

    # Invoke PM agent
    result = pm(summary_task, invocation_state=invocation_state)

    # Parse response to check completion
    response_text = str(result).upper()
    summary_completed = f"SUMMARY_COMPLETE: {phase.upper()}" in response_text

    # Determine summary path
    summary_path = f"docs/phase-summaries/{phase.lower()}.md"

    logger.info(
        "PM summary generation %s for project=%s, phase=%s (path=%s)",
        "COMPLETED" if summary_completed else "ATTEMPTED",
        project_id,
        phase,
        summary_path,
    )

    return {
        "project_id": project_id,
        "phase": phase,
        "summary_path": summary_path,
        "summary_completed": summary_completed,
        "status": "COMPLETED" if summary_completed else "INCOMPLETE",
    }
```

#### Step 2: Register Handler in API Router

```python
# File: src/phases/api_handlers.py in route() function

def route(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route API Gateway events to appropriate handler."""
    # ... existing code ...
    try:
        if method == "POST" and resource == "/projects/{id}/approve":
            return approve_handler(event)
        # ... other endpoints ...
    except Exception:
        logger.exception("Handler error")
```

**Note:** This is a Lambda to be called directly from Step Functions, not via API Gateway. So don't add to route() — register in Step Functions instead.

#### Step 3: Update Step Functions State Machine

```terraform
# File: infra/terraform/step_functions.tf

resource "aws_sfn_state_machine" "orchestrator" {
  definition = jsonencode({
    States = {
      Architecture = {
        Type = "Task"
        Resource = "arn:aws:states:::lambda:invoke.waitForTaskToken"
        # ... phase execution ...
        Next = "ArchitectureGenerateSummary"  # NEW
      }

      # NEW STATE
      ArchitectureGenerateSummary = {
        Type = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = aws_lambda_function.pm_summary.arn  # NEW Lambda
          Payload = {
            "project_id.$" = "$.project_id"
            "phase" = "ARCHITECTURE"
          }
        }
        ResultPath = "$.summary"
        Next = "ArchitecturePMReview"
      }

      ArchitecturePMReview = {
        # ... existing review logic ...
        Next = "ArchitectureApproval"
      }

      # ... rest unchanged ...
    }
  })
}
```

#### Step 4: Test

```python
# tests/unit/phases/test_pm_summary.py

def test_pm_generates_summary():
    """Verify PM generates phase summary."""
    event = {
        "project_id": "test-proj",
        "phase": "ARCHITECTURE",
    }
    result = pm_generate_summary_handler(event, None)
    assert result["status"] == "COMPLETED"
    assert "docs/phase-summaries/architecture.md" in result["summary_path"]

def test_summary_file_created():
    """Verify summary file is actually created in git."""
    # Mock git operations
    # Invoke pm_generate_summary_handler
    # Verify git_write_phase_summary was called
    # Verify file path is correct
```

---

## FIX #3: Chat API Implementation (FEATURE CRITICAL)

**Status:** Blocks interactive review experience
**Effort:** 3-4 hours
**Files to Create/Modify:**
- `src/phases/api_handlers.py` (new chat_handler)
- `src/phases/pm_chat_handler.py` (may already exist, extend it)
- `infra/terraform/step_functions.tf` (no changes needed)
- `dashboard/src/state/queries/useChatQueries.ts` (add React Query hooks)

### Problem

Dashboard can't send messages to PM during review. No backend chat API exists.

### Solution

Create a chat endpoint that invokes PM agent with review context and stores history.

#### Step 1: Create Chat Handler

```python
# File: src/phases/api_handlers.py (or pm_chat_handler.py)

def chat_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Chat with PM during phase review.

    POST /projects/{id}/chat
    Body: {
      "message": "string",
      "phase": "ARCHITECTURE"
    }
    Response: {
      "message_id": "uuid",
      "response": "string (PM's response)",
      "timestamp": "ISO8601",
      "thinking_time_ms": number
    }
    """
    import uuid
    import time

    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    # NEW: Authorization check
    is_authorized, user_id = _verify_project_access(event, project_id)
    if not is_authorized:
        return _response(403, {"error": "Forbidden"})

    body = json.loads(event.get("body", "{}"))
    message: str = body.get("message", "").strip()
    if not message:
        return _response(400, {"error": "message is required"})

    phase: str = body.get("phase", "").upper()
    if phase not in ["DISCOVERY", "ARCHITECTURE", "POC", "PRODUCTION", "HANDOFF"]:
        return _response(400, {"error": "invalid phase"})

    try:
        from src.agents.pm import create_pm_agent
        from src.agents.base import build_invocation_state
        from src.state.chat import store_chat_message, get_chat_history

        # Build invocation state
        invocation_state = build_invocation_state(
            project_id=project_id,
            phase=phase.lower(),
        )

        # Get recent chat history for context (last 5 exchanges)
        chat_history = get_chat_history(TASK_LEDGER_TABLE, project_id, phase, limit=5)
        history_context = "\n".join(
            [f"{'USER' if m.is_user else 'PM'}: {m.content}" for m in chat_history]
        )

        # Build PM prompt with context
        pm_prompt = (
            f"You are reviewing the {phase} phase deliverables with the customer.\n"
            f"Answer their question about the phase, artifacts, or next steps.\n\n"
            f"Recent conversation:\n{history_context}\n\n"
            f"Customer question: {message}\n\n"
            f"Provide a concise, helpful response."
        )

        # Invoke PM agent
        pm = create_pm_agent()
        start_time = time.monotonic()
        result = pm(pm_prompt, invocation_state=invocation_state)
        thinking_time_ms = int((time.monotonic() - start_time) * 1000)

        response_text = str(result)

        # Store chat messages in DynamoDB
        message_id = str(uuid.uuid4())
        store_chat_message(
            TASK_LEDGER_TABLE,
            project_id,
            phase,
            message_id,
            content=message,
            is_user=True,
            timestamp=time.time(),
        )
        store_chat_message(
            TASK_LEDGER_TABLE,
            project_id,
            phase,
            str(uuid.uuid4()),
            content=response_text,
            is_user=False,
            timestamp=time.time(),
        )

        logger.info("Chat message processed for project=%s, phase=%s", project_id, phase)

        return _response(
            200,
            {
                "message_id": message_id,
                "response": response_text,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "thinking_time_ms": thinking_time_ms,
            },
        )

    except Exception as exc:
        logger.exception("Chat handler error: %s", exc)
        return _response(500, {"error": f"Chat failed: {exc}"})
```

#### Step 2: Register Chat Handler in Router

```python
# File: src/phases/api_handlers.py

def route(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Route API Gateway events."""
    method = event.get("httpMethod", "")
    resource = event.get("resource", "")

    try:
        # ... existing endpoints ...
        if method == "POST" and resource == "/projects/{id}/chat":
            return chat_handler(event)
        # ... rest ...
    except Exception:
        logger.exception("Handler error")
```

#### Step 3: Create Chat Storage Functions

```python
# File: src/state/chat.py (new file)

"""Chat message storage and retrieval."""

import time
from dataclasses import dataclass

import boto3

from src.config import AWS_REGION


@dataclass
class ChatMessage:
    """A chat message during phase review."""

    message_id: str
    content: str
    is_user: bool
    timestamp: float
    phase: str


def store_chat_message(
    table_name: str,
    project_id: str,
    phase: str,
    message_id: str,
    content: str,
    is_user: bool,
    timestamp: float,
) -> None:
    """Store a chat message in DynamoDB."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(table_name)

    # Store in a partition key like "chat#{project}#{phase}"
    table.put_item(
        Item={
            "pk": f"chat#{project_id}#{phase}",
            "sk": f"msg#{int(timestamp)}#{message_id}",
            "content": content,
            "is_user": is_user,
            "timestamp": int(timestamp),
            "ttl": int(timestamp) + 30 * 24 * 60 * 60,  # 30 days
        }
    )


def get_chat_history(
    table_name: str,
    project_id: str,
    phase: str,
    limit: int = 10,
) -> list[ChatMessage]:
    """Retrieve recent chat messages."""
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(table_name)

    response = table.query(
        KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq(
            f"chat#{project_id}#{phase}"
        ),
        ScanIndexForward=False,  # Most recent first
        Limit=limit,
    )

    messages = []
    for item in sorted(response["Items"], key=lambda x: x["sk"]):
        messages.append(
            ChatMessage(
                message_id=item["sk"].split("#")[-1],
                content=item["content"],
                is_user=item["is_user"],
                timestamp=item["timestamp"],
                phase=phase,
            )
        )

    return messages
```

#### Step 4: Add Dashboard Chat Query Hook

```typescript
// File: dashboard/src/state/queries/useChatQueries.ts (new or extend)

import { useMutation } from "@tanstack/react-query";
import { post } from "@/lib/api";

export interface ChatMessage {
  message_id: string;
  response: string;
  timestamp: string;
  thinking_time_ms: number;
}

export function useSendChatMessage(projectId: string, phase: string) {
  return useMutation({
    mutationFn: async (message: string) => {
      if (isDemoMode(projectId)) {
        // Demo implementation (existing)
        return generateDemoChatResponse(message);
      }
      return post<ChatMessage>(`/projects/${projectId}/chat`, {
        message,
        phase,
      });
    },
    onSuccess: () => {
      // Invalidate chat history query
      void queryClient.invalidateQueries({ queryKey: ["chat", projectId, phase] });
    },
  });
}

export function useChatHistory(projectId: string, phase: string) {
  return useQuery({
    queryKey: ["chat", projectId, phase],
    queryFn: () => {
      if (isDemoMode(projectId)) {
        // Return demo chat history
        return [];
      }
      return get<ChatMessage[]>(`/projects/${projectId}/chat?phase=${phase}`);
    },
  });
}
```

#### Step 5: Test

```python
# tests/unit/phases/test_chat.py

def test_chat_requires_message():
    """Verify chat fails without message."""
    event = {
        "pathParameters": {"id": "proj1"},
        "body": json.dumps({"phase": "ARCHITECTURE"}),
    }
    result = chat_handler(event)
    assert result["statusCode"] == 400

def test_chat_stores_message():
    """Verify chat message is stored."""
    # Mock DynamoDB
    # Call chat_handler
    # Verify store_chat_message was called
    pass

def test_chat_invokes_pm():
    """Verify PM is invoked with review context."""
    # Mock PM agent
    # Call chat_handler
    # Verify PM was invoked
    pass
```

---

## FIX #4: Opening/Closing Messages API (FEATURE CRITICAL)

**Status:** Blocks review message display
**Effort:** 1-2 hours
**Files to Modify:**
- `src/phases/api_handlers.py` (add review_context handler)
- `dashboard/src/state/queries/useProjectQueries.ts` (extend status query)

### Problem

Dashboard hardcodes opening/closing messages from demoTimeline. In real mode, these messages have no source.

### Solution

Add review context to project status API that includes opening/closing messages.

#### Step 1: Extend Project Status Model

```python
# File: src/state/models.py (add to ProjectStatusSummary)

from dataclasses import dataclass, field


@dataclass
class ReviewContext:
    """Context for phase review."""

    opening_message: str
    closing_message: str
    summary_path: str
    artifacts: list[dict[str, str]]  # [{path, name}, ...]


@dataclass
class ProjectStatusSummary:
    """Summary of project status (returned by status API)."""

    project_id: str
    project_name: str
    current_phase: Phase
    phase_status: str
    deliverables: dict[str, list]
    # ... existing fields ...
    review_context: ReviewContext | None = None  # NEW
```

#### Step 2: Create Review Context Builder

```python
# File: src/phases/api_handlers.py

def _build_review_context(project_id: str, phase: str) -> dict[str, Any] | None:
    """Build review context with opening/closing messages and artifacts.

    Args:
        project_id: The project ID
        phase: The current phase

    Returns:
        Review context dict or None if not in review state
    """
    ledger = read_ledger(TASK_LEDGER_TABLE, project_id)
    if ledger.phase_status != "AWAITING_APPROVAL":
        return None

    # Get phase-specific messages (hardcoded or from config)
    messages = {
        "DISCOVERY": {
            "opening": "Welcome to the **Discovery** phase review! 🎯\n\n"
                      "We've gathered stakeholder requirements and identified key assumptions.",
            "closing": "Thank you for approving the Discovery phase!",
        },
        "ARCHITECTURE": {
            "opening": "Welcome to the **Architecture** phase review! 🎉\n\n"
                      "Our team completed a comprehensive analysis of your requirements.",
            "closing": "Thank you for approving the Architecture phase!",
        },
        "POC": {
            "opening": "Welcome to the **POC** phase review! ✅\n\n"
                      "We've validated the architecture with working code.",
            "closing": "Thank you for approving the POC phase!",
        },
        "PRODUCTION": {
            "opening": "Welcome to the **Production** phase review! ✨\n\n"
                      "Your system is now live and running strong.",
            "closing": "Thank you for approving the Production phase!",
        },
        "HANDOFF": {
            "opening": "Welcome to the **Handoff** phase review! 🎓\n\n"
                      "We've completed comprehensive knowledge transfer.",
            "closing": "Thank you for completing the Handoff phase!",
        },
    }

    phase_messages = messages.get(phase, {
        "opening": f"Welcome to the {phase} phase review.",
        "closing": f"Thank you for approving the {phase} phase."
    })

    # Build artifact list
    summary_path = f"docs/phase-summaries/{phase.lower()}.md"
    artifacts = [
        {"path": summary_path, "name": f"{phase} Phase Summary"},
        # Add phase-specific artifacts
    ]

    # Phase-specific artifacts
    if phase == "ARCHITECTURE":
        artifacts.extend([
            {"path": "docs/architecture.md", "name": "System Architecture"},
            {"path": "docs/data-model.md", "name": "Data Model"},
            {"path": "docs/security-design.md", "name": "Security Design"},
        ])
    elif phase == "POC":
        artifacts.extend([
            {"path": "docs/poc-results.md", "name": "POC Results"},
            {"path": "tests/", "name": "Test Suite"},
        ])
    elif phase == "PRODUCTION":
        artifacts.extend([
            {"path": "docs/data-migration-report.md", "name": "Data Migration Report"},
            {"path": "docs/deployment-guide.md", "name": "Deployment Guide"},
        ])
    elif phase == "HANDOFF":
        artifacts.extend([
            {"path": "docs/operations-runbook.md", "name": "Operations Runbook"},
            {"path": "docs/api-documentation.md", "name": "API Documentation"},
            {"path": "docs/training-materials.md", "name": "Training Materials"},
        ])

    return {
        "opening_message": phase_messages["opening"],
        "closing_message": phase_messages["closing"],
        "summary_path": summary_path,
        "artifacts": artifacts,
    }
```

#### Step 3: Update Project Status Handler

```python
# File: src/phases/api_handlers.py

def project_status_handler(event: dict[str, Any]) -> dict[str, Any]:
    """Get project status.

    GET /projects/{id}/status
    """
    project_id = event.get("pathParameters", {}).get("id", "")
    if not project_id:
        return _response(400, {"error": "project_id is required"})

    try:
        ledger = read_ledger(TASK_LEDGER_TABLE, project_id)

        status = {
            "project_id": project_id,
            "project_name": ledger.customer_name,
            "current_phase": ledger.current_phase.value,
            "phase_status": ledger.phase_status.value,
            "deliverables": {
                phase: [d.model_dump() for d in delivs]
                for phase, delivs in ledger.deliverables.items()
            },
            "facts": [f.model_dump() for f in ledger.facts],
            "assumptions": [a.model_dump() for a in ledger.assumptions],
            "decisions": [d.model_dump() for d in ledger.decisions],
            "blockers": [b.model_dump() for b in ledger.blockers],
            "created_at": ledger.created_at.isoformat() + "Z",
            "updated_at": ledger.updated_at.isoformat() + "Z",
            # NEW: Add review context if in review state
            "review_context": _build_review_context(project_id, ledger.current_phase.value),
        }

        return _response(200, status)
    except Exception as exc:
        logger.exception("project_status_handler error: %s", exc)
        return _response(500, {"error": f"Failed to get project status: {exc}"})
```

#### Step 4: Update Dashboard to Use Backend Messages

```typescript
// File: dashboard/src/pages/DashboardPage.tsx

export function DashboardPage() {
  // ... existing code ...
  const { data: project } = useProjectStatus(projectId);

  const onReviewClick = () => {
    if (!project?.review_context) {
      console.warn("No review context available");
      return;
    }

    const { opening_message, closing_message, summary_path } = project.review_context;

    usePhaseReviewStore.getState().beginReview(
      project.current_phase,
      opening_message,  // From backend now
      closing_message,   // From backend now
      summary_path       // From backend now
    );
  };

  // Rest unchanged
}
```

#### Step 5: Test

```python
# tests/unit/phases/test_review_context.py

def test_review_context_when_awaiting_approval():
    """Verify review context is returned when phase is awaiting approval."""
    # Mock ledger with AWAITING_APPROVAL status
    # Call project_status_handler
    # Verify review_context is in response
    pass

def test_review_context_has_opening_message():
    """Verify opening message is included."""
    # Call project_status_handler
    # Verify review_context.opening_message is populated
    pass

def test_review_context_none_when_not_awaiting():
    """Verify review context is None when not awaiting approval."""
    # Mock ledger with IN_PROGRESS status
    # Call project_status_handler
    # Verify review_context is None
    pass
```

---

## Implementation Checklist

### Authorization (Fix #1)
- [ ] Add `_verify_project_access()` function
- [ ] Update `approve_handler()` with auth check
- [ ] Update `revise_handler()` with auth check
- [ ] Update `artifact_content_handler()` with auth check
- [ ] Update `interrupt_respond_handler()` with auth check
- [ ] Create/update unit tests
- [ ] Test with Cognito claims
- [ ] Implement project ownership model (if needed)

### Phase Summary (Fix #2)
- [ ] Create `pm_generate_summary_handler()` Lambda
- [ ] Update Step Functions state machine
- [ ] Register new Lambda in Terraform
- [ ] Test summary file creation
- [ ] Test phase summary tool invocation
- [ ] Add error handling for PM failures

### Chat API (Fix #3)
- [ ] Create `chat_handler()` in api_handlers.py
- [ ] Create chat storage module (`src/state/chat.py`)
- [ ] Add authorization check to chat handler
- [ ] Register chat endpoint in router
- [ ] Create React Query hooks for dashboard
- [ ] Update DynamoDB schema (if needed)
- [ ] Test end-to-end chat flow
- [ ] Test chat history retrieval

### Review Context (Fix #4)
- [ ] Add `ReviewContext` to models
- [ ] Create `_build_review_context()` builder
- [ ] Update `project_status_handler()` with review context
- [ ] Update dashboard to use review context from backend
- [ ] Test review context API
- [ ] Hardcode phase messages (first version)
- [ ] Later: Load messages from database

---

## Rollout Strategy

### Phase 1: Deploy Fixes in Order
1. Authorization (security critical)
2. Phase Summary Generation
3. Chat API
4. Review Context

### Phase 2: Testing
- Integration tests with all fixes
- Load testing
- Real project test run

### Phase 3: Monitor
- Error rate tracking
- Performance metrics
- User feedback

### Estimated Total Time
- **Planning/Design:** 2 hours
- **Authorization:** 2-3 hours
- **Phase Summary:** 1-2 hours
- **Chat API:** 3-4 hours
- **Review Context:** 1-2 hours
- **Integration Testing:** 2-3 hours
- **Documentation:** 1 hour

**Total: 13-18 hours**

---

## Reference: Current Data Model

### DynamoDB Task Ledger Schema

```
pk: {project_id}
sk: "metadata"

{
  project_id: string
  customer_name: string
  current_phase: "DISCOVERY" | "ARCHITECTURE" | "POC" | "PRODUCTION" | "HANDOFF"
  phase_status: "IN_PROGRESS" | "AWAITING_APPROVAL" | "COMPLETED"
  created_at: ISO8601
  updated_at: ISO8601
  deliverables: {
    ARCHITECTURE: [
      {
        name: string
        path: string
        description: string
        approved: boolean
      }
    ]
    ...
  }
  facts: [{description, source, timestamp}]
  assumptions: [{description, confidence, timestamp}]
  decisions: [{description, rationale, made_by, timestamp, adr_path}]
  blockers: [{description, severity, owner, timestamp}]
}
```

### New Partitions Needed

**For Chat History:**
```
pk: "chat#{project_id}#{phase}"
sk: "msg#{timestamp}#{message_id}"

{
  content: string
  is_user: boolean
  timestamp: number (Unix timestamp)
  ttl: number (Unix timestamp + 30 days)
}
```

**For Project Ownership (if needed):**
```
pk: "project#{project_id}"
sk: "owner"

{
  owner_id: string (Cognito subject)
  created_at: ISO8601
}
```
