resource "aws_ecs_capacity_provider" "smollm" {
  name = "smollm-capacity-provider"

  auto_scaling_group_provider {
    auto_scaling_group_arn = aws_autoscaling_group.smollm.arn

    managed_scaling {
      status          = "ENABLED"
      target_capacity = 100

      minimum_scaling_step_size = 1
      maximum_scaling_step_size = 1

      instance_warmup_period = 180
    }

    managed_termination_protection = "DISABLED"
  }
}

resource "aws_ecs_cluster_capacity_providers" "smollm" {
  cluster_name = aws_ecs_cluster.smollm.name

  capacity_providers = [
    aws_ecs_capacity_provider.smollm.name
  ]

  default_capacity_provider_strategy {
    capacity_provider = aws_ecs_capacity_provider.smollm.name
    weight            = 1
  }
}