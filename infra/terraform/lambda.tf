# Lambda functions — all use container images from ECR.
# Same Docker image as ECS, different CMD override per function.

# =============================================================================
# CloudWatch Log Groups
# =============================================================================

resource "aws_cloudwatch_log_group" "lambda_sfn_handlers" {
  name              = "/aws/lambda/cloudcrew-sfn-handlers"
  retention_in_days = 14

  tags = { Name = "cloudcrew-sfn-handlers-logs" }
}

resource "aws_cloudwatch_log_group" "lambda_pm_review" {
  name              = "/aws/lambda/cloudcrew-pm-review"
  retention_in_days = 14

  tags = { Name = "cloudcrew-pm-review-logs" }
}

resource "aws_cloudwatch_log_group" "lambda_approval" {
  name              = "/aws/lambda/cloudcrew-approval"
  retention_in_days = 14

  tags = { Name = "cloudcrew-approval-logs" }
}

resource "aws_cloudwatch_log_group" "lambda_api" {
  name              = "/aws/lambda/cloudcrew-api"
  retention_in_days = 14

  tags = { Name = "cloudcrew-api-logs" }
}

# =============================================================================
# Lambda Functions
# =============================================================================

# --- SFN Handlers (start_phase + store_approval_token, dispatched by route) ---

resource "aws_lambda_function" "sfn_handlers" {
  function_name = "cloudcrew-sfn-handlers"
  role          = aws_iam_role.lambda_sfn_handlers.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.phase_runner.repository_url}:latest"
  memory_size   = 128
  timeout       = 30

  image_config {
    entry_point = ["python", "-m", "awslambdaric"]
    command     = ["src.phases.sfn_handlers.route"]
  }

  environment {
    variables = {
      AWS_DEFAULT_REGION  = var.aws_region
      TASK_LEDGER_TABLE   = aws_dynamodb_table.projects.name
      ECS_CLUSTER_ARN     = aws_ecs_cluster.main.arn
      ECS_TASK_DEFINITION = aws_ecs_task_definition.phase_runner.arn
      ECS_SUBNETS         = join(",", aws_subnet.public[*].id)
      ECS_SECURITY_GROUP  = aws_security_group.ecs_tasks.id
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_sfn_handlers]

  tags = { Name = "cloudcrew-sfn-handlers" }
}

# --- PM Review (standalone PM agent for deliverable validation) ---

resource "aws_lambda_function" "pm_review" {
  function_name = "cloudcrew-pm-review"
  role          = aws_iam_role.lambda_pm_review.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.phase_runner.repository_url}:latest"
  memory_size   = var.lambda_pm_review_memory
  timeout       = var.lambda_pm_review_timeout

  image_config {
    entry_point = ["python", "-m", "awslambdaric"]
    command     = ["src.phases.pm_review_handler.handler"]
  }

  environment {
    variables = {
      AWS_DEFAULT_REGION = var.aws_region
      TASK_LEDGER_TABLE  = aws_dynamodb_table.projects.name
      SOW_BUCKET         = aws_s3_bucket.sow_uploads.id
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_pm_review]

  tags = { Name = "cloudcrew-pm-review" }
}

# --- Approval Handler (approve/revise endpoints) ---

resource "aws_lambda_function" "approval" {
  function_name = "cloudcrew-approval"
  role          = aws_iam_role.lambda_approval.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.phase_runner.repository_url}:latest"
  memory_size   = 128
  timeout       = 30

  image_config {
    entry_point = ["python", "-m", "awslambdaric"]
    command     = ["src.phases.api_handlers.route"]
  }

  environment {
    variables = {
      AWS_DEFAULT_REGION = var.aws_region
      TASK_LEDGER_TABLE  = aws_dynamodb_table.projects.name
      STATE_MACHINE_ARN  = aws_sfn_state_machine.orchestrator.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_approval]

  tags = { Name = "cloudcrew-approval" }
}

# --- API Handler (project CRUD, status, deliverables, interrupt respond) ---

resource "aws_lambda_function" "api" {
  function_name = "cloudcrew-api"
  role          = aws_iam_role.lambda_api.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.phase_runner.repository_url}:latest"
  memory_size   = 256
  timeout       = 30

  image_config {
    entry_point = ["python", "-m", "awslambdaric"]
    command     = ["src.phases.api_handlers.route"]
  }

  environment {
    variables = {
      AWS_DEFAULT_REGION = var.aws_region
      TASK_LEDGER_TABLE  = aws_dynamodb_table.projects.name
      SOW_BUCKET         = aws_s3_bucket.sow_uploads.id
      STATE_MACHINE_ARN  = aws_sfn_state_machine.orchestrator.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_api]

  tags = { Name = "cloudcrew-api" }
}
