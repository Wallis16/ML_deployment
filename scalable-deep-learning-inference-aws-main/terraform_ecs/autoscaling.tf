resource "aws_autoscaling_group" "smollm" {
  name = "smollm-asg"

  min_size         = 1
  desired_capacity = 1
  max_size         = 2

  protect_from_scale_in = false

  vpc_zone_identifier = [
    "subnet-0928aa9f914502ed0",
    "subnet-0fe7962cd007e7a53",
    "subnet-084e6444ef2b4f71c"
  ]

  launch_template {
    id      = aws_launch_template.smollm.id
    version = "$Default"

  }

  instance_refresh {
    strategy = "Rolling"

    preferences {
      min_healthy_percentage = 0
    }
  }

  tag {
    key                 = "Name"
    value               = "smollm-gpu"
    propagate_at_launch = true
  }
}
