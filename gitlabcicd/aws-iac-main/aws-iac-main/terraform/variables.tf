# Defining Region
variable "aws_region" {
  default = "us-east-1"
}

# Defining CIDR Block for VPC
# Showing demo
variable "vpc_cidr" {
  default = "10.0.0.0/16"
}
