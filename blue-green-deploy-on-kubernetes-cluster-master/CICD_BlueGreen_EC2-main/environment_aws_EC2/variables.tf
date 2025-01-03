variable "region" {
  default = "eu-central-1"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "count_ubuntu_instances" {
  default = "1"
}

variable "count_rhel_instances" {
  default = "1"
}
