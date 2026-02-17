"""Architecture boundary tests.

These tests enforce module boundaries and structural rules. They run as part of
the normal test suite and CI pipeline. They exist to prevent architectural drift
when AI agents generate code.

NEVER weaken these tests to make code pass. Fix the code instead.
If you need a new exception, add it with a comment explaining WHY.
"""

import ast
from pathlib import Path
from typing import ClassVar

import pytest

SRC_DIR = Path(__file__).parent.parent.parent / "src"

# --- Import boundary rules ---
# Format: {module: [list of modules it MUST NOT import from]}
FORBIDDEN_IMPORTS: dict[str, list[str]] = {
    "tools": ["agents", "phases"],
    "hooks": ["agents", "tools", "phases"],
    "state": ["agents", "tools", "hooks", "phases"],
    "templates": ["agents", "tools", "hooks", "state", "phases", "config"],
    "config": ["agents", "tools", "hooks", "state", "phases", "templates"],
}

MAX_FILE_LINES = 500


def _get_python_files(directory: Path) -> list[Path]:
    """Recursively find all .py files in a directory."""
    if not directory.exists():
        return []
    return sorted(directory.rglob("*.py"))


def _get_imports(filepath: Path) -> list[str]:
    """Extract all import module names from a Python file."""
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return []

    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)
    return imports


def _resolve_src_module(import_path: str) -> str | None:
    """Extract the src submodule name from an import path.

    e.g., 'src.agents.pm' -> 'agents'
          'cloudcrew.tools.git_tools' -> 'tools'
    """
    parts = import_path.split(".")
    # Handle 'src.X.Y' or 'cloudcrew.X.Y' patterns
    for prefix in ("src", "cloudcrew"):
        if prefix in parts:
            idx = parts.index(prefix)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    # Handle direct 'X.Y' where X is a known module
    known_modules = {"agents", "tools", "hooks", "state", "templates", "phases", "config"}
    if parts[0] in known_modules:
        return parts[0]
    return None


# --- Tests ---


@pytest.mark.architecture
class TestImportBoundaries:
    """Verify that modules respect import boundaries."""

    @pytest.mark.parametrize(
        "module_name,forbidden",
        list(FORBIDDEN_IMPORTS.items()),
        ids=list(FORBIDDEN_IMPORTS.keys()),
    )
    def test_forbidden_imports(self, module_name: str, forbidden: list[str]) -> None:
        """Module must not import from forbidden modules."""
        module_dir = SRC_DIR / module_name
        if not module_dir.exists():
            pytest.skip(f"Module {module_name}/ does not exist yet")

        violations: list[str] = []
        for filepath in _get_python_files(module_dir):
            imports = _get_imports(filepath)
            for imp in imports:
                src_module = _resolve_src_module(imp)
                if src_module in forbidden:
                    rel_path = filepath.relative_to(SRC_DIR.parent)
                    violations.append(f"  {rel_path}: imports '{imp}' (forbidden: {module_name} -> {src_module})")

        if violations:
            msg = f"\nImport boundary violations in {module_name}/:\n" + "\n".join(violations)
            pytest.fail(msg)


@pytest.mark.architecture
class TestNoCircularImports:
    """Verify no circular import chains exist."""

    def test_no_circular_imports(self) -> None:
        """Check for circular imports between src modules."""
        if not SRC_DIR.exists():
            pytest.skip("src/ does not exist yet")

        # Build dependency graph: module -> set of modules it imports
        graph: dict[str, set[str]] = {}
        known_modules = {"agents", "tools", "hooks", "state", "templates", "phases", "config"}

        for module_name in known_modules:
            module_dir = SRC_DIR / module_name
            if not module_dir.exists():
                continue

            deps: set[str] = set()
            for filepath in _get_python_files(module_dir):
                for imp in _get_imports(filepath):
                    src_module = _resolve_src_module(imp)
                    if src_module and src_module != module_name and src_module in known_modules:
                        deps.add(src_module)
            graph[module_name] = deps

        # Detect cycles using DFS
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str], visited: set[str]) -> None:
            if node in path:
                cycle_start = path.index(node)
                cycles.append([*path[cycle_start:], node])
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for dep in graph.get(node, set()):
                dfs(dep, path, visited)
            path.pop()

        visited: set[str] = set()
        for module in graph:
            dfs(module, [], visited)

        if cycles:
            cycle_strs = [" -> ".join(c) for c in cycles]
            pytest.fail("\nCircular import chains detected:\n" + "\n".join(f"  {c}" for c in cycle_strs))


