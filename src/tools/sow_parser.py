"""SOW (Statement of Work) parser tool.

Extracts structured requirements from SOW documents using an explicit
Bedrock Converse call. This module imports from config — NEVER from agents/.
"""

import json
import logging

import boto3
from strands import tool
from strands.types.tools import ToolContext

from src.config import AWS_REGION, MODEL_ID_OPUS
from src.state.models import ParsedSOW

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """You are a requirements extraction specialist. Analyze the following
Statement of Work (SOW) document and extract structured requirements.

Return ONLY a valid JSON object with the following keys:
- "objectives": list of project objectives (strings)
- "requirements": list of functional and non-functional requirements (strings)
- "constraints": list of constraints, limitations, or boundaries (strings)
- "deliverables": list of expected deliverables (strings)
- "acceptance_criteria": list of acceptance criteria (strings)
- "timeline": summary of the timeline or milestones (string)

If a section has no content in the SOW, return an empty list or empty string.
Do not add any text outside the JSON object.

SOW Document:
---
{document_content}
---

JSON Output:"""


def _build_extraction_prompt(document_content: str) -> str:
    """Build the extraction prompt with the SOW content inserted.

    Args:
        document_content: The raw SOW text.

    Returns:
        The complete prompt string.
    """
    return EXTRACTION_PROMPT.format(document_content=document_content)


def _extract_json_from_response(response_text: str) -> dict[str, object]:
    """Extract and parse JSON from the model response.

    Handles cases where the model wraps JSON in markdown code blocks.

    Args:
        response_text: The raw model response text.

    Returns:
        Parsed JSON dict.

    Raises:
        json.JSONDecodeError: If no valid JSON can be extracted.
    """
    text = response_text.strip()
    # Strip markdown code block wrappers if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (``` markers)
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    result: dict[str, object] = json.loads(text)
    return result


@tool(context=True)
def parse_sow(document_content: str, tool_context: ToolContext) -> str:
    """Parse a Statement of Work and extract structured requirements.

    Makes an explicit Bedrock Converse call to extract structured data
    from the SOW document.

    Args:
        document_content: The raw SOW text content.
        tool_context: Strands tool context (injected by framework).

    Returns:
        JSON string with objectives, requirements, constraints,
        deliverables, acceptance_criteria, and timeline.
    """
    if not document_content or not document_content.strip():
        return "Error: Empty SOW document content."

    try:
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        response = client.converse(
            modelId=MODEL_ID_OPUS,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"text": _build_extraction_prompt(document_content)},
                    ],
                },
            ],
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

        # Parse and validate
        parsed_data = _extract_json_from_response(response_text)
        validated = ParsedSOW.model_validate(parsed_data)
        return validated.model_dump_json(indent=2)

    except json.JSONDecodeError as e:
        logger.exception("Failed to parse JSON from SOW extraction")
        return f"Error: Model returned invalid JSON: {e}"
    except Exception as e:
        logger.exception("SOW parsing failed")
        return f"Error parsing SOW: {e}"
