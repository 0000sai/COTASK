provider "aws" {
  region = "ap-south-1"
}

data "aws_region" "current" {}

# Variables
variable "vpc_id" {
  description = "VpcId of your existing Virtual Private Cloud (VPC)"
  type        = string
  default     = "vpc-0e1c42289714e2c6a"
}

variable "subnets" {
  description = "The list of SubnetIds in your Virtual Private Cloud (VPC)"
  type        = list(string)
  default  = ["subnet-0d2602fc52bd79ee6","subnet-015e2b43db3059d17"]
}

variable "instance_type" {
  description = "WebServer EC2 instance type"
  type        = string
  default     = "t2.micro"
  validation {
    condition     = contains(["t1.micro", "t2.nano", "t2.micro", "t2.small", "t2.medium", "t2.large", "m1.small", "m1.medium", "m1.large"], var.instance_type)
    error_message = "must be a valid EC2 instance type."
  }
}

variable "operator_email" {
  description = "Email address to notify if there are any scaling operations"
  type        = string
  default     = "kvs100101@gmail.com"
  validation {
    condition     = can(regex("^([a-zA-Z0-9_\\-\\.]+)@(([a-zA-Z0-9\\-]+\\.)+)([a-zA-Z]{2,4}|[0-9]{1,3})(\\]?)$", var.operator_email))
    error_message = "must be a valid email address."
  }
}

variable "key_name" {
  description = "The EC2 Key Pair to allow SSH access to the instances"
  type        = string
  default     = "terrafonme test"
}

variable "ssh_location" {
  description = "The IP address range that can be used to SSH to the EC2 instances"
  type        = string
  default     = "0.0.0.0/0"
}

# Locals (for mappings and lookup)
locals {
  region_amis = {
    "us-east-1"      = "ami-0e86e20dae9224db8"
    "us-west-2"      = "ami-085f9c64a9b75eed5"
    "us-west-1"      = "ami-0d53d72369335a9d6"
    "eu-west-1"      = "ami-03cc8375791cb8bcf"
    # Add the remaining mappings as required
  }
}

# Data Sources (used for example lookup)
data "aws_ami" "example" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# SNS Topic for notification
resource "aws_sns_topic" "notification_topic" {
  name = "notification_topic"
}

resource "aws_sns_topic_subscription" "topic_subscription" {
  topic_arn = aws_sns_topic.notification_topic.arn
  protocol  = "email"
  endpoint  = var.operator_email
}

# Launch Configuration
resource "aws_launch_configuration" "web_server_launch_configuration" {
  name          = "web_server_launch_configuration"
  image_id      = lookup(local.region_amis, data.aws_region.current.name, local.region_amis["us-east-1"])
  instance_type = var.instance_type
  key_name      = var.key_name
  user_data     = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl enable httpd
    systemctl start httpd
    echo "<h1>Congratulations, you have successfully launched the AWS CloudFormation sample.</h1>" > /var/www/html/index.html
  EOF

  iam_instance_profile = "arn:aws:iam::235343540751:instance-profile/ec2adminaccess"
  security_groups      = [aws_security_group.instance_sg.id]
}

# Auto Scaling Group
resource "aws_autoscaling_group" "web_server_group" {
  desired_capacity     = 1
  max_size             = 3
  min_size             = 1
  vpc_zone_identifier  = var.subnets
  launch_configuration = aws_launch_configuration.web_server_launch_configuration.id
  target_group_arns    = [aws_lb_target_group.alb_target_group.arn]

  tag {
    key                 = "Name"
    value               = "WebServer"
    propagate_at_launch = true
  }
}

# Scaling Policies
resource "aws_autoscaling_policy" "scale_up" {
  name                   = "scale_up_policy"
  scaling_adjustment      = 1
  adjustment_type         = "ChangeInCapacity"
  cooldown               = 60
  autoscaling_group_name  = aws_autoscaling_group.web_server_group.name
}

resource "aws_autoscaling_policy" "scale_down" {
  name                   = "scale_down_policy"
  scaling_adjustment      = -1
  adjustment_type         = "ChangeInCapacity"
  cooldown               = 60
  autoscaling_group_name  = aws_autoscaling_group.web_server_group.name
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu_alarm_high" {
  alarm_name          = "high_cpu_alarm"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 90

  alarm_actions = [aws_autoscaling_policy.scale_up.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web_server_group.name
  }
}

resource "aws_cloudwatch_metric_alarm" "cpu_alarm_low" {
  alarm_name          = "low_cpu_alarm"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 70

  alarm_actions = [aws_autoscaling_policy.scale_down.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web_server_group.name
  }
}

# Load Balancer
resource "aws_lb" "application_load_balancer" {
  name               = "devops"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.lb_sg.id]
  subnets            = var.subnets
}

resource "aws_lb_listener" "http_listener" {
  load_balancer_arn = aws_lb.application_load_balancer.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.alb_target_group.arn
  }
}

resource "aws_lb_target_group" "alb_target_group" {
  name     = "dev"
  port     = 80
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    interval            = 30
    timeout             = 5
    healthy_threshold   = 3
    unhealthy_threshold = 5
  }
}

# Security Groups
resource "aws_security_group" "instance_sg" {
  vpc_id      = var.vpc_id
  description = "Enable SSH access and HTTP from the load balancer only"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_location]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    security_groups = [aws_lb.application_load_balancer.security_groups]
  }
}

resource "aws_security_group" "lb_sg" {
  vpc_id = var.vpc_id

  egress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Outputs
output "alb_dns" {
  description = "The DNS name of the Application Load Balancer"
  value       = aws_lb.application_load_balancer.dns_name
}
