# API Gateway REST API for customer-facing endpoints.
# WebSocket API deferred to M5 (Dashboard).

resource "aws_api_gateway_rest_api" "main" {
  name        = "cloudcrew-api-${var.environment}"
  description = "CloudCrew customer API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = { Name = "cloudcrew-api-${var.environment}" }
}

# =============================================================================
# Resources
# =============================================================================

# /projects
resource "aws_api_gateway_resource" "projects" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "projects"
}

# /projects/{id}
resource "aws_api_gateway_resource" "project" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.projects.id
  path_part   = "{id}"
}

# /projects/{id}/status
resource "aws_api_gateway_resource" "status" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.project.id
  path_part   = "status"
}

# /projects/{id}/deliverables
resource "aws_api_gateway_resource" "deliverables" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.project.id
  path_part   = "deliverables"
}

# /projects/{id}/approve
resource "aws_api_gateway_resource" "approve" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.project.id
  path_part   = "approve"
}

# /projects/{id}/revise
resource "aws_api_gateway_resource" "revise" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.project.id
  path_part   = "revise"
}

# /projects/{id}/interrupt
resource "aws_api_gateway_resource" "interrupt" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.project.id
  path_part   = "interrupt"
}

# /projects/{id}/interrupt/{interruptId}
resource "aws_api_gateway_resource" "interrupt_id" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interrupt.id
  path_part   = "{interruptId}"
}

# /projects/{id}/interrupt/{interruptId}/respond
resource "aws_api_gateway_resource" "interrupt_respond" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.interrupt_id.id
  path_part   = "respond"
}

# /projects/{id}/chat
resource "aws_api_gateway_resource" "chat" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.project.id
  path_part   = "chat"
}

# /projects/{id}/upload
resource "aws_api_gateway_resource" "upload" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.project.id
  path_part   = "upload"
}

# =============================================================================
# Methods → Lambda integrations
# =============================================================================

# POST /projects → api Lambda
resource "aws_api_gateway_method" "post_projects" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.projects.id
  http_method   = "POST"
  authorization = "NONE" # IAM auth for M4; Cognito in M5
}

resource "aws_api_gateway_integration" "post_projects" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.projects.id
  http_method             = aws_api_gateway_method.post_projects.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# GET /projects/{id}/status → api Lambda
resource "aws_api_gateway_method" "get_status" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.status.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_status" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.status.id
  http_method             = aws_api_gateway_method.get_status.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# GET /projects/{id}/deliverables → api Lambda
resource "aws_api_gateway_method" "get_deliverables" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.deliverables.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_deliverables" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.deliverables.id
  http_method             = aws_api_gateway_method.get_deliverables.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# POST /projects/{id}/approve → approval Lambda
resource "aws_api_gateway_method" "post_approve" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.approve.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_approve" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.approve.id
  http_method             = aws_api_gateway_method.post_approve.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.approval.invoke_arn
}

# POST /projects/{id}/revise → approval Lambda
resource "aws_api_gateway_method" "post_revise" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.revise.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_revise" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.revise.id
  http_method             = aws_api_gateway_method.post_revise.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.approval.invoke_arn
}

# POST /projects/{id}/interrupt/{interruptId}/respond → api Lambda
resource "aws_api_gateway_method" "post_interrupt_respond" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.interrupt_respond.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_interrupt_respond" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.interrupt_respond.id
  http_method             = aws_api_gateway_method.post_interrupt_respond.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# POST /projects/{id}/chat → api Lambda
resource "aws_api_gateway_method" "post_chat" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.chat.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_chat" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.chat.id
  http_method             = aws_api_gateway_method.post_chat.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# GET /projects/{id}/chat → api Lambda
resource "aws_api_gateway_method" "get_chat" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.chat.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_chat" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.chat.id
  http_method             = aws_api_gateway_method.get_chat.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# POST /projects/{id}/upload → api Lambda
resource "aws_api_gateway_method" "post_upload" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.upload.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_upload" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.upload.id
  http_method             = aws_api_gateway_method.post_upload.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api.invoke_arn
}

# =============================================================================
# Lambda Permissions for API Gateway
# =============================================================================

resource "aws_lambda_permission" "api_gateway_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_approval" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.approval.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# =============================================================================
# Deployment + Stage
# =============================================================================

resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.projects,
      aws_api_gateway_resource.project,
      aws_api_gateway_resource.status,
      aws_api_gateway_resource.deliverables,
      aws_api_gateway_resource.approve,
      aws_api_gateway_resource.revise,
      aws_api_gateway_resource.interrupt_respond,
      aws_api_gateway_resource.chat,
      aws_api_gateway_resource.upload,
      aws_api_gateway_method.post_projects,
      aws_api_gateway_method.get_status,
      aws_api_gateway_method.get_deliverables,
      aws_api_gateway_method.post_approve,
      aws_api_gateway_method.post_revise,
      aws_api_gateway_method.post_interrupt_respond,
      aws_api_gateway_integration.post_projects,
      aws_api_gateway_integration.get_status,
      aws_api_gateway_integration.get_deliverables,
      aws_api_gateway_integration.post_approve,
      aws_api_gateway_integration.post_revise,
      aws_api_gateway_integration.post_interrupt_respond,
      aws_api_gateway_method.post_chat,
      aws_api_gateway_method.get_chat,
      aws_api_gateway_method.post_upload,
      aws_api_gateway_integration.post_chat,
      aws_api_gateway_integration.get_chat,
      aws_api_gateway_integration.post_upload,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "dev" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  tags = { Name = "cloudcrew-api-${var.environment}" }
}
