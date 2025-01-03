#This script is creating necessary infra with the necessary EC2 instances (Ubuntu or RHEL8)
#and ECR for Gitlab CI/CD
#
# For using ssh keys in this script we need to do:
#
# Go to the ssh dir and generate keys:
# ssh-keygen -t rsa -b 2048

#############################
# Provider
#############################

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 3.0"
    }
  }
}

provider "aws" {
  region = var.region
}

#############################
# Data config
#############################

# Take the data about default VPC
data "aws_vpc" "default" {
  default = true
}

# Tahe the data about default Subnets
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
  filter {
    name   = "default-for-az"
    values = ["true"]
  }

}

# Take the data about RHEL8 AMI
data "aws_ami" "rhel8" {
  most_recent = true
  filter {
    name   = "name"
    values = ["RHEL-8*HVM-*Hourly*"]
  }
  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
  filter {
    name   = "state"
    values = ["available"]
  }
  owners = ["309956199498"] # Red Hat
}

# Take the data about Ubuntu AMI
data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"] # Ubuntu
}

#############################
# SSH key
#############################

# Creation of ssh key:
# ssh-keygen -t rsa -b 4096 -f gitlab_runner

# Variable for ssh dir.
variable "ssh_dir" {
  type    = string
  default = "~/.ssh"
}

# Read the public key from the local SSH directory
data "local_file" "public_key" {
  filename = "${pathexpand(var.ssh_dir)}/gitlab_runner.pub"
}

# Create the key pair in AWS
resource "aws_key_pair" "ssh_key" {
  key_name   = "gitlab-runner-ssh-key"
  public_key = data.local_file.public_key.content
}

#############################
# ECR
#############################

resource "aws_ecr_repository" "repo" {
  name                 = "nginx"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

#############################
# EC2 instance
#############################

# RHEL8 EC2 instance
resource "aws_instance" "RHEL8_instance" {
  count                  = var.count_rhel_instances
  ami                    = data.aws_ami.rhel8.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.ssh_key.key_name
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2profile.name

  tags = {
    Name  = "Server_RHEL8_${count.index + 1}"
    Owner = "Gitlab"
  }
  provisioner "file" {
    source      = "scripts/docker_aws_install_rhel.sh"
    destination = "/tmp/docker_aws_install_rhel.sh"
  }
  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/docker_aws_install_rhel.sh",
      "sudo /tmp/docker_aws_install_rhel.sh"
    ]
  }
  connection {
    type        = "ssh"
    host        = self.public_ip
    user        = "ec2-user"
    private_key = file("~/.ssh/gitlab_runner")
  }
  depends_on = [aws_eip.eip]
}

# Ubuntu EC2 instance
resource "aws_instance" "ubuntu_instance" {
  count                  = var.count_ubuntu_instances
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.ssh_key.key_name
  subnet_id              = data.aws_subnets.default.ids[0]
  vpc_security_group_ids = [aws_security_group.sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2profile.name

  tags = {
    Name  = "Server_Ubuntu_${count.index + 1}"
    Owner = "Gtlab"
  }
  provisioner "file" {
    source      = "scripts/docker_aws_install_ubuntu.sh"
    destination = "/tmp/docker_aws_install_ubuntu.sh"
  }
  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/docker_aws_install_ubuntu.sh",
      "sudo /tmp/docker_aws_install_ubuntu.sh"
    ]
  }
  connection {
    type        = "ssh"
    host        = self.public_ip
    user        = "ubuntu"
    private_key = file("~/.ssh/gitlab_runner")
  }
  depends_on = [aws_eip.eip]
}

#############################
# Elastic IP
#############################

# Elastic IPs
resource "aws_eip" "eip" {
  count = var.count_ubuntu_instances + var.count_rhel_instances
  vpc   = true
}

# Association the Elastic IP to the instances
resource "aws_eip_association" "eip_association" {
  count         = length(concat(aws_instance.ubuntu_instance, aws_instance.RHEL8_instance))
  allocation_id = aws_eip.eip[count.index].id
  instance_id   = element(concat(aws_instance.ubuntu_instance.*.id, aws_instance.RHEL8_instance.*.id), count.index)

  lifecycle {
    create_before_destroy = true
  }
}


#############################
#  NSG
#############################

# Network Security Group
resource "aws_security_group" "sg" {
  name        = "SG-EC2-bluegreen"
  description = "sg for gitlab ssh access and web access"
  vpc_id      = data.aws_vpc.default.id

  dynamic "ingress" {
    for_each = ["80", "8080", "443", "22"]
    content {
      description = "Allow HTTP, HTTPS, SSH"
      from_port   = ingress.value
      to_port     = ingress.value
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
    }
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

#############################
#  IAM
#############################

# Create an IAM instance profile for the instances
resource "aws_iam_instance_profile" "ec2profile" {
  name = "gitlab-instance-profile"

  role = aws_iam_role.gitlab-ec2-role.name
}

# Create an IAM role for the instances
resource "aws_iam_role" "gitlab-ec2-role" {
  name = "gitlab-ec2-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = ["ec2.amazonaws.com", "ssm.amazonaws.com"]
        }
      }
    ]
  })
}

# Create an IAM policy with full access to ECR
resource "aws_iam_policy" "ecr_policy" {
  name = "my-ecr-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "ecr:*"
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Attach the IAM policy to the IAM role
resource "aws_iam_role_policy_attachment" "my_attachment" {
  policy_arn = aws_iam_policy.ecr_policy.arn
  role       = aws_iam_role.gitlab-ec2-role.name
}

