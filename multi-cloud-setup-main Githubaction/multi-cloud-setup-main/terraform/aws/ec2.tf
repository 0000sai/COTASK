# EC2 Instance
resource "aws_instance" "app_server" {
  count = var.ec2_instance_count

  ami           = var.ec2_ami
  instance_type = var.ec2_instance_type
  subnet_id     = module.vpc.private_subnets[count.index % length(module.vpc.private_subnets)]

  vpc_security_group_ids = [aws_security_group.app_sg.id]

  root_block_device {
    volume_size = 20
    encrypted   = true
  }

  tags = merge(
    var.common_tags,
    {
      Name = "app-server-${count.index + 1}"
    }
  )
}

# Security Group
resource "aws_security_group" "app_sg" {
  name_prefix = "app-sg"
  vpc_id      = module.vpc.vpc_id

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

  tags = var.common_tags
}
