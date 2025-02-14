# Provider configuration
# variables.tf
variable "ami" {
  type    = string
  default = "ami-0a07ff89aacad043e"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "sandboxes" {
  type    = list(string)
  default = ["d1","d2","d3"]
}

# main.tf
resource "aws_instance" "this" {
  ami           = var.ami
  instance_type = var.instance_type
  for_each      = toset(var.sandboxes)
   tags ={
    Name = "demo${each.value}" # for a set, each.value and each.key is the same
  }
}

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

# Launch Configuration for ASG
resource "aws_launch_configuration" "my_launch_config" {
  name          = "podASG"
  image_id      = var.ami
  instance_type = var.instance_type
  security_groups = [aws_security_group.allow_http.id]
  associate_public_ip_address = true
}

# Auto Scaling Group (ASG)
resource "aws_autoscaling_group" "my_asg" {
  launch_configuration = aws_launch_configuration.my_launch_config.id
  vpc_zone_identifier  = data.aws_subnets.default_subnets.ids
  desired_capacity     = 2
  max_size             = 3
  min_size             = 1

  tag {
    key                 = "Name"
    value               = "example-asg"
    propagate_at_launch = true
  }
}

# Application Load Balancer (ALB)
resource "aws_lb" "my_alb" {
  name               = "pre-pod"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.allow_http.id]
  subnets            = data.aws_subnets.default_subnets.ids
}

# ALB Target Group
resource "aws_lb_target_group" "my_target_group" {
  name     = "pre-poduat"
  port     = 80
  protocol = "HTTP"
  vpc_id   = data.aws_vpc.default.id
}

# ALB Listener
resource "aws_lb_listener" "my_listener" {
  load_balancer_arn = aws_lb.my_alb.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.my_target_group.arn
  }
}

# Attach ASG to ALB
resource "aws_autoscaling_attachment" "asg_attachment" {
  autoscaling_group_name = aws_autoscaling_group.my_asg.id
  lb_target_group_arn    = aws_lb_target_group.my_target_group.arn
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
  group_names = [aws_autoscaling_group.my_asg.name]
  notifications = [
    "autoscaling:EC2_INSTANCE_LAUNCH",
    "autoscaling:EC2_INSTANCE_TERMINATE",
    "autoscaling:EC2_INSTANCE_LAUNCH_ERROR",
    "autoscaling:EC2_INSTANCE_TERMINATE_ERROR",
  ]
  topic_arn = aws_sns_topic.example.arn
}
