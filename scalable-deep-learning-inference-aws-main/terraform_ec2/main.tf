terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

#################################
# Deep Learning AMI GPU
#################################

data "aws_ami" "deep_learning_gpu" {
  owners      = ["amazon"]
  most_recent = true

  filter {
    name = "name"
    values = [
      "Deep Learning OSS Nvidia Driver AMI GPU PyTorch*"
    ]
  }
}

#################################
# IAM ROLE
#################################

resource "aws_iam_role" "ec2_role" {
  name = "smollm-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecr_readonly" {
  role       = aws_iam_role.ec2_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "profile" {
  name = "smollm-profile"
  role = aws_iam_role.ec2_role.name
}

#################################
# Security Group
#################################

resource "aws_security_group" "smollm" {
  name = "smollm-sg"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
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
# EC2
#################################

resource "aws_instance" "smollm" {
  ami                    = data.aws_ami.deep_learning_gpu.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.smollm.id]

  iam_instance_profile = aws_iam_instance_profile.profile.name

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
  }

  user_data = templatefile("${path.module}/userdata.sh", {
    ecr_repository = var.ecr_repository
    region         = var.aws_region
  })

  tags = {
    Name = "smollm-gpu"
  }
}