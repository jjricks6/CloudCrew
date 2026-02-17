# DynamoDB tables. All use PAY_PER_REQUEST billing (on-demand, zero cost when idle).
#
# Table: cloudcrew-projects
# - Task ledger (project state, phase tracking, agent assignments)
# - Approval tokens (waitForTaskToken storage)
# PK: PROJECT#{project_id}, SK: LEDGER | TOKEN#{token_id}
#
# Table: cloudcrew-metrics
# - Engagement metrics (per-engagement summary, per-phase breakdowns)
# - Cross-engagement timeline (trend queries)
# - Post-engagement surveys
# PK: ENGAGEMENT#{project_id}, SK: SUMMARY | PHASE#{name} | SURVEY
# PK: TIMELINE, SK: #{timestamp}#{project_id}
