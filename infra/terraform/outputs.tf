# Terraform outputs — resource identifiers needed for deployment and wiring.

# --- ECR ---
output "ecr_repository_url" {
  description = "ECR repository URL for the phase runner image"
  value       = aws_ecr_repository.phase_runner.repository_url
}

# --- ECS ---
output "ecs_cluster_arn" {
  description = "ECS cluster ARN"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_task_definition_arn" {
  description = "ECS phase runner task definition ARN"
  value       = aws_ecs_task_definition.phase_runner.arn
}

# --- Step Functions ---
output "step_functions_arn" {
  description = "Step Functions state machine ARN"
  value       = aws_sfn_state_machine.orchestrator.arn
}

# --- API Gateway ---
output "api_gateway_url" {
  description = "API Gateway invoke URL"
  value       = aws_api_gateway_stage.dev.invoke_url
}

# --- Lambda ---
output "lambda_sfn_handlers_arn" {
  description = "SFN handlers Lambda function ARN"
  value       = aws_lambda_function.sfn_handlers.arn
}

output "lambda_pm_review_arn" {
  description = "PM review Lambda function ARN"
  value       = aws_lambda_function.pm_review.arn
}

output "lambda_approval_arn" {
  description = "Approval Lambda function ARN"
  value       = aws_lambda_function.approval.arn
}

output "lambda_api_arn" {
  description = "API Lambda function ARN"
  value       = aws_lambda_function.api.arn
}

# --- Networking ---
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "subnet_ids" {
  description = "Public subnet IDs"
  value       = aws_subnet.public[*].id
}

# --- DynamoDB ---
output "dynamodb_projects_table" {
  description = "DynamoDB projects table name"
  value       = aws_dynamodb_table.projects.name
}

# --- S3 ---
output "sow_bucket" {
  description = "SOW uploads S3 bucket name"
  value       = aws_s3_bucket.sow_uploads.id
}
