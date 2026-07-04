resource "aws_cloudwatch_log_group" "smollm" {
  name              = "/ecs/smollm"
  retention_in_days = 7
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "smollm-ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_ecs_task_definition" "smollm" {
  family                   = "smollm"
  requires_compatibilities = ["EC2"]
  network_mode             = "bridge"

  cpu    = 1024
  memory = 8192

  execution_role_arn = aws_iam_role.ecs_task_execution_role.arn

  container_definitions = jsonencode([
    {
      name      = "smollm"
      image     = var.ecr_repository
      essential = true

      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]

      environment = [
        {
          name  = "MODEL_ID"
          value = "HuggingFaceTB/SmolLM2-360M-Instruct"
        },
        {
          name  = "SMOLLM_MOCK"
          value = "0"
        }
      ]

      resourceRequirements = [
        {
          type  = "GPU"
          value = "1"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-region        = var.aws_region
          awslogs-group         = aws_cloudwatch_log_group.smollm.name
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}
