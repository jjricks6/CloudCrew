"""Tests for src/config.py."""

import os
from unittest.mock import patch

import pytest


@pytest.mark.unit
class TestConfigDefaults:
    """Verify configuration defaults when env vars are not set."""

    def test_model_id_opus_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            # Re-import to pick up clean environment
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.MODEL_ID_OPUS == "us.anthropic.claude-opus-4-6-v1"

    def test_model_id_sonnet_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.MODEL_ID_SONNET == "us.anthropic.claude-sonnet-4-20250514-v1:0"

    def test_task_ledger_table_default(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.TASK_LEDGER_TABLE == "cloudcrew-projects"

    def test_empty_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.KNOWLEDGE_BASE_ID == ""
            assert src.config.PROJECT_REPO_PATH == ""
            assert src.config.PATTERNS_BUCKET == ""

    def test_timeout_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.NODE_TIMEOUT == 600.0
            assert src.config.EXECUTION_TIMEOUT_DISCOVERY == 1800.0
            assert src.config.EXECUTION_TIMEOUT_ARCHITECTURE == 2400.0

    def test_retry_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.PHASE_MAX_RETRIES == 2
            assert src.config.PHASE_RETRY_DELAY == 5.0

    def test_bedrock_client_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.BEDROCK_READ_TIMEOUT == 300
            assert src.config.BEDROCK_MAX_RETRIES == 3


@pytest.mark.unit
class TestConfigOverrides:
    """Verify env var overrides work."""

    def test_env_var_override(self) -> None:
        with patch.dict(os.environ, {"MODEL_ID_OPUS": "custom-model-id"}):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.MODEL_ID_OPUS == "custom-model-id"

    def test_project_repo_path_override(self) -> None:
        with patch.dict(os.environ, {"PROJECT_REPO_PATH": "/tmp/test-repo"}):
            import importlib

            import src.config

            importlib.reload(src.config)
            assert src.config.PROJECT_REPO_PATH == "/tmp/test-repo"
