"""Configuration constants loaded from environment variables.

This module is the single source of truth for all configuration values.
It imports NOTHING from src/ — only stdlib os.
"""

import os

# --- Model IDs (cross-region inference prefix for Bedrock) ---
MODEL_ID_OPUS: str = os.environ.get("MODEL_ID_OPUS", "us.anthropic.claude-opus-4-6-v1")
MODEL_ID_SONNET: str = os.environ.get("MODEL_ID_SONNET", "us.anthropic.claude-sonnet-4-20250514-v1:0")

# --- AWS Infrastructure ---
TASK_LEDGER_TABLE: str = os.environ.get("TASK_LEDGER_TABLE", "cloudcrew-projects")
METRICS_TABLE: str = os.environ.get("METRICS_TABLE", "cloudcrew-metrics")
KNOWLEDGE_BASE_ID: str = os.environ.get("KNOWLEDGE_BASE_ID", "")
PATTERNS_KNOWLEDGE_BASE_ID: str = os.environ.get("PATTERNS_KNOWLEDGE_BASE_ID", "")
PATTERNS_BUCKET: str = os.environ.get("PATTERNS_BUCKET", "")
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")

# --- Git ---
PROJECT_REPO_PATH: str = os.environ.get("PROJECT_REPO_PATH", "")
