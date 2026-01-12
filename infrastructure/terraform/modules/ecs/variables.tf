variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (staging, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

# Task Definition Variables
variable "api_image" {
  description = "Docker image for API service"
  type        = string
}

variable "ocr_worker_image" {
  description = "Docker image for OCR worker"
  type        = string
}

variable "validation_worker_image" {
  description = "Docker image for validation worker"
  type        = string
}

variable "api_cpu" {
  description = "CPU units for API task"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory for API task (MiB)"
  type        = number
  default     = 1024
}

variable "worker_cpu" {
  description = "CPU units for worker tasks"
  type        = number
  default     = 256
}

variable "worker_memory" {
  description = "Memory for worker tasks (MiB)"
  type        = number
  default     = 512
}

# ECS Cluster Variables
variable "ecs_cluster_id" {
  description = "ECS Cluster ID"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS Cluster name"
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "ECS Task Execution Role ARN"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS Task Role ARN"
  type        = string
}

variable "ecs_security_group_id" {
  description = "Security Group ID for ECS tasks"
  type        = string
}

# Networking Variables
variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

# Database Variables
variable "db_endpoint" {
  description = "Database endpoint"
  type        = string
}

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "db_username" {
  description = "Database username"
  type        = string
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

# S3 Variables
variable "receipts_bucket_name" {
  description = "S3 bucket name for receipts"
  type        = string
}

# SQS Variables
variable "ocr_queue_url" {
  description = "OCR SQS queue URL"
  type        = string
}

variable "validation_queue_url" {
  description = "Validation SQS queue URL"
  type        = string
}

# SSM Parameters
variable "alb_target_group_arn" {
  description = "ALB Target Group ARN (stored in SSM)"
  type        = string
}

# Secret Management
variable "secret_key" {
  description = "Flask secret key"
  type        = string
  sensitive   = true
}

variable "jwt_secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "enable_secrets_manager" {
  description = "Enable AWS Secrets Manager for sensitive data"
  type        = bool
  default     = false
}

# Service Configuration
variable "api_desired_count" {
  description = "Desired number of API tasks"
  type        = number
  default     = 2
}

variable "api_max_count" {
  description = "Maximum number of API tasks for autoscaling"
  type        = number
  default     = 10
}

variable "worker_desired_count" {
  description = "Desired number of worker tasks"
  type        = number
  default     = 1
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "enable_proxy" {
  description = "Enable RDS proxy"
  type        = bool
  default     = false
}
