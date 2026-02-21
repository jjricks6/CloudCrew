# Cognito user pool for customer authentication.

resource "aws_cognito_user_pool" "main" {
  name = "cloudcrew-users-${var.environment}"

  # Sign-in with email
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  password_policy {
    minimum_length    = 8
    require_uppercase = true
    require_lowercase = true
    require_numbers   = true
    require_symbols   = false
  }

  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = { Name = "cloudcrew-users-${var.environment}" }
}

resource "aws_cognito_user_pool_client" "dashboard" {
  name         = "cloudcrew-dashboard-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  # SPA client — no client secret
  generate_secret = false

  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
  ]

  # Token validity
  access_token_validity  = 1  # hours
  id_token_validity      = 1  # hours
  refresh_token_validity = 30 # days

  token_validity_units {
    access_token  = "hours"
    id_token      = "hours"
    refresh_token = "days"
  }
}

resource "aws_cognito_user_pool_domain" "main" {
  domain       = "cloudcrew-${data.aws_caller_identity.current.account_id}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id
}
