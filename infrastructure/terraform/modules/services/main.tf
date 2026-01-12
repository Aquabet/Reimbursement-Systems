# Microservice-specific ECS Service Module

resource "aws_ecs_cluster" "microservices" {
  name = "${var.project_name}-${var.environment}-microservices"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-microservices"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Report Service
resource "aws_ecs_task_definition" "report_service" {
  family                   = "${var.project_name}-${var.environment}-report-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.report_service_cpu
  memory                   = var.report_service_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn           = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "report-service"
      image = var.report_service_image

      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DATABASE_URL"
          value = "mysql://${var.db_username}:${var.db_password}@${var.db_endpoint}/${var.db_name}"
        },
        {
          name  = "SECRET_KEY"
          value = var.secret_key
        },
        {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        },
        {
          name  = "S3_BUCKET_NAME"
          value = var.receipts_bucket_name
        },
        {
          name  = "OCR_QUEUE_URL"
          value = var.ocr_queue_url
        },
        {
          name  = "VALIDATION_QUEUE_URL"
          value = var.validation_queue_url
        },
        {
          name  = "FLASK_ENV"
          value = var.environment
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}/${var.environment}/report-service"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

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
    Name        = "${var.project_name}-${var.environment}-report-service-task"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_service" "report_service" {
  name            = "${var.project_name}-${var.environment}-report-service"
  cluster         = aws_ecs_cluster.microservices.id
  task_definition = aws_ecs_task_definition.report_service.arn
  launch_type     = "FARGATE"
  desired_count   = var.report_service_desired_count

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.report_service_target_group_arn
    container_name   = "report-service"
    container_port   = 5000
  }

  health_check_grace_period_seconds = 300

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-report-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Receipt Service
resource "aws_ecs_task_definition" "receipt_service" {
  family                   = "${var.project_name}-${var.environment}-receipt-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.receipt_service_cpu
  memory                   = var.receipt_service_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn           = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "receipt-service"
      image = var.receipt_service_image

      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DATABASE_URL"
          value = "mysql://${var.db_username}:${var.db_password}@${var.db_endpoint}/${var.db_name}"
        },
        {
          name  = "SECRET_KEY"
          value = var.secret_key
        },
        {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        },
        {
          name  = "S3_BUCKET_NAME"
          value = var.receipts_bucket_name
        },
        {
          name  = "OCR_QUEUE_URL"
          value = var.ocr_queue_url
        },
        {
          name  = "VALIDATION_QUEUE_URL"
          value = var.validation_queue_url
        },
        {
          name  = "FLASK_ENV"
          value = var.environment
        },
        {
          name  = "REVIEW_SERVICE_URL"
          value = "http://${aws_ecs_service.review_service.name}.${var.environment}.local:5000"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}/${var.environment}/receipt-service"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

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
    Name        = "${var.project_name}-${var.environment}-receipt-service-task"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_service" "receipt_service" {
  name            = "${var.project_name}-${var.environment}-receipt-service"
  cluster         = aws_ecs_cluster.microservices.id
  task_definition = aws_ecs_task_definition.receipt_service.arn
  launch_type     = "FARGATE"
  desired_count   = var.receipt_service_desired_count

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.receipt_service.arn
    container_name   = "receipt-service"
    container_port   = 5000
  }

  health_check_grace_period_seconds = 300

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-receipt-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Review Service
resource "aws_ecs_task_definition" "review_service" {
  family                   = "${var.project_name}-${var.environment}-review-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.review_service_cpu
  memory                   = var.review_service_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn           = var.task_role_arn

  container_definitions = jsonencode([
    {
      name  = "review-service"
      image = var.review_service_image

      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "DATABASE_URL"
          value = "mysql://${var.db_username}:${var.db_password}@${var.db_endpoint}/${var.db_name}"
        },
        {
          name  = "SECRET_KEY"
          value = var.secret_key
        },
        {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        },
        {
          name  = "FLASK_ENV"
          value = var.environment
        },
        {
          name  = "RECEIPT_SERVICE_URL"
          value = "http://${aws_ecs_service.receipt_service.name}.${var.environment}.local:5000"
        },
        {
          name  = "REPORT_SERVICE_URL"
          value = "http://${aws_ecs_service.report_service.name}.${var.environment}.local:5000"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/${var.project_name}/${var.environment}/review-service"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }

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
    Name        = "${var.project_name}-${var.environment}-review-service-task"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_ecs_service" "review_service" {
  name            = "${var.project_name}-${var.environment}-review-service"
  cluster         = aws_ecs_cluster.microservices.id
  task_definition = aws_ecs_task_definition.review_service.arn
  launch_type     = "FARGATE"
  desired_count   = var.review_service_desired_count

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.ecs_security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.review_service.arn
    container_name   = "review-service"
    container_port   = 5000
  }

  health_check_grace_period_seconds = 300

  deployment_maximum_percent         = 200
  deployment_minimum_healthy_percent = 100

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-review-service"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Target Groups for microservices
resource "aws_lb_target_group" "receipt_service" {
  name     = "${var.project_name}-${var.environment}-receipt-service"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-receipt-service-tg"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_lb_target_group" "review_service" {
  name     = "${var.project_name}-${var.environment}-review-service"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-review-service-tg"
    Environment = var.environment
    Project     = var.project_name
  }
}
