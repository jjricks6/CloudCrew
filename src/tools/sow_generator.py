"""SOW (Statement of Work) generation tool.

Generates comprehensive Statements of Work from customer requirements using
Bedrock. This module imports from config — NEVER from agents/.
"""

import logging

import boto3
from botocore.config import Config
from strands import tool
from strands.types.tools import ToolContext

from src.config import AWS_REGION, MODEL_ID_SONNET

logger = logging.getLogger(__name__)

GENERATION_PROMPT = """You are a professional services Project Manager generating a comprehensive Statement of Work.

Customer's Initial Requirements:
{customer_requirements}

Project Name: {project_name}

Generate a detailed, professional Statement of Work with these sections:

# Statement of Work: {project_name}

## 1. Executive Summary
A brief overview of the project, its strategic value, and what will be delivered.

## 2. Objectives
Clear, measurable objectives the project will achieve. List 3-5 primary objectives.

## 3. Scope

### In Scope
What IS included in this project.

### Out of Scope
What is explicitly NOT included (help prevent scope creep).

## 4. Deliverables
Concrete deliverables organized by phase. Include:
- Architecture documentation and diagrams
- Proof of concept implementation
- Production-ready code and infrastructure
- Operational documentation

## 5. Acceptance Criteria
How the customer will validate that each deliverable meets requirements.

## 6. Timeline
Estimated duration for each phase:
- Discovery: 1-2 weeks
- Architecture: 1-2 weeks
- POC: 2-3 weeks
- Production: 3-4 weeks
- Handoff: 1 week

Total estimated timeline and key milestones.

## 7. Constraints & Assumptions
- Technical constraints (compliance, security, integration requirements)
- Budget or resource limitations
- Any assumptions about the customer's environment
- Team structure and availability

## 8. Success Metrics
Measurable criteria for project success:
- Performance benchmarks
- Uptime/reliability requirements
- Cost metrics
- User adoption or satisfaction metrics

---

Write professionally and specifically. Ensure all customer requirements are captured.
The SOW should be suitable for customer review and approval."""


def _build_generation_prompt(customer_requirements: str, project_name: str) -> str:
    """Build the generation prompt with customer requirements inserted.

    Args:
        customer_requirements: The customer's brief project description.
        project_name: The name of the project.

    Returns:
        The complete prompt string.
    """
    return GENERATION_PROMPT.format(
        customer_requirements=customer_requirements,
        project_name=project_name,
    )


@tool(context=True)
def generate_sow(
    customer_requirements: str,
    project_name: str,
    tool_context: ToolContext,
) -> str:
    """Generate a comprehensive Statement of Work from customer requirements.

    Uses Bedrock Converse with Claude Sonnet to transform customer's brief
    project description into a structured, professional SOW document.

    Args:
        customer_requirements: The customer's initial project description or requirements.
        project_name: The name of the project.
        tool_context: Strands tool context (injected by framework).

    Returns:
        The generated SOW markdown content as a string.
        Returns error string if generation fails.
    """
    if not customer_requirements or not customer_requirements.strip():
        return "Error: Empty customer requirements."

    if not project_name or not project_name.strip():
        return "Error: Empty project name."

    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            config=Config(read_timeout=300),
        )
        response = client.converse(
            modelId=MODEL_ID_SONNET,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": _build_generation_prompt(customer_requirements, project_name)},
                    ],
                },
            ],
            inferenceConfig={
                "maxTokens": 4000,
                "temperature": 0.5,
            },
        )

        # Extract text from Converse response
        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])
        response_text = ""
        for block in content_blocks:
            if "text" in block:
                response_text += block["text"]

        if not response_text:
            return "Error: No text in model response."

        logger.info("Generated SOW: %d characters for project %s", len(response_text), project_name)
        return response_text

    except Exception as e:
        logger.exception("SOW generation failed")
        return f"Error generating SOW: {e}"
