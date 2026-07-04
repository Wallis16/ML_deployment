#################################
# SECURITY GROUP - ALB
#################################

resource "aws_security_group" "alb" {
  name   = "smollm-alb-sg"
  vpc_id = data.aws_vpc.default.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

#################################
# ALB
#################################

resource "aws_lb" "smollm" {
  name               = "smollm-alb"
  load_balancer_type = "application"
  internal           = false
  idle_timeout       = 300

  security_groups = [aws_security_group.alb.id]
  subnets         = data.aws_subnets.default.ids
}

#################################
# TARGET GROUP
#################################

resource "aws_lb_target_group" "smollm" {
  name_prefix = "smol-"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "instance"

  health_check {
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  lifecycle {
    create_before_destroy = true
  }
}

#################################
# LISTENER
#################################

resource "aws_lb_listener" "smollm" {
  load_balancer_arn = aws_lb.smollm.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.smollm.arn
  }
}
