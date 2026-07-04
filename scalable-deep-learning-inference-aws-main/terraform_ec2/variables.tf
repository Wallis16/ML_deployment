variable "aws_region" {
  default = "us-east-1"
}

variable "key_name" {
  description = "<>.pem"
}

variable "ecr_repository" {
  default = "<>.dkr.ecr.us-east-1.amazonaws.com/smollm-inference"
}

variable "instance_type" {
  default = "g4dn.xlarge"
}