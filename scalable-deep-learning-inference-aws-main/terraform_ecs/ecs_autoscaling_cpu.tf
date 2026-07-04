resource "aws_appautoscaling_target" "ecs" {

  max_capacity = 2
  min_capacity = 1

  resource_id        = "service/${aws_ecs_cluster.smollm.name}/${aws_ecs_service.smollm.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {

  count = var.autoscaling_strategy == "cpu" ? 1 : 0

  name = "smollm-cpu"

  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  resource_id        = aws_appautoscaling_target.ecs.resource_id

  policy_type = "TargetTrackingScaling"

  target_tracking_scaling_policy_configuration {

    target_value = 70

    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }

    scale_in_cooldown  = 120
    scale_out_cooldown = 60
  }
}