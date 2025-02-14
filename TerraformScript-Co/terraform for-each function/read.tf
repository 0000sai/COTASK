# Fetch the default VPC
data "aws_vpc" "default" {
  default = true
}

# Fetch all subnets within the default VPC
data "aws_subnets" "default_subnets" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group for EC2 instances allowing HTTP traffic
resource "aws_security_group" "allow_http" {
  name        = "pre-podscaling"
  description = "Allow HTTP traffic"

  ingress {
    from_port   = 80
    to_port     = 80
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

# Launch Configuration for ASG (with for_each for multiple sandboxes)
resource "aws_launch_configuration" "my_launch_config" {
  for_each        = toset(var.sandboxes)  # Loop through each sandbox
  name            = "podASG-${each.key}"  # Name is unique for each sandbox
  image_id        = var.ami
  instance_type   = var.instance_type
  security_groups = [aws_security_group.allow_http.id]
  associate_public_ip_address = true
}

# Auto Scaling Group (ASG) for each sandbox
resource "aws_autoscaling_group" "my_asg" {
  for_each              = aws_launch_configuration.my_launch_config  # Reference to Launch Config
  launch_configuration  = each.value.id
  vpc_zone_identifier   = data.aws_subnets.default_subnets.ids
  desired_capacity      = 2
  max_size              = 3
  min_size              = 1

  tag {
    key                 = "Name"
    value               = "${each.key}-example-asg"
    propagate_at_launch = true
  }
}

# Application Load Balancer (ALB) for each sandbox
resource "aws_lb" "my_alb" {
  for_each            = toset(var.sandboxes)
  name                = "pre-pod-${each.key}"  # Unique ALB name for each sandbox
  internal            = false
  load_balancer_type  = "application"
  security_groups     = [aws_security_group.allow_http.id]
  subnets             = data.aws_subnets.default_subnets.ids
}

# ALB Target Group for each sandbox
resource "aws_lb_target_group" "my_target_group" {
  for_each = toset(var.sandboxes)
  name     = "pre-pod-${each.key}-target"
  port     = 80
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id
}

# ALB Listener for each sandbox
resource "aws_lb_listener" "my_listener" {
  for_each           = aws_lb.my_alb
  load_balancer_arn  = each.value.arn
  port               = 80
  protocol           = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.my_target_group[each.key].arn
  }
}

# Attach ASG to ALB Target Group for each sandbox
resource "aws_autoscaling_attachment" "asg_attachment" {
  for_each               = aws_autoscaling_group.my_asg  # Loop through each ASG
  autoscaling_group_name = each.value.id
  lb_target_group_arn    = aws_lb_target_group.my_target_group[each.key].arn
}

# SNS Topic for Auto Scaling notifications
resource "aws_sns_topic" "example" {
  name = "auto-scaling-notifications"
}

# SNS Topic Subscription (Email)
resource "aws_sns_topic_subscription" "example" {
  topic_arn = aws_sns_topic.example.arn
  protocol  = "email"
  endpoint  = "kvs.vishnusai@gmail.com"  # Replace with your email address
}

# Auto Scaling Notification for SNS
resource "aws_autoscaling_notification" "example" {
  for_each     = aws_autoscaling_group.my_asg  # For each ASG
  group_names  = [each.value.name]
  notifications = [
    "autoscaling:EC2_INSTANCE_LAUNCH",
    "autoscaling:EC2_INSTANCE_TERMINATE",
    "autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
    "autoscaling:EC2_INSTANCE_TERMINATE_ERROR",
  ]
  topic_arn = aws_sns_topic.example.arn
}

root@ip-172-31-44-74:/home/ubuntu/new# vi variables.tf
root@ip-172-31-44-74:/home/ubuntu/new# cat variables.tf
variable "ami" {
  type    = string
  default = "ami-05d2438ca66594916"
}

variable "instance_type" {
  type    = string
  default = "t2.micro"
}

variable "sandboxes" {
  type    = list(string)
  default = ["d1","d2","d3"]
}
