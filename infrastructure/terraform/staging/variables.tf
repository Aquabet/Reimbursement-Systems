variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "reimbursement-system"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# VPC Variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

# RDS Variables
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "reimbursement_db"
}

variable "db_username" {
  description = "Database username"
  type        = string
  default     = "dbadmin"
}

variable "db_password" {
  description = "Database password (should be provided via TF_VAR or prompt)"
  type        = string
  sensitive   = true
}

variable "db_max_connections" {
  description = "Maximum database connections"
  type        = number
  default     = 100
}

variable "enable_proxy" {
  description = "Enable RDS proxy"
  type        = bool
  default     = false
}

variable "proxy_role_arn" {
  description = "RDS Proxy IAM role ARN"
  type        = string
  default     = ""
}

# ECS Variables
variable "api_image" {
  description = "Docker image for API service"
  type        = string
  default     = "reimbursement-api:latest"
}

variable "ocr_worker_image" {
  description = "Docker image for OCR worker"
  type        = string
  default     = "reimbursement-ocr-worker:latest"
}

variable "validation_worker_image" {
  description = "Docker image for validation worker"
  type        = string
  default     = "reimbursement-validation-worker:latest"
}

variable "api_desired_count" {
  description = "Desired number of API tasks"
  type        = number
  default     = 2
}

variable "api_max_count" {
  description = "Maximum number of API tasks for autoscaling"
  type        = number
  default     = 5
}

variable "worker_desired_count" {
  description = "Desired number of worker tasks"
  type        = number
  default     = 1
}

# Load Balancer Variables
variable "alb_target_group_arn" {
  description = "ALB Target Group ARN"
  type        = string
}

# Secrets
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

# Logging
variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs"
  type        = bool
  default     = true
}

variable "flow_logs_role_arn" {
  description = "IAM Role ARN for VPC Flow Logs"
  type        = string
  default     = ""
}
