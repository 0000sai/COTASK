terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS Provider
provider "aws" {
  region = "ap-south-1"
}

# create an iam user
resource "aws_iam_user" "iam_user" {
  name = "Aicloud"
}

# give the iam user programatic access
resource "aws_iam_access_key" "iam_access_key" {
  user = aws_iam_user.iam_user.name
}

# create the inline policy
data "aws_iam_policy_document" "s3_get_put_detele_policy_document" {
  statement {
    actions = [
      "s3:PutObject",
      "s3:GetObject",
      "s3:DeleteObject",
    ]

    resources = [
      "arn:aws:s3:::revanth-bucket-12345/*"
    ]
  }
}

# attach the policy to the useri
resource "aws_iam_user_policy" "s3_get_put_detele_policy" {
  name   = "s3-get-put-delete"
  user   = aws_iam_user.iam_user.name
  policy = data.aws_iam_policy_document.s3_get_put_detele_policy_document.json
}
