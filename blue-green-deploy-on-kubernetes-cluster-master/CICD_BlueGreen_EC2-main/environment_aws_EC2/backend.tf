#############################
# Terraform backend
#############################

terraform {
  backend "s3" {
    bucket = "your-s3-bucket"                                # bucket for terraform state file, should be exist
    key    = "gitlab-runner-configuration/terraform.tfstate" # object name in the bucket to save terraform file
    region = "eu-central-1"                                  # region where the bucket is created
  }
}
