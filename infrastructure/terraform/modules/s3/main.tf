terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Receipts bucket for storing uploaded receipt images
resource "aws_s3_bucket" "receipts" {
  bucket = "${var.project_name}-${var.environment}-receipts-${data.aws_caller_identity.current.account_id}"

  tags = {
    Name        = "${var.project_name}-${var.environment}-receipts"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_s3_bucket_versioning" "receipts" {
  bucket = aws_s3_bucket.receipts.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "receipts" {
  bucket = aws_s3_bucket.receipts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "receipts" {
  bucket = aws_s3_bucket.receipts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Terraform state bucket
resource "aws_s3_bucket" "terraform_state" {
  count  = var.create_terraform_state_bucket ? 1 : 0
  bucket = "${var.project_name}-terraform-state-${var.environment}-${data.aws_caller_identity.current.account_id}"

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Name        = "${var.project_name}-terraform-state"
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 bucket for ECS exec logs
resource "aws_s3_bucket" "ecs_exec" {
  bucket = "${var.project_name}-${var.environment}-ecs-exec-${data.aws_caller_identity.current.account_id}"

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  lifecycle_rule {
    id      = "log-expiration"
    enabled = true

    expiration {
      days = 90
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecs-exec"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM policy for ECS task role to access S3
resource "aws_iam_policy" "s3_receipts_access" {
  name        = "${var.project_name}-${var.environment}-s3-receipts-access"
  description = "Allow ECS tasks to access receipts S3 bucket"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.receipts.arn}",
          "${aws_s3_bucket.receipts.arn}/*"
        ]
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-s3-access"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Outputs
output "receipts_bucket_name" {
  value = aws_s3_bucket.receipts.bucket
}

output "receipts_bucket_arn" {
  value = aws_s3_bucket.receipts.arn
}

output "terraform_state_bucket_name" {
  value = var.create_terraform_state_bucket ? aws_s3_bucket.terraform_state[0].bucket : ""
}

output "ecs_exec_bucket_name" {
  value = aws_s3_bucket.ecs_exec.bucket
}

output "s3_access_policy_arn" {
  value = aws_iam_policy.s3_receipts_access.arn
}
