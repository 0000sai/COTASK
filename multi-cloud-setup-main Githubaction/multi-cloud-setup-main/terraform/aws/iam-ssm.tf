resource "aws_iam_policy" "ssm_access" {
  name        = "ssm-parameter-access"
  description = "Allow access to SSM parameters"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath"
        ]
        Resource = [
          "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/demo-app/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role" "eks_ssm_role" {
  name = "eks-ssm-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}:sub": "system:serviceaccount:default:ssm-sa"
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_policy_attachment" {
  policy_arn = aws_iam_policy.ssm_access.arn
  role       = aws_iam_role.eks_ssm_role.name
}
