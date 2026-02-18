# ECS Fargate cluster + task definition for phase execution.
# NO ECS Services — only Tasks launched on-demand by Step Functions.
# Tasks run in public subnets (dev) with auto-assign public IP.

resource "aws_ecs_cluster" "main" {
  name = "cloudcrew-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "cloudcrew-${var.environment}" }
}

# --- CloudWatch Log Group for ECS ---

resource "aws_cloudwatch_log_group" "ecs_phase_runner" {
  name              = "/ecs/cloudcrew-phase-runner"
  retention_in_days = 14

  tags = { Name = "cloudcrew-phase-runner-logs" }
}

# --- Task Definition ---

resource "aws_ecs_task_definition" "phase_runner" {
  family                   = "cloudcrew-phase-runner"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_cpu
  memory                   = var.ecs_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([
    {
      name      = "phase-runner"
      image     = "${aws_ecr_repository.phase_runner.repository_url}:latest"
      essential = true

      environment = [
        { name = "AWS_DEFAULT_REGION", value = var.aws_region },
        { name = "TASK_LEDGER_TABLE", value = aws_dynamodb_table.projects.name },
        { name = "SOW_BUCKET", value = aws_s3_bucket.sow_uploads.id },
      ]

      # PROJECT_ID, PHASE, TASK_TOKEN, CUSTOMER_FEEDBACK set at run_task time

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_phase_runner.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "phase"
        }
      }
    }
  ])

  tags = { Name = "cloudcrew-phase-runner" }
}
