resource "aws_lb" "test" {
  name               = "devops"
  internal           = false
  load_balancer_type = "application"
  security_groups    = ["sg-051560a66860c94cd"]
  subnets            = [ "subnet-078b1c46cec5be2fb","subnet-08f200b1fcb56ee1f" ]

  enable_deletion_protection = true

  access_logs {
    bucket  = "dbdevopsteam"                                                                   
    enabled = true
  }

  tags = {
    Environment = "production"
  }
}
