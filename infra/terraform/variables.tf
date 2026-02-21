variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "budget_alert_email" {
  description = "Email address for budget alerts"
  type        = string
}

variable "monthly_budget_amount" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 50
}

# --- Networking ---

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# --- ECS ---

variable "ecs_cpu" {
  description = "CPU units for the ECS phase runner task (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "ecs_memory" {
  description = "Memory (MiB) for the ECS phase runner task"
  type        = number
  default     = 2048
}

# --- Lambda ---

variable "lambda_pm_review_memory" {
  description = "Memory (MB) for the PM review Lambda"
  type        = number
  default     = 512
}

variable "lambda_pm_review_timeout" {
  description = "Timeout (seconds) for the PM review Lambda"
  type        = number
  default     = 300
}

variable "lambda_pm_chat_memory" {
  description = "Memory (MB) for the PM chat Lambda"
  type        = number
  default     = 512
}

variable "lambda_pm_chat_timeout" {
  description = "Timeout (seconds) for the PM chat Lambda"
  type        = number
  default     = 120
}

# --- Auth ---

variable "enable_auth" {
  description = "Enable Cognito authorizer on API Gateway methods"
  type        = bool
  default     = false
}

# --- Dashboard ---

variable "dashboard_origin" {
  description = "Allowed CORS origin for the dashboard (CloudFront domain or * for dev). Use * only in dev — set to the CloudFront domain in staging/prod."
  type        = string
  default     = "*"
}
