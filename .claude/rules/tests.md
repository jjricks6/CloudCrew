---
paths:
  - "tests/**"
---

# Testing Rules

- Mirror the `src/` structure: `tests/unit/tools/test_git_tools.py` tests `src/tools/git_tools.py`
- Use pytest markers on EVERY test: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`
- Architecture tests go in `tests/architecture/` — these enforce module boundaries and are sacred

## Unit tests (`tests/unit/`)
- Mock ALL external services (Bedrock, DynamoDB, S3, Git)
- Test one function/method per test
- Use descriptive names: `test_parse_sow_extracts_objectives_from_pdf`
- No network calls. No file I/O to real paths. No AWS calls.

## Integration tests (`tests/integration/`)
- Test real AWS calls with small payloads
- Use `@pytest.mark.integration` so they can be skipped in CI without credentials
- Clean up any resources created during the test

## Architecture tests (`tests/architecture/`)
- NEVER weaken architecture tests to make code pass. Fix the code instead.
- If you need a new import boundary exception, document WHY in the test file.

## Fixtures
- Shared fixtures go in `tests/conftest.py`
- Use `@pytest.fixture` for setup/teardown, not setUp/tearDown methods
- Use `tmp_path` for any file I/O in tests
