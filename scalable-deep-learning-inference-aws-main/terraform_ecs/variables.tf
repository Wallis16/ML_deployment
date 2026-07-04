variable "aws_region" {
  default = "us-east-1"
}

variable "key_name" {
  description = "Nome da key pair EC2"
  default     = "<>"
}

variable "ecr_repository" {
  description = "URI completa da imagem no ECR"
  default     = "<>.dkr.ecr.us-east-1.amazonaws.com/smollm-inference"
}

variable "instance_type" {
  description = "Tipo da instância GPU usada no ASG"
  default     = "g4dn.xlarge"
}

variable "autoscaling_strategy" {
  description = "Estratégia de Auto Scaling do ECS"
  type        = string
  default     = "cpu"

  validation {
    condition     = contains(["cpu", "latency"], var.autoscaling_strategy)
    error_message = "autoscaling_strategy deve ser 'cpu' ou 'latency'."
  }
}