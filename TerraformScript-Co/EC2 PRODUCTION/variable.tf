variable "aws_region" {
  description = "AWS region to launch resources"
  default     = "ap-south-1"
}

variable "instance_type" {
  description = "Instance type for EC2 instances"
  default     = "t2.micro"
}

variable "vpc_id" {
  description = "VPC ID where resources will be created"
  type        = string
  default     = null  # If not provided, the default VPC will be used
}

variable "subnet_ids" {
  description = "List of Subnet IDs where resources will be launched"
  type        = list(string)
  default     = []  # If not provided, default subnets will be used
}
