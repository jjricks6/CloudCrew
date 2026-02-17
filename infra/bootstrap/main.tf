# Bootstrap: creates S3 bucket + DynamoDB table for Terraform remote state.
# Run once. Uses local state. These resources persist permanently (~$0.02/month).
#
# Usage:
#   make bootstrap-init
#   make bootstrap-apply

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = "cloudcrew"
      ManagedBy = "terraform"
      Component = "bootstrap"
    }
  }
}

# --- S3 bucket for Terraform state ---

#checkov:skip=CKV2_AWS_62:Event notifications unnecessary for state bucket
#checkov:skip=CKV_AWS_144:Cross-region replication unnecessary for single-region dev project
#checkov:skip=CKV_AWS_18:Access logging adds cost; state bucket access audited via CloudTrail
resource "aws_s3_bucket" "terraform_state" {
  bucket = var.state_bucket_name

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# --- DynamoDB table for state locking ---

#checkov:skip=CKV_AWS_28:PITR unnecessary for lock table — ephemeral lock data only
#checkov:skip=CKV_AWS_119:CMK encryption unnecessary — default encryption sufficient for lock table
resource "aws_dynamodb_table" "terraform_locks" {
  name         = var.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }
}
