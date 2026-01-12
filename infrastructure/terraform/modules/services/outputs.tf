output "report_service_name" {
  value = aws_ecs_service.report_service.name
}

output "receipt_service_name" {
  value = aws_ecs_service.receipt_service.name
}

output "review_service_name" {
  value = aws_ecs_service.review_service.name
}

output "report_service_cluster" {
  value = aws_ecs_cluster.microservices.name
}

output "receipt_service_target_group_arn" {
  value = aws_lb_target_group.receipt_service.arn
}

output "review_service_target_group_arn" {
  value = aws_lb_target_group.review_service.arn
}
