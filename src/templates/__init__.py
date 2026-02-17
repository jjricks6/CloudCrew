"""Artifact templates for CloudCrew deliverables.

Pure data module — imports NOTHING from src/. Provides template loading only.
"""

from pathlib import Path

_TEMPLATE_DIR = Path(__file__).parent


def load_template(name: str) -> str:
    """Load a template file by name.

    Args:
        name: Filename of the template (e.g., "adr.md").

    Returns:
        Template content as a string.

    Raises:
        FileNotFoundError: If the template does not exist.
    """
    path = _TEMPLATE_DIR / name
    if not path.exists():
        msg = f"Template not found: {name}"
        raise FileNotFoundError(msg)
    return path.read_text()
