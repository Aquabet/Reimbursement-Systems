terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Data source to get the latest recommended Amazon Linux 2023 AMI
data "aws_ssm_parameter" "alb_target_group_arn" {
  name = "/${var.project_name}/${var.environment}/alb/target-group-arn"
}

# CloudWatch Log Group for API service
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}/${var.environment}/api"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for OCR Worker
resource "aws_cloudwatch_log_group" "ocr_worker" {
  name              = "/ecs/${var.project_name}/${var.environment}/ocr-worker"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-worker-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Log Group for Validation Worker
resource "aws_cloudwatch_log_group" "validation_worker" {
  name              = "/ecs/${var.project_name}/${var.environment}/validation-worker"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-validation-worker-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Task Definition
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-${var.environment}-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "api"
      image = var.api_image

      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.api.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      environment = [
        {
          name  = "DATABASE_URL"
          value = "mysql+pymysql://${var.db_username}:${urlencode(var.db_password)}@${var.db_endpoint}/${var.db_name}"
        },
        {
          name  = "STORAGE_TYPE"
          value = "s3"
        },
        {
          name  = "S3_BUCKET_NAME"
          value = var.receipts_bucket_name
        },
        {
          name  = "SQS_QUEUE_URL"
          value = var.ocr_queue_url
        },
        {
          name  = "SQS_VALIDATION_QUEUE_URL"
          value = var.validation_queue_url
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "MCP_BASE_URL"
          value = "http://localhost:8080"  # In production, use actual MCP service URL
        },
        {
          name  = "SECRET_KEY"
          value = var.secret_key
        },
        {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        }
      ]

      secrets = var.enable_secrets_manager ? [
        {
          name      = "DB_PASSWORD"
          valueFrom = "${aws_secretsmanager_secret.db_password.arn}::password::"
        }
      ] : []

      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:5000/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
    }
  ])

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-task"
    Environment = var.environment
    Project     = var.project_name
  }
}

# OCR Worker Task Definition
resource "aws_ecs_task_definition" "ocr_worker" {
  family                   = "${var.project_name}-${var.environment}-ocr-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "ocr-worker"
      image = var.ocr_worker_image

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ocr_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      environment = [
        {
          name  = "DATABASE_URL"
          value = "mysql+pymysql://${var.db_username}:${urlencode(var.db_password)}@${var.db_endpoint}/${var.db_name}"
        },
        {
          name  = "SQS_QUEUE_URL"
          value = var.ocr_queue_url
        },
        {
          name  = "SQS_VALIDATION_QUEUE_URL"
          value = var.validation_queue_url
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "MCP_BASE_URL"
          value = "http://localhost:8080"  # In production, use actual MCP service URL
        }
      ]
    }
  ])

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-worker-task"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Validation Worker Task Definition
resource "aws_ecs_task_definition" "validation_worker" {
  family                   = "${var.project_name}-${var.environment}-validation-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = var.ecs_task_execution_role_arn
  task_role_arn           = var.ecs_task_role_arn

  container_definitions = jsonencode([
    {
      name  = "validation-worker"
      image = var.validation_worker_image

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.validation_worker.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

      environment = [
        {
          name  = "DATABASE_URL"
          value = "mysql+pymysql://${var.db_username}:${urlencode(var.db_password)}@${var.db_endpoint}/${var.db_name}"
        },
        {
          name  = "SQS_VALIDATION_QUEUE_URL"
          value = var.validation_queue_url
        },
        {
          name  = "AWS_REGION"
          value = var.aws_region
        }
      ]
    }
  ])

  tags = {
    Name        = "${var.project_name}-${var.environment}-validation-worker-task"
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Service
resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-${var.environment}-api"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = data.aws_ssm_parameter.alb_target_group_arn.value
    container_name   = "api"
    container_port   = 5000
  }

  health_check_grace_period_seconds = 60

  depends_on = [aws_ecs_task_definition.api]

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# OCR Worker Service
resource "aws_ecs_service" "ocr_worker" {
  name            = "${var.project_name}-${var.environment}-ocr-worker"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.ocr_worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  # Ensure workers don't run on the same host (not needed for Fargate, but good practice)
  scheduling_strategy = "REPLICA"

  depends_on = [aws_ecs_task_definition.ocr_worker]

  tags = {
    Name        = "${var.project_name}-${var.environment}-ocr-worker-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Validation Worker Service
resource "aws_ecs_service" "validation_worker" {
  name            = "${var.project_name}-${var.environment}-validation-worker"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.validation_worker.arn
  desired_count   = var.worker_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  scheduling_strategy = "REPLICA"

  depends_on = [aws_ecs_task_definition.validation_worker]

  tags = {
    Name        = "${var.project_name}-${var.environment}-validation-worker-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Auto Scaling for API Service
resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_count
  min_capacity       = var.api_desired_count
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.api]
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.project_name}-${var.environment}-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}

resource "aws_appautoscaling_policy" "api_memory" {
  name               = "${var.project_name}-${var.environment}-api-memory"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 80
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
  }
}

# Secrets Manager for sensitive data (optional)
resource "aws_secretsmanager_secret" "db_password" {
  count = var.enable_secrets_manager ? 1 : 0

  name                    = "${var.project_name}-${var.environment}-db-password"
  description            = "Database password for ${var.project_name} ${var.environment}"
  recovery_window_in_days = 7

  tags = {
    Name        = "${var.project_name}-${var.environment}-db-password"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "db_password" {
  count = var.enable_secrets_manager ? 1 : 0

  secret_id     = aws_secretsmanager_secret.db_password[0].id
  secret_string = jsonencode({
    password = var.db_password
  })
}
