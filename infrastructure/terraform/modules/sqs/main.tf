terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# OCR Jobs Queue (main queue)
resource "aws_sqs_queue" "ocr_jobs" {
  name                       = "${var.project_name}-${var.environment}-ocr-jobs"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 1209600  # 14 days

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ocr_jobs_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-jobs"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "ocr-processing"
  }
}

# OCR Jobs DLQ
resource "aws_sqs_queue" "ocr_jobs_dlq" {
  name                       = "${var.project_name}-${var.environment}-ocr-jobs-dlq"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 1209600

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-jobs-dlq"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "dead-letter-for-ocr"
  }
}

# Validation Jobs Queue (main queue)
resource "aws_sqs_queue" "validation_jobs" {
  name                       = "${var.project_name}-${var.environment}-validation-jobs"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 1209600

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.validation_jobs_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-validation-jobs"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "validation-processing"
  }
}

# Validation Jobs DLQ
resource "aws_sqs_queue" "validation_jobs_dlq" {
  name                       = "${var.project_name}-${var.environment}-validation-jobs-dlq"
  visibility_timeout_seconds = 180
  message_retention_seconds  = 1209600

  tags = {
    Name        = "${var.project_name}-${var.environment}-validation-jobs-dlq"
    Environment = var.environment
    Project     = var.project_name
    Purpose     = "dead-letter-for-validation"
  }
}

# Queue Policy for ECS tasks
resource "aws_sqs_queue_policy" "ecs_access" {
  queue_url = aws_sqs_queue.ocr_jobs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = aws_sqs_queue.ocr_jobs.arn
      }
    ]
  })
}

# IAM policy for SQS access
resource "aws_iam_policy" "sqs_access" {
  name        = "${var.project_name}-${var.environment}-sqs-access"
  description = "Allow ECS tasks to access SQS queues"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = [
          aws_sqs_queue.ocr_jobs.arn,
          aws_sqs_queue.ocr_jobs_dlq.arn,
          aws_sqs_queue.validation_jobs.arn,
          aws_sqs_queue.validation_jobs_dlq.arn
        ]
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-sqs-access"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Outputs
output "ocr_queue_url" {
  value = aws_sqs_queue.ocr_jobs.url
}

output "ocr_queue_arn" {
  value = aws_sqs_queue.ocr_jobs.arn
}

output "ocr_dlq_url" {
  value = aws_sqs_queue.ocr_jobs_dlq.url
}

output "validation_queue_url" {
  value = aws_sqs_queue.validation_jobs.url
}

output "validation_queue_arn" {
  value = aws_sqs_queue.validation_jobs.arn
}

output "validation_dlq_url" {
  value = aws_sqs_queue.validation_jobs_dlq.url
}

output "sqs_access_policy_arn" {
  value = aws_iam_policy.sqs_access.arn
}
