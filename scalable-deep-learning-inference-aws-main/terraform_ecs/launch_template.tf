resource "aws_security_group" "ec2" {
  name   = "smollm-ec2-sg"
  vpc_id = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    # Em produção, restrinja o acesso SSH ao seu IP.
  }

  ingress {
    description     = "App from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "smollm-ec2-sg"
  }
}

resource "aws_launch_template" "smollm" {
  name_prefix            = "smollm-"
  image_id               = data.aws_ssm_parameter.ecs_gpu_ami.value
  instance_type          = "g4dn.xlarge"
  update_default_version = true

  iam_instance_profile {
    name = aws_iam_instance_profile.profile.name
  }

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.ec2.id]
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash

    cat <<ECS_CONFIG >/etc/ecs/ecs.config
    ECS_CLUSTER=${aws_ecs_cluster.smollm.name}
    ECS_ENABLE_GPU_SUPPORT=true
    ECS_ENABLE_SPOT_INSTANCE_DRAINING=true
    ECS_CONFIG
  EOF
  )

  monitoring {
    enabled = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 2
  }

  tag_specifications {
    resource_type = "instance"

    tags = {
      Name = "smollm-gpu"
    }
  }

  tag_specifications {
    resource_type = "volume"

    tags = {
      Name = "smollm-gpu"
    }
  }
}