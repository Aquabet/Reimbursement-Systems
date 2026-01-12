terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-${var.environment}-db-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-subnet-group"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DB Parameter Group (optimized for reimbursement system workload)
resource "aws_db_parameter_group" "main" {
  name   = "${var.project_name}-${var.environment}-db-params"
  family = var.db_family

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "character_set_client"
    value = "utf8mb4"
  }

  parameter {
    name  = "max_connections"
    value = var.db_max_connections
  }

  parameter {
    name  = "slow_query_log"
    value = "1"
  }

  parameter {
    name  = "log_output"
    value = "FILE"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-params"
    Environment = var.environment
    Project     = var.project_name
  }
}

# RDS Instance
resource "aws_db_instance" "main" {
  identifier        = "${var.project_name}-${var.environment}-db"
  engine            = var.db_engine
  engine_version    = var.db_engine_version
  instance_class    = var.db_instance_class
  allocated_storage = var.db_allocated_storage
  storage_type      = var.db_storage_type
  storage_encrypted = var.db_storage_encrypted

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.db_security_group_id]
  parameter_group_name   = aws_db_parameter_group.main.name

  backup_retention_period = var.db_backup_retention_period
  backup_window           = var.db_backup_window
  maintenance_window      = var.db_maintenance_window

  # Enable deletion protection for production
  deletion_protection = var.environment == "production"

  # Enable performance insights
  performance_insights_enabled          = true
  performance_insights_retention_period = 7

  # Multi-AZ for production
  multi_az = var.environment == "production"

  # CloudWatch logs
  enabled_cloudwatch_logs_exports = ["error", "general", "slow-query"]

  tags = {
    Name        = "${var.project_name}-${var.environment}-db"
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "terraform"
  }

  lifecycle {
    prevent_destroy = var.environment == "production"
    ignore_changes  = [password]
  }
}

# RDS Proxy (optional, for connection pooling)
resource "aws_db_proxy" "main" {
  count = var.enable_proxy ? 1 : 0

  name                   = "${var.project_name}-${var.environment}-db-proxy"
  debug_logging          = var.environment != "production"
  engine_family          = "MYSQL"
  idle_client_timeout    = 1800
  require_tls            = true
  role_arn               = var.proxy_role_arn
  vpc_security_group_ids = [var.db_security_group_id]
  vpc_subnet_ids         = var.private_subnet_ids

  auth {
    auth_scheme = "SECRETS"
    description = "RDS Proxy authentication"
    iam_auth    = "DISABLED"
    secret_arn  = var.db_secret_arn
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-proxy"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Output DB endpoint
output "db_endpoint" {
  value = aws_db_instance.main.endpoint
}

output "db_port" {
  value = aws_db_instance.main.port
}

output "db_host" {
  value = split(":", aws_db_instance.main.endpoint)[0]
}

output "db_name" {
  value = var.db_name
}

output "db_username" {
  value     = var.db_username
  sensitive = true
}

output "db_password" {
  value     = var.db_password
  sensitive = true
}

output "db_proxy_endpoint" {
  value = var.enable_proxy ? aws_db_proxy.main[0].endpoint : ""
}
