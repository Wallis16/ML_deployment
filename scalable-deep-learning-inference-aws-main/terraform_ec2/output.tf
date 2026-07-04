output "public_ip" {
  value = aws_instance.smollm.public_ip
}

output "instance_id" {
  value = aws_instance.smollm.id
}