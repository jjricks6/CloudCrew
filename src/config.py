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

# --- AgentCore Memory ---
STM_MEMORY_ID: str = os.environ.get("STM_MEMORY_ID", "")
LTM_MEMORY_ID: str = os.environ.get("LTM_MEMORY_ID", "")

# --- Git ---
PROJECT_REPO_PATH: str = os.environ.get("PROJECT_REPO_PATH", "")

# --- Bedrock Client ---
BEDROCK_READ_TIMEOUT: int = int(os.environ.get("BEDROCK_READ_TIMEOUT", "300"))
BEDROCK_MAX_RETRIES: int = int(os.environ.get("BEDROCK_MAX_RETRIES", "3"))

# --- Timeouts (seconds) ---
NODE_TIMEOUT: float = float(os.environ.get("NODE_TIMEOUT", "600.0"))
EXECUTION_TIMEOUT_DISCOVERY: float = float(os.environ.get("EXECUTION_TIMEOUT_DISCOVERY", "1800.0"))
EXECUTION_TIMEOUT_ARCHITECTURE: float = float(os.environ.get("EXECUTION_TIMEOUT_ARCHITECTURE", "2400.0"))

# --- Phase Retry ---
PHASE_MAX_RETRIES: int = int(os.environ.get("PHASE_MAX_RETRIES", "2"))
PHASE_RETRY_DELAY: float = float(os.environ.get("PHASE_RETRY_DELAY", "5.0"))
