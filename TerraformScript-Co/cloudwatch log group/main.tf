provider "aws" {
  region = "ap-south-1"
}

resource "aws_cloudwatch_log_group" "log_group" {
  name              = var.log_group_name
  retention_in_days = var.retention_days
}

resource "aws_cloudwatch_log_stream" "log_stream" {
  name           = "devops-log-stream"                          
  log_group_name = aws_cloudwatch_log_group.log_group.name
}
