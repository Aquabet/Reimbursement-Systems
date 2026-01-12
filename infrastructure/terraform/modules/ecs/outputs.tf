output "cloudwatch_log_group_api" {
  value = aws_cloudwatch_log_group.api.name
}

output "cloudwatch_log_group_ocr_worker" {
  value = aws_cloudwatch_log_group.ocr_worker.name
}

output "cloudwatch_log_group_validation_worker" {
  value = aws_cloudwatch_log_group.validation_worker.name
}

output "ecs_service_api_name" {
  value = aws_ecs_service.api.name
}

output "ecs_service_ocr_worker_name" {
  value = aws_ecs_service.ocr_worker.name
}

output "ecs_service_validation_worker_name" {
  value = aws_ecs_service.validation_worker.name
}
