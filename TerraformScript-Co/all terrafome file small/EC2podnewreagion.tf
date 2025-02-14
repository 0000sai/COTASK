provider "aws" {
  region = "ap-south-2"  # Change this to your desired region
}

# Variables for VPC, Subnets, and other configurations
variable "vpc_id" {
  description = "The ID of the VPC"
  type        = string
  default     = "vpc-0c635ee4510147f94"
}

variable "subnets" {
  description = "A list of subnets for the ALB and EC2 instances"
  type        = list(string)
  default     = ["subnet-09a8c8ec376000861", "subnet-0d5cda54df1cf295d"]  # Replace with default subnets
}

variable "domain_name" {
  description = "The domain name for Route 53"
  type        = string
  default     = "demotask.com"
}

variable "hosted_zone_id" {
  description = "The Route 53 Hosted Zone ID"
  type        = string
  default     = "Z00683973FZBOOBXQBBX4"  # Replace with a default Hosted Zone ID
}

variable "instance_type" {
  description = "The instance type for the EC2 instances"
  type        = string
  default     = "t3.micro"
}

# Security Group for EC2 instances and ALB
resource "aws_security_group" "web_sg" {
  name        = "web-sg"
  description = "Allow HTTP and HTTPS traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "web-sg"
  }
}

# Launch Template for Auto Scaling Group
resource "aws_launch_template" "web_lt" {
  name_prefix   = "web-template"
  image_id      = "ami-068daf89d1895ab7b"  # Replace with your preferred AMI ID
  instance_type = var.instance_type

  network_interfaces {
    security_groups = [aws_security_group.web_sg.id]
  }

  lifecycle {
    create_before_destroy = true
  }

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "web-server"
    }
  }
}

# Auto Scaling Group
resource "aws_autoscaling_group" "web_asg" {
  vpc_zone_identifier = var.subnets
  launch_template {
    id      = aws_launch_template.web_lt.id
    version = "$Latest"
  }

  min_size           = 1
  max_size           = 3
  desired_capacity   = 2
  health_check_type  = "ELB"
  health_check_grace_period = 300

  tag {
    key                 = "Name"
    value               = "web-server"
    propagate_at_launch = true
  }
}

# Application Load Balancer
resource "aws_lb" "web_lb" {
  name               = "web-lb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.web_sg.id]
  subnets            = var.subnets

  enable_deletion_protection = true

  tags = {
    Name = "web-alb"
  }
}

# Target Group for the ALB
resource "aws_lb_target_group" "web_lb" {
  name     = "web-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
  }

  tags = {
    Name = "web-tg"
  }
}

# Listener for the ALB
resource "aws_lb_listener" "web_etb" {
  load_balancer_arn = aws_lb.web_lb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.web_lb.arn
}
}
# Route 53 Record
resource "aws_route53_record" "web_record" {
  zone_id = var.hosted_zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.web_lb.dns_name
    zone_id                = aws_lb.web_lb.zone_id
    evaluate_target_health = true
  }
}

# Data source to get the instance IDs in the Auto Scaling Group
data "aws_instances" "web_asg_instances" {
  filter {
    name   = "tag:Name"
    values = ["web-server"]
  }

  filter {
    name   = "instance-state-name"
    values = ["running"]
  }
}

#Outputs
output "alb_dns_name" {
  value = aws_lb.web_lb.dns_name
}

output "asg_instance_ids" {
  value = data.aws_instances.web_asg_instances.ids
}


