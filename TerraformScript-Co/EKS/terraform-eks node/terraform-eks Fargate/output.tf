output "endpoint" {
  value = aws_eks_cluster.eks-demo-cluster-01.endpoint
}

output "kubeconfig-certificate-authority-data" {
  value = aws_eks_cluster.eks-demo-cluster-01.certificate_authority[0].data
}

output "vpc_id" {
  value = aws_vpc.eks-demo-vpc-01.id
}

output "subnet_ids" {
  value = [
    aws_subnet.eks-demo-public-01.id,
    aws_subnet.eks-demo-public-02.id,
    aws_subnet.eks-demo-private-01.id,
    aws_subnet.eks-demo-private-02.id
  ]
}

output "internet_gateway_id" {
  value = aws_internet_gateway.eks-demo-internet-gateway-01.id
}

output "nat_gateway_id" {
  value = aws_nat_gateway.eks-demo-internet-nat.id
}

output "cluster_arn" {
  value = aws_eks_cluster.eks-demo-cluster-01.arn
}
