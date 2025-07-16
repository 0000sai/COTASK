variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "ec2_instance_count" {
  description = "Number of EC2 instances"
  type        = number
  default     = 2
}

variable "ec2_instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "ec2_ami" {
  description = "AMI ID for EC2 instances"
  type        = string
  default     = "ami-0c55b159cbfafe1f0" # Amazon Linux 2
}

variable "eks_cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "main-cluster"
}

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS cluster"
  type        = string
  default     = "1.27"
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "Production"
    Project     = "Multi-Cloud-Setup"
    ManagedBy   = "Terraform"
  }
}
