# Two separate Bedrock Knowledge Bases (each with its own S3 data source).
# - Project artifacts KB (KNOWLEDGE_BASE_ID) — synced from project Git repo via S3
# - Pattern library KB (PATTERNS_KNOWLEDGE_BASE_ID) — synced from cloudcrew-patterns S3 bucket
# Separate KBs allow independent re-sync schedules and scoped search.
