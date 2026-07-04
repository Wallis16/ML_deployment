#################################
# ECS STEP SCALING (LATENCY)
#################################

resource "aws_appautoscaling_policy" "scale_out_latency" {

  count = var.autoscaling_strategy == "latency" ? 1 : 0

  name        = "smollm-scale-out-latency"
  policy_type = "StepScaling"

  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  resource_id        = aws_appautoscaling_target.ecs.resource_id

  step_scaling_policy_configuration {

    adjustment_type         = "ChangeInCapacity"
    cooldown                = 120
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_lower_bound = 0
      scaling_adjustment          = 1
    }
  }
}

resource "aws_appautoscaling_policy" "scale_in_latency" {

  count = var.autoscaling_strategy == "latency" ? 1 : 0

  name        = "smollm-scale-in-latency"
  policy_type = "StepScaling"

  service_namespace  = aws_appautoscaling_target.ecs.service_namespace
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  resource_id        = aws_appautoscaling_target.ecs.resource_id

  step_scaling_policy_configuration {

    adjustment_type         = "ChangeInCapacity"
    cooldown                = 300
    metric_aggregation_type = "Average"

    step_adjustment {
      metric_interval_upper_bound = 0
      scaling_adjustment          = -1
    }
  }
}

#################################
# CLOUDWATCH ALARM - SCALE OUT
#################################

resource "aws_cloudwatch_metric_alarm" "high_latency" {

  count = var.autoscaling_strategy == "latency" ? 1 : 0

  alarm_name = "smollm-high-latency"

  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1

  metric_name = "TargetResponseTime"
  namespace   = "AWS/ApplicationELB"

  period    = 30
  statistic = "Average"

  threshold = 4

  dimensions = {
    LoadBalancer = aws_lb.smollm.arn_suffix
    TargetGroup  = aws_lb_target_group.smollm.arn_suffix
  }

  alarm_actions = [
    aws_appautoscaling_policy.scale_out_latency[0].arn
  ]
}

#################################
# CLOUDWATCH ALARM - SCALE IN
#################################

resource "aws_cloudwatch_metric_alarm" "low_latency" {

  count = var.autoscaling_strategy == "latency" ? 1 : 0

  alarm_name = "smollm-low-latency"

  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 5

  metric_name = "TargetResponseTime"
  namespace   = "AWS/ApplicationELB"

  period    = 60
  statistic = "Average"

  threshold = 0.5

  dimensions = {
    LoadBalancer = aws_lb.smollm.arn_suffix
    TargetGroup  = aws_lb_target_group.smollm.arn_suffix
  }

  alarm_actions = [
    aws_appautoscaling_policy.scale_in_latency[0].arn
  ]
}