resource "aws_route_table" "terraform-public" {
  vpc_id = aws_vpc.default.id

  # route {
  #   cidr_block = "0.0.0.0/0"
  #   gateway_id = aws_internet_gateway.default.id
  # }

  tags = {
    Name              = "${var.vpc_name}-MAIN-RT"
    Terraform-Managed = "Yes"
    Env               = local.new_environment
    ProjectID         = local.projid
  }
}

#VPC Peering Routes are getting recreated when we apply. To overcome this issue Routing Table
#is created with out any routes & routes for igw,peering are created seperatly.
#https://stackoverflow.com/questions/49174421/terraform-route-table-forcing-new-resource-every-apply

resource "aws_route" "igw-route" {
  route_table_id         = aws_route_table.terraform-public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.default.id
}

resource "aws_route_table_association" "terraform-public" {
  #count             = 4 # 0 1 2
  count = length(local.new_public_subnet_cidrs)
  #Using * is called Splat Syntax
  subnet_id      = element(aws_subnet.public-subnets.*.id, count.index)
  route_table_id = aws_route_table.terraform-public.id
}