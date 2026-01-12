terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # S3 Backend for state storage
  backend "s3" {
    bucket = "reimbursement-system-staging-terraform-state"  # Will be created by Terraform and replaced
    key    = "staging/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "terraform"
    }
  }
}

# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

locals {
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
}

# VPC Module
module "vpc" {
  source = "../modules/vpc"

  project_name          = var.project_name
  environment           = var.environment
  vpc_cidr              = var.vpc_cidr
  public_subnet_cidrs   = var.public_subnet_cidrs
  private_subnet_cidrs  = var.private_subnet_cidrs
  availability_zones    = local.availability_zones
  enable_nat_gateway    = true
  enable_flow_logs      = var.enable_flow_logs
  log_retention_days    = var.log_retention_days
  flow_logs_role_arn    = var.flow_logs_role_arn
}

# RDS Security Group
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  description = "Security group for RDS database"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "MySQL from ECS tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-rds-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Security Group
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-${var.environment}-ecs-"
  description = "Security group for ECS tasks"
  vpc_id      = module.vpc.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-ecs-sg"
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Module
module "s3" {
  source = "../modules/s3"

  project_name                   = var.project_name
  environment                    = var.environment
  create_terraform_state_bucket = false  # Already configured above
  log_retention_days            = var.log_retention_days
}

# SQS Module
module "sqs" {
  source = "../modules/sqs"

  project_name = var.project_name
  environment  = var.environment
}

# RDS Module
module "rds" {
  source = "../modules/rds"

  project_name                = var.project_name
  environment                 = var.environment
  db_engine                   = "mysql"
  db_engine_version           = "8.0"
  db_instance_class           = var.db_instance_class
  db_allocated_storage        = var.db_allocated_storage
  db_name                     = var.db_name
  db_username                 = var.db_username
  db_password                 = var.db_password
  db_family                   = "mysql8.0"
  db_subnet_group_name        = module.vpc.private_subnet_ids
  db_security_group_id        = aws_security_group.rds.id
  db_backup_retention_period  = 7
  db_backup_window            = "03:00-04:00"
  db_maintenance_window       = "sun:04:00-sun:05:00"
  db_storage_encrypted        = true
  db_max_connections          = var.db_max_connections
  enable_proxy                = var.enable_proxy
  proxy_role_arn              = var.proxy_role_arn
  db_secret_arn               = ""
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-cluster"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-${var.environment}-ecs-task-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-task-exec-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-${var.environment}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-task-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_iam_policy" "ecs_task_additional" {
  name        = "${var.project_name}-${var.environment}-ecs-task-additional"
  description = "Additional policies for ECS tasks"

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
          "${module.s3.receipts_bucket_arn}",
          "${module.s3.receipts_bucket_arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Resource = [
          module.sqs.ocr_queue_arn,
          module.sqs.validation_queue_arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_additional" {
  role       = aws_iam_role.ecs_task.name
  policy_arn = aws_iam_policy.ecs_task_additional.arn
}

# ECS Module
module "ecs" {
  source = "../modules/ecs"

  project_name                = var.project_name
  environment                 = var.environment
  aws_region                  = var.aws_region
  api_image                   = var.api_image
  ocr_worker_image           = var.ocr_worker_image
  validation_worker_image    = var.validation_worker_image
  db_endpoint                 = module.rds.db_host
  db_name                     = module.rds.db_name
  db_username                 = module.rds.db_username
  db_password                 = module.rds.db_password
  receipts_bucket_name        = module.s3.receipts_bucket_name
  ocr_queue_url              = module.sqs.ocr_queue_url
  validation_queue_url       = module.sqs.validation_queue_url
  alb_target_group_arn        = var.alb_target_group_arn
  ecs_cluster_id              = aws_ecs_cluster.main.id
  ecs_cluster_name            = aws_ecs_cluster.main.name
  ecs_task_execution_role_arn = aws_iam_role.ecs_task_execution.arn
  ecs_task_role_arn           = aws_iam_role.ecs_task.arn
  private_subnet_ids          = module.vpc.private_subnet_ids
  public_subnet_ids           = module.vpc.public_subnet_ids
  ecs_security_group_id       = aws_security_group.ecs_tasks.id
  secret_key                  = var.secret_key
  jwt_secret_key             = var.jwt_secret_key
  api_desired_count          = var.api_desired_count
  api_max_count              = var.api_max_count
  worker_desired_count       = var.worker_desired_count
  log_retention_days         = var.log_retention_days
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "public_subnet_ids" {
  value = module.vpc.public_subnet_ids
}

output "private_subnet_ids" {
  value = module.vpc.private_subnet_ids
}

output "receipts_bucket_name" {
  value = module.s3.receipts_bucket_name
}

output "receipts_bucket_arn" {
  value = module.s3.receipts_bucket_arn
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "ecs_cluster_id" {
  value = aws_ecs_cluster.main.id
}

output "db_endpoint" {
  value = module.rds.db_endpoint
}

output "db_host" {
  value = module.rds.db_host
}
