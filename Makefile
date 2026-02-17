.PHONY: check test lint format typecheck security arch-test install install-hooks clean

# Run ALL quality checks — the single command agents must run after changes
check: format lint typecheck test

# Install dependencies
install:
	pip install -e ".[dev]"

# Install pre-commit hooks
install-hooks:
	pre-commit install

# Format code (auto-fix)
format:
	ruff format src/ tests/

# Lint code
lint:
	ruff check src/ tests/

# Lint with auto-fix
lint-fix:
	ruff check --fix src/ tests/

# Type check (strict)
typecheck:
	mypy src/

# Run tests with coverage
test:
	pytest tests/ -m "not integration and not e2e" --cov=src --cov-report=term-missing

# Run only architecture boundary tests
arch-test:
	pytest tests/architecture/ -v

# Run integration tests (requires AWS credentials)
test-integration:
	pytest tests/ -m integration --cov=src --cov-report=term-missing

# Security scan
security:
	bandit -r src/ -c pyproject.toml

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage
