variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security Group ID for ECS tasks"
  type        = string
}

variable "execution_role_arn" {
  description = "ECS Task Execution Role ARN"
  type        = string
}

variable "task_role_arn" {
  description = "ECS Task Role ARN"
  type        = string
}

variable "db_endpoint" {
  description = "Database endpoint"
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

variable "db_name" {
  description = "Database name"
  type        = string
}

variable "receipts_bucket_name" {
  description = "S3 bucket name for receipts"
  type        = string
}

variable "ocr_queue_url" {
  description = "OCR SQS queue URL"
  type        = string
}

variable "validation_queue_url" {
  description = "Validation SQS queue URL"
  type        = string
}

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

# Report Service Variables
variable "report_service_image" {
  description = "Docker image for report service"
  type        = string
}

variable "report_service_cpu" {
  description = "CPU units for report service"
  type        = number
  default     = 512
}

variable "report_service_memory" {
  description = "Memory for report service (MiB)"
  type        = number
  default     = 1024
}

variable "report_service_desired_count" {
  description = "Desired number of report service tasks"
  type        = number
  default     = 2
}

variable "report_service_target_group_arn" {
  description = "ALB Target Group ARN for report service"
  type        = string
}

# Receipt Service Variables
variable "receipt_service_image" {
  description = "Docker image for receipt service"
  type        = string
}

variable "receipt_service_cpu" {
  description = "CPU units for receipt service"
  type        = number
  default     = 256
}

variable "receipt_service_memory" {
  description = "Memory for receipt service (MiB)"
  type        = number
  default     = 512
}

variable "receipt_service_desired_count" {
  description = "Desired number of receipt service tasks"
  type        = number
  default     = 2
}

variable "receipt_service_target_group_arn" {
  description = "ALB Target Group ARN for receipt service"
  type        = string
  default     = ""
}

# Review Service Variables
variable "review_service_image" {
  description = "Docker image for review service"
  type        = string
}

variable "review_service_cpu" {
  description = "CPU units for review service"
  type        = number
  default     = 256
}

variable "review_service_memory" {
  description = "Memory for review service (MiB)"
  type        = number
  default     = 512
}

variable "review_service_desired_count" {
  description = "Desired number of review service tasks"
  type        = number
  default     = 1
}

variable "review_service_target_group_arn" {
  description = "ALB Target Group ARN for review service"
  type        = string
  default     = ""
}
