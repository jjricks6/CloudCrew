# DynamoDB tables. All use PAY_PER_REQUEST billing (on-demand, zero cost when idle).
#
# Table: cloudcrew-projects
# - Task ledger (project state, phase tracking, agent assignments)
# - Approval tokens (waitForTaskToken storage)
# - Interrupt records (mid-phase HITL questions/responses)
# PK: PROJECT#{project_id}, SK: LEDGER | TOKEN#{phase} | INTERRUPT#{id}
#
# Table: cloudcrew-metrics (populated in M6)
# - Engagement metrics (per-engagement summary, per-phase breakdowns)
# - Cross-engagement timeline (trend queries)
# PK: ENGAGEMENT#{project_id}, SK: SUMMARY | PHASE#{name} | SURVEY
# PK: TIMELINE, SK: #{timestamp}#{project_id}

resource "aws_dynamodb_table" "projects" {
  name         = "cloudcrew-projects"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = { Name = "cloudcrew-projects" }
}

resource "aws_dynamodb_table" "metrics" {
  name         = "cloudcrew-metrics"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = { Name = "cloudcrew-metrics" }
}

# Table: cloudcrew-connections
# - WebSocket connection registry for real-time dashboard push
# PK: projectId, SK: connectionId, TTL: 2h
resource "aws_dynamodb_table" "connections" {
  name         = "cloudcrew-connections"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = { Name = "cloudcrew-connections" }
}

# Table: cloudcrew-activity
# - Agent activity events for dashboard visualization
# PK: PROJECT#{id}, SK: EVENT#{timestamp}#{uuid}, TTL: 24h
resource "aws_dynamodb_table" "activity" {
  name         = "cloudcrew-activity"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = { Name = "cloudcrew-activity" }
}

# Table: cloudcrew-board-tasks
# - Kanban board tasks managed by agents, visible to customer on dashboard
# PK: PROJECT#{project_id}, SK: TASK#{phase}#{task_id}
resource "aws_dynamodb_table" "board_tasks" {
  name         = "cloudcrew-board-tasks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "PK"
  range_key    = "SK"

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = { Name = "cloudcrew-board-tasks" }
}
