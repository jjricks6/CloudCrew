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

output "lambda_pm_chat_arn" {
  description = "PM Chat Lambda function ARN"
  value       = aws_lambda_function.pm_chat.arn
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

# --- WebSocket API ---
output "websocket_api_url" {
  description = "WebSocket API Gateway URL for dashboard connections"
  value       = "wss://${aws_apigatewayv2_api.websocket.id}.execute-api.${var.aws_region}.amazonaws.com/${var.environment}"
}

output "lambda_ws_handlers_arn" {
  description = "WebSocket handlers Lambda function ARN"
  value       = aws_lambda_function.ws_handlers.arn
}

# --- DynamoDB ---
output "dynamodb_projects_table" {
  description = "DynamoDB projects table name"
  value       = aws_dynamodb_table.projects.name
}

output "dynamodb_connections_table" {
  description = "DynamoDB connections table name"
  value       = aws_dynamodb_table.connections.name
}

output "dynamodb_activity_table" {
  description = "DynamoDB activity table name"
  value       = aws_dynamodb_table.activity.name
}

output "dynamodb_board_tasks_table" {
  description = "DynamoDB board tasks table name"
  value       = aws_dynamodb_table.board_tasks.name
}

# --- S3 ---
output "sow_bucket" {
  description = "SOW uploads S3 bucket name"
  value       = aws_s3_bucket.sow_uploads.id
}

output "dashboard_bucket" {
  description = "Dashboard static hosting S3 bucket name"
  value       = aws_s3_bucket.dashboard.id
}

# --- Cognito ---
output "cognito_user_pool_id" {
  description = "Cognito user pool ID for dashboard authentication"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_client_id" {
  description = "Cognito app client ID for dashboard SPA"
  value       = aws_cognito_user_pool_client.dashboard.id
}

output "cognito_domain" {
  description = "Cognito hosted UI domain"
  value       = aws_cognito_user_pool_domain.main.domain
}

# --- CloudFront ---
output "cloudfront_domain" {
  description = "CloudFront distribution domain for the dashboard"
  value       = aws_cloudfront_distribution.dashboard.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (for cache invalidation)"
  value       = aws_cloudfront_distribution.dashboard.id
}
