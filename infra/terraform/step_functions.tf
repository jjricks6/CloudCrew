# Step Functions state machine for phase orchestration.
# Discovery → Architecture → POC → Production → Handoff
# Each phase: ECS Swarm → PM Review (Lambda) → Approval Gate (waitForTaskToken)
