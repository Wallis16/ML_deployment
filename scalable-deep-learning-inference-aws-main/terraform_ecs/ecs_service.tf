resource "aws_ecs_service" "smollm" {
  name            = "smollm-service"
  cluster         = aws_ecs_cluster.smollm.id
  task_definition = aws_ecs_task_definition.smollm.arn

  desired_count = 1

  capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.smollm.name
    weight            = 1
  }

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = 300

  #################################
  # LOAD BALANCER
  #################################

  load_balancer {
    target_group_arn = aws_lb_target_group.smollm.arn
    container_name   = "smollm"
    container_port   = 8000
  }

  depends_on = [
    aws_lb_listener.smollm,
    aws_ecs_cluster_capacity_providers.smollm
  ]

}
