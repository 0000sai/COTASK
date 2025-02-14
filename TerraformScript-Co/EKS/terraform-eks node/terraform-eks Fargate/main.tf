# VPC-01
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/vpc
resource "aws_vpc" "eks-demo-vpc-01" {
  cidr_block = "10.0.0.0/16"
  tags = {
    Name = "eks-demo-vpc-01"
  }
}
# VPC-02
# Public Subnet
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/subnet
resource "aws_subnet" "eks-demo-public-01" {
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  vpc_id                  = aws_vpc.eks-demo-vpc-01.id
  map_public_ip_on_launch = true
  tags = {
    Name = "eks-demo-public-01"
  }
}
# VPC-03
# Private Subnet
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/subnet
resource "aws_subnet" "eks-demo-private-01" {
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "us-east-1a"
  vpc_id                  = aws_vpc.eks-demo-vpc-01.id
  map_public_ip_on_launch = true
  tags = {
    Name = "eks-demo-private-01"
  }
}
# VPC-04
# Public Subnet
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/subnet
resource "aws_subnet" "eks-demo-public-02" {
  cidr_block              = "10.0.3.0/24"
  availability_zone       = "us-east-1b"
  vpc_id                  = aws_vpc.eks-demo-vpc-01.id
  map_public_ip_on_launch = true
  tags = {
    Name = "eks-demo-public-02"
  }
}
# VPC-05
# Private Subnet
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/subnet
resource "aws_subnet" "eks-demo-private-02" {
  cidr_block              = "10.0.4.0/24"
  availability_zone       = "us-east-1b"
  vpc_id                  = aws_vpc.eks-demo-vpc-01.id
  map_public_ip_on_launch = true
  tags = {
    Name = "eks-demo-private-02"
  }
}
# VPC-06
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eip
resource "aws_eip" "demo-eip-01" {
  domain                    = "vpc"
  depends_on = [aws_internet_gateway.eks-demo-internet-gateway-01]
  tags = {
    Name = "demo-eip-01"
  }
}
# VPC-07
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/internet_gateway
resource "aws_internet_gateway" "eks-demo-internet-gateway-01" {
  vpc_id = aws_vpc.eks-demo-vpc-01.id
  tags = {
    Name = "eks-demo-internet-gateway"
  }
}
# VPC-08
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/nat_gateway
resource "aws_nat_gateway" "eks-demo-internet-nat" {
  allocation_id = aws_eip.demo-eip-01.id
  subnet_id     = aws_subnet.eks-demo-public-01.id

  tags = {
    Name = "eks-demo-net-gateway"
  }

  depends_on = [aws_internet_gateway.eks-demo-internet-gateway-01]
}

# VPC-09
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table
resource "aws_route_table" "eks-demo-public" {
  vpc_id = aws_vpc.eks-demo-vpc-01.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.eks-demo-internet-gateway-01.id
  }

  tags = {
    Name = "eks-demo-public"
  }
}
# VPC-10
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table
resource "aws_route_table" "eks-demo-private" {
  vpc_id = aws_vpc.eks-demo-vpc-01.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.eks-demo-internet-nat.id
  }

  tags = {
    Name = "eks-demo-private"
  }
}
# VPC-11
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association
resource "aws_route_table_association" "private-us-east-1a" {
  subnet_id      = aws_subnet.eks-demo-private-01.id
  route_table_id = aws_route_table.eks-demo-private.id
}


# VPC-12
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association
resource "aws_route_table_association" "private-us-east-1b" {
  subnet_id      = aws_subnet.eks-demo-private-02.id
  route_table_id = aws_route_table.eks-demo-private.id
}

# VPC-13
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association
resource "aws_route_table_association" "public-us-east-1a" {
  subnet_id      = aws_subnet.eks-demo-public-01.id
  route_table_id = aws_route_table.eks-demo-public.id
}

# VPC-14
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/route_table_association
resource "aws_route_table_association" "public-us-east-1b" {
  subnet_id      = aws_subnet.eks-demo-public-02.id
  route_table_id = aws_route_table.eks-demo-public.id
}


# eks-cluster-01
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_cluster
resource "aws_eks_cluster" "eks-demo-cluster-01" {
  name     = "eks-demo-cluster-01"
  version  = "1.28"
  role_arn = aws_iam_role.eks-demo-cluster-admin-role-01.arn
  vpc_config {
    subnet_ids              = [
      aws_subnet.eks-demo-public-01.id,
      aws_subnet.eks-demo-public-02.id,
      ]
    endpoint_public_access  = true
    endpoint_private_access = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }
   access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
    bootstrap_cluster_creator_admin_permissions = true
  }
  depends_on = [
    aws_iam_role_policy_attachment.eks-demo-cluster-01-AmazonEKSClusterPolicy,aws_iam_role_policy_attachment.eks-demo-cluster-01-AmazonEKSVPCResourceController
  ]
  tags = {
    demo = "eks"
  }


}

# eks-cluster-02
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/data-sources/iam_policy_document
data "aws_iam_policy_document" "eks-demo-cluster-admin-role-policy" {
  statement {
    effect = "Allow"
    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }

    actions = ["sts:AssumeRole"]
  }
}

# eks-cluster-03
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role
resource "aws_iam_role" "eks-demo-cluster-admin-role-01" {
  name               = "eks-demo-cluster-admin-role-01"
  assume_role_policy = data.aws_iam_policy_document.eks-demo-cluster-admin-role-policy.json
}
# eks-cluster-04
resource "aws_iam_role_policy_attachment" "eks-demo-cluster-01-AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks-demo-cluster-admin-role-01.name
}

# eks-cluster-05
# Optionally, enable Security Groups for Pods
# Reference: https://docs.aws.amazon.com/eks/latest/userguide/security-groups-for-pods.html
resource "aws_iam_role_policy_attachment" "eks-demo-cluster-01-AmazonEKSVPCResourceController" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
  role       = aws_iam_role.eks-demo-cluster-admin-role-01.name
}

# eks-cluster-06
# Addones
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
resource "aws_eks_addon" "eks-demo-addon-coredns" {
  cluster_name                = aws_eks_cluster.eks-demo-cluster-01.name
  addon_name                  = "coredns"
  addon_version               = "v1.10.1-eksbuild.4" 
  resolve_conflicts_on_create = "OVERWRITE" 
}
# eks-cluster-07
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
resource "aws_eks_addon" "eks-demo-addon-kube-proxy" {
  cluster_name                = aws_eks_cluster.eks-demo-cluster-01.name
  addon_name                  = "kube-proxy"
  addon_version               = "v1.28.2-eksbuild.2" 
  resolve_conflicts_on_create = "OVERWRITE" 
}
# eks-cluster-08
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_addon
resource "aws_eks_addon" "eks-demo-addon-vpc-cni" {
  cluster_name                = aws_eks_cluster.eks-demo-cluster-01.name
  addon_name                  = "vpc-cni"
  addon_version               = "v1.15.1-eksbuild.1" 
  resolve_conflicts_on_create = "OVERWRITE" 
}

# eks-cluster-09
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role
resource "aws_iam_role" "eks-fargate-demo-profile-role-01" {
  name = "eks-fargate-demo-profile-role-01"

  assume_role_policy = jsonencode({
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks-fargate-pods.amazonaws.com"
      }
    }]
    Version = "2012-10-17"
  })
}

# eks-fargate-01
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/eks_fargate_profile
resource "aws_eks_fargate_profile" "fargate-demo-01" {
  cluster_name           = aws_eks_cluster.eks-demo-cluster-01.name
  fargate_profile_name   = "fargate-demo-01"
  pod_execution_role_arn = aws_iam_role.eks-fargate-demo-profile-role-01.arn
  subnet_ids = [
    aws_subnet.eks-demo-private-01.id,
    aws_subnet.eks-demo-private-02.id
  ]
  selector {
    namespace = "kube-system"
    labels = {
      k8s-app="kube-dns"
    }
  }
  selector {
    namespace = "demo"
  }

}

# eks-fargate-02
# https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy_attachment
resource "aws_iam_role_policy_attachment" "eks-demo-fargate-profile-01" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy"
  role       = aws_iam_role.eks-fargate-demo-profile-role-01.name
}

