# IAM roles and policies.
# Follows least-privilege principle — each role gets only the permissions it needs.

data "aws_caller_identity" "current" {}

# =============================================================================
# ECS Task Execution Role (pulls ECR images, writes CloudWatch logs)
# =============================================================================

resource "aws_iam_role" "ecs_execution" {
  name = "cloudcrew-ecs-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-ecs-execution-${var.environment}" }
}

resource "aws_iam_role_policy" "ecs_execution" {
  name = "ecs-execution"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ECR"
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Resource = "*"
      },
      {
        Sid    = "ECRImage"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
        ]
        Resource = aws_ecr_repository.phase_runner.arn
      },
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.ecs_phase_runner.arn}:*"
      },
    ]
  })
}

# =============================================================================
# ECS Task Role (runtime permissions for the phase runner container)
# =============================================================================

resource "aws_iam_role" "ecs_task" {
  name = "cloudcrew-ecs-task-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-ecs-task-${var.environment}" }
}

resource "aws_iam_role_policy" "ecs_task" {
  name = "ecs-task"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Bedrock"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      },
      {
        Sid    = "BedrockKB"
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve",
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:knowledge-base/*"
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
        ]
        Resource = [
          aws_dynamodb_table.projects.arn,
          aws_dynamodb_table.metrics.arn,
        ]
      },
      {
        Sid    = "ActivityTable"
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:Query",
        ]
        Resource = aws_dynamodb_table.activity.arn
      },
      {
        Sid    = "BroadcastConnections"
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:DeleteItem",
        ]
        Resource = aws_dynamodb_table.connections.arn
      },
      {
        Sid    = "BroadcastPostToConnection"
        Effect = "Allow"
        Action = "execute-api:ManageConnections"
        Resource = "${aws_apigatewayv2_api.websocket.execution_arn}/${var.environment}/*"
      },
      {
        Sid    = "S3Read"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
        ]
        Resource = [
          aws_s3_bucket.sow_uploads.arn,
          "${aws_s3_bucket.sow_uploads.arn}/*",
          aws_s3_bucket.kb_data.arn,
          "${aws_s3_bucket.kb_data.arn}/*",
        ]
      },
      {
        Sid    = "StepFunctions"
        Effect = "Allow"
        Action = [
          "states:SendTaskSuccess",
          "states:SendTaskFailure",
        ]
        Resource = aws_sfn_state_machine.orchestrator.arn
      },
    ]
  })
}

# =============================================================================
# Lambda: PM Review (runs PM agent to validate deliverables)
# =============================================================================

resource "aws_iam_role" "lambda_pm_review" {
  name = "cloudcrew-lambda-pm-review-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-lambda-pm-review-${var.environment}" }
}

resource "aws_iam_role_policy" "lambda_pm_review" {
  name = "pm-review"
  role = aws_iam_role.lambda_pm_review.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.lambda_pm_review.arn}:*"
      },
      {
        Sid    = "Bedrock"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
        ]
        Resource = aws_dynamodb_table.projects.arn
      },
      {
        Sid    = "S3Read"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
        ]
        Resource = [
          "${aws_s3_bucket.sow_uploads.arn}/*",
          "${aws_s3_bucket.kb_data.arn}/*",
        ]
      },
    ]
  })
}

# =============================================================================
# Lambda: Approval Handler (approval/revise API endpoints)
# =============================================================================

resource "aws_iam_role" "lambda_approval" {
  name = "cloudcrew-lambda-approval-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-lambda-approval-${var.environment}" }
}

resource "aws_iam_role_policy" "lambda_approval" {
  name = "approval"
  role = aws_iam_role.lambda_approval.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.lambda_approval.arn}:*"
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
        ]
        Resource = aws_dynamodb_table.projects.arn
      },
      {
        Sid    = "StepFunctions"
        Effect = "Allow"
        Action = [
          "states:SendTaskSuccess",
          "states:SendTaskFailure",
        ]
        Resource = aws_sfn_state_machine.orchestrator.arn
      },
    ]
  })
}

# =============================================================================
# Lambda: API Handler (project CRUD, status, deliverables, interrupt respond)
# =============================================================================

resource "aws_iam_role" "lambda_api" {
  name = "cloudcrew-lambda-api-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-lambda-api-${var.environment}" }
}

resource "aws_iam_role_policy" "lambda_api" {
  name = "api"
  role = aws_iam_role.lambda_api.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.lambda_api.arn}:*"
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
        ]
        Resource = aws_dynamodb_table.projects.arn
      },
      {
        Sid    = "S3Upload"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
        ]
        Resource = "${aws_s3_bucket.sow_uploads.arn}/*"
      },
      {
        Sid    = "StepFunctions"
        Effect = "Allow"
        Action = [
          "states:StartExecution",
        ]
        Resource = aws_sfn_state_machine.orchestrator.arn
      },
    ]
  })
}

# =============================================================================
# Lambda: SFN Handlers (store approval token, update ledger)
# =============================================================================

resource "aws_iam_role" "lambda_sfn_handlers" {
  name = "cloudcrew-lambda-sfn-handlers-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-lambda-sfn-handlers-${var.environment}" }
}

resource "aws_iam_role_policy" "lambda_sfn_handlers" {
  name = "sfn-handlers"
  role = aws_iam_role.lambda_sfn_handlers.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.lambda_sfn_handlers.arn}:*"
      },
      {
        Sid    = "ECS"
        Effect = "Allow"
        Action = [
          "ecs:RunTask",
          "ecs:DescribeTasks",
        ]
        Resource = aws_ecs_task_definition.phase_runner.arn
      },
      {
        Sid    = "PassRole"
        Effect = "Allow"
        Action = "iam:PassRole"
        Resource = [
          aws_iam_role.ecs_execution.arn,
          aws_iam_role.ecs_task.arn,
        ]
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
        ]
        Resource = aws_dynamodb_table.projects.arn
      },
      {
        Sid    = "BroadcastConnections"
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:DeleteItem",
        ]
        Resource = aws_dynamodb_table.connections.arn
      },
      {
        Sid    = "BroadcastPostToConnection"
        Effect = "Allow"
        Action = "execute-api:ManageConnections"
        Resource = "${aws_apigatewayv2_api.websocket.execution_arn}/${var.environment}/*"
      },
    ]
  })
}

# =============================================================================
# Step Functions Execution Role
# =============================================================================

resource "aws_iam_role" "sfn_execution" {
  name = "cloudcrew-sfn-execution-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "states.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-sfn-execution-${var.environment}" }
}

resource "aws_iam_role_policy" "sfn_execution" {
  name = "sfn-execution"
  role = aws_iam_role.sfn_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeLambda"
        Effect = "Allow"
        Action = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.sfn_handlers.arn,
          aws_lambda_function.pm_review.arn,
          aws_lambda_function.approval.arn,
        ]
      },
      {
        Sid    = "Logs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups",
        ]
        Resource = "*"
      },
    ]
  })
}
