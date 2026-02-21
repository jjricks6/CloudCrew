# WebSocket API Gateway for real-time dashboard communication.
# Routes: $connect, $disconnect, $default
# All routes integrated with a single Lambda function (ws_handlers.route).
#
# AUTH NOTE: The $connect route has no API Gateway authorizer. When
# enable_auth is true, the ws_handlers Lambda validates the JWT token
# from the query string (COGNITO_USER_POOL_ID / COGNITO_CLIENT_ID env vars).
# In dev (enable_auth=false), connections are unauthenticated.

# =============================================================================
# WebSocket API
# =============================================================================

resource "aws_apigatewayv2_api" "websocket" {
  name                       = "cloudcrew-ws-${var.environment}"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"

  tags = { Name = "cloudcrew-ws-${var.environment}" }
}

# =============================================================================
# Lambda Function for WebSocket handlers
# =============================================================================

resource "aws_cloudwatch_log_group" "lambda_ws" {
  name              = "/aws/lambda/cloudcrew-ws-handlers"
  retention_in_days = 14

  tags = { Name = "cloudcrew-ws-handlers-logs" }
}

resource "aws_lambda_function" "ws_handlers" {
  function_name = "cloudcrew-ws-handlers"
  role          = aws_iam_role.lambda_ws.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.phase_runner.repository_url}:latest"
  memory_size   = 128
  timeout       = 10

  image_config {
    entry_point = ["python", "-m", "awslambdaric"]
    command     = ["src.phases.ws_handlers.route"]
  }

  environment {
    variables = {
      AWS_DEFAULT_REGION   = var.aws_region
      CONNECTIONS_TABLE    = aws_dynamodb_table.connections.name
      COGNITO_USER_POOL_ID = aws_cognito_user_pool.main.id
      COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.dashboard.id
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda_ws]

  tags = { Name = "cloudcrew-ws-handlers" }
}

# =============================================================================
# IAM Role for WebSocket Lambda
# =============================================================================

resource "aws_iam_role" "lambda_ws" {
  name = "cloudcrew-lambda-ws-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = { Name = "cloudcrew-lambda-ws-${var.environment}" }
}

resource "aws_iam_role_policy" "lambda_ws" {
  name = "ws-handlers"
  role = aws_iam_role.lambda_ws.id

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
        Resource = "${aws_cloudwatch_log_group.lambda_ws.arn}:*"
      },
      {
        Sid    = "DynamoDB"
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:Scan",
        ]
        Resource = aws_dynamodb_table.connections.arn
      },
      {
        Sid      = "ManageConnections"
        Effect   = "Allow"
        Action   = "execute-api:ManageConnections"
        Resource = "${aws_apigatewayv2_api.websocket.execution_arn}/${var.environment}/*"
      },
    ]
  })
}

# =============================================================================
# Lambda Permission for WebSocket API Gateway
# =============================================================================

resource "aws_lambda_permission" "ws_api_gateway" {
  statement_id  = "AllowWebSocketAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ws_handlers.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.websocket.execution_arn}/*/*"
}

# =============================================================================
# Integrations
# =============================================================================

resource "aws_apigatewayv2_integration" "ws_lambda" {
  api_id             = aws_apigatewayv2_api.websocket.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.ws_handlers.invoke_arn
  integration_method = "POST"
}

# =============================================================================
# Routes: $connect, $disconnect, $default
# =============================================================================

resource "aws_apigatewayv2_route" "connect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$connect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_lambda.id}"
}

resource "aws_apigatewayv2_route" "disconnect" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$disconnect"
  target    = "integrations/${aws_apigatewayv2_integration.ws_lambda.id}"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.websocket.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.ws_lambda.id}"
}

# =============================================================================
# Stage
# =============================================================================

resource "aws_apigatewayv2_stage" "ws" {
  api_id      = aws_apigatewayv2_api.websocket.id
  name        = var.environment
  auto_deploy = true

  default_route_settings {
    throttling_burst_limit = 100
    throttling_rate_limit  = 50
  }

  tags = { Name = "cloudcrew-ws-${var.environment}" }
}
