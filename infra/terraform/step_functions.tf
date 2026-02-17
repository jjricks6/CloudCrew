# Step Functions state machine for phase orchestration.
# Discovery → Architecture → POC → Production → Handoff → Retrospective
# Each delivery phase: ECS Swarm → PM Review (Lambda) → Approval Gate (waitForTaskToken)
# Retrospective: ECS Swarm (PM, QA) → Finalize Metrics (Lambda) → Post-Engagement Survey → Complete