@pytest.mark.architecture
class TestFileSizeLimits:
    """Verify no Python file exceeds the line limit."""

    def test_max_file_lines(self) -> None:
        """No Python file in src/ should exceed MAX_FILE_LINES."""
        if not SRC_DIR.exists():
            pytest.skip("src/ does not exist yet")

        violations: list[str] = []
        for filepath in _get_python_files(SRC_DIR):
            line_count = len(filepath.read_text().splitlines())
            if line_count > MAX_FILE_LINES:
                rel_path = filepath.relative_to(SRC_DIR.parent)
                violations.append(f"  {rel_path}: {line_count} lines (max: {MAX_FILE_LINES})")

        if violations:
            pytest.fail(f"\nFiles exceeding {MAX_FILE_LINES} line limit:\n" + "\n".join(violations))


@pytest.mark.architecture
class TestToolConventions:
    """Verify tool implementations follow conventions."""

    def test_tools_have_docstrings(self) -> None:
        """Every function in tools/ must have a docstring."""
        tools_dir = SRC_DIR / "tools"
        if not tools_dir.exists():
            pytest.skip("src/tools/ does not exist yet")

        violations: list[str] = []
        for filepath in _get_python_files(tools_dir):
            if filepath.name == "__init__.py":
                continue
            try:
                tree = ast.parse(filepath.read_text())
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_") and not ast.get_docstring(node):
                    rel_path = filepath.relative_to(SRC_DIR.parent)
                    violations.append(f"  {rel_path}:{node.lineno} — function '{node.name}' missing docstring")

        if violations:
            pytest.fail("\nTools without docstrings:\n" + "\n".join(violations))


@pytest.mark.architecture
class TestAgentConventions:
    """Verify agent definitions follow conventions."""

    def test_agents_have_system_prompt(self) -> None:
        """Every agent module should define a system prompt constant."""
        agents_dir = SRC_DIR / "agents"
        if not agents_dir.exists():
            pytest.skip("src/agents/ does not exist yet")

        violations: list[str] = []
        for filepath in _get_python_files(agents_dir):
            if filepath.name in ("__init__.py", "base.py"):
                continue

            content = filepath.read_text()
            # Check for a SYSTEM_PROMPT constant (any variation)
            if "SYSTEM_PROMPT" not in content and "system_prompt" not in content:
                rel_path = filepath.relative_to(SRC_DIR.parent)
                violations.append(f"  {rel_path}: no SYSTEM_PROMPT constant found")

        if violations:
            pytest.fail("\nAgent files missing system prompt:\n" + "\n".join(violations))


@pytest.mark.architecture
class TestNoNewTopLevelModules:
    """Verify no unauthorized top-level modules in src/."""

    ALLOWED_MODULES: ClassVar[set[str]] = {"agents", "tools", "hooks", "templates", "state", "phases", "__pycache__"}
    ALLOWED_FILES: ClassVar[set[str]] = {"__init__.py", "config.py"}

    def test_no_unauthorized_modules(self) -> None:
        """src/ should only contain approved top-level directories and files."""
        if not SRC_DIR.exists():
            pytest.skip("src/ does not exist yet")

        violations: list[str] = []
        for entry in SRC_DIR.iterdir():
            if entry.is_dir() and entry.name not in self.ALLOWED_MODULES:
                violations.append(f"  Unauthorized directory: src/{entry.name}/")
            elif entry.is_file() and entry.name not in self.ALLOWED_FILES:
                violations.append(f"  Unauthorized file: src/{entry.name}")

        if violations:
            msg = (
                "\nUnauthorized entries in src/:\n"
                + "\n".join(violations)
                + "\n\nIf this is intentional, add it to ALLOWED_MODULES/ALLOWED_FILES in test_boundaries.py"
                + " with a comment explaining why."
            )
            pytest.fail(msg)
