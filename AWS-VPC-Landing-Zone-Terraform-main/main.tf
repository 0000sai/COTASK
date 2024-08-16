resource "aws_vpc" "amc-vpc" {
  tags       = merge(var.tags, {})
  cidr_block = var.vpc_cidr
}


