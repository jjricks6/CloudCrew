"""Utilities for phase review screens.

Builds context for opening/closing messages during phase review.

This module is in phases/ — the ONLY package allowed to import from agents/.
"""

from typing import Any


def build_review_context(phase: str) -> dict[str, Any]:
    """Build review context with opening/closing messages for a phase.

    Args:
        phase: The current phase (e.g., "ARCHITECTURE", "POC")

    Returns:
        Review context dict with opening, closing, and summary path.
    """
    # Phase-specific messages for review screens
    messages = {
        "DISCOVERY": {
            "opening": (
                "Welcome to the **Discovery** phase review! 🎯\n\n"
                "Our team has gathered stakeholder requirements and identified "
                "key assumptions about your project scope, scale, and priorities."
            ),
            "closing": "Thank you for approving the Discovery phase! We're ready to proceed to Architecture.",
        },
        "ARCHITECTURE": {
            "opening": (
                "Welcome to the **Architecture** phase review! 🎉\n\n"
                "We've designed a scalable, production-ready system that aligns with your "
                "requirements and technical constraints. All key technical decisions are documented."
            ),
            "closing": "Thank you for approving the Architecture phase! We'll now build and validate the design.",
        },
        "POC": {
            "opening": (
                "Welcome to the **Proof of Concept** phase review! ✅\n\n"
                "We've built working code validating the architecture. The system demonstrates "
                "core functionality with performance and security meeting requirements."
            ),
            "closing": "Thank you for approving the POC phase! We'll now move to production implementation.",
        },
        "PRODUCTION": {
            "opening": (
                "Welcome to the **Production** phase review! ✨\n\n"
                "Your system is now fully built, tested, and deployed. All deliverables "
                "meet acceptance criteria with zero critical findings."
            ),
            "closing": "Thank you for approving the Production phase! We'll transition to handoff and support.",
        },
        "HANDOFF": {
            "opening": (
                "Welcome to the **Handoff** phase review! 🎓\n\n"
                "We've completed comprehensive knowledge transfer and your team is ready to "
                "operate the system independently with confidence."
            ),
            "closing": "Thank you for completing the Handoff phase! The engagement is now complete.",
        },
    }

    phase_messages = messages.get(
        phase,
        {"opening": f"Welcome to the {phase} phase review.", "closing": f"Thank you for approving the {phase} phase."},
    )

    summary_path = f"docs/phase-summaries/{phase.lower()}.md"

    return {
        "opening_message": phase_messages["opening"],
        "closing_message": phase_messages["closing"],
        "summary_path": summary_path,
    }
