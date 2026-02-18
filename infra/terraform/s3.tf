# S3 buckets.
# - SOW uploads (customer uploads Statement of Work)
# - Bedrock KB data source (artifacts indexed for agent search)
# Dashboard hosting and pattern library deferred to M5/M6.

# --- SOW Uploads Bucket ---

resource "aws_s3_bucket" "sow_uploads" {
  bucket        = "cloudcrew-sow-uploads-${var.environment}"
  force_destroy = true

  tags = { Name = "cloudcrew-sow-uploads-${var.environment}" }
}

resource "aws_s3_bucket_versioning" "sow_uploads" {
  bucket = aws_s3_bucket.sow_uploads.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "sow_uploads" {
  bucket = aws_s3_bucket.sow_uploads.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "sow_uploads" {
  bucket = aws_s3_bucket.sow_uploads.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# --- Bedrock KB Data Bucket ---

resource "aws_s3_bucket" "kb_data" {
  bucket        = "cloudcrew-kb-data-${var.environment}"
  force_destroy = true

  tags = { Name = "cloudcrew-kb-data-${var.environment}" }
}

resource "aws_s3_bucket_versioning" "kb_data" {
  bucket = aws_s3_bucket.kb_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "kb_data" {
  bucket = aws_s3_bucket.kb_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_public_access_block" "kb_data" {
  bucket = aws_s3_bucket.kb_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
