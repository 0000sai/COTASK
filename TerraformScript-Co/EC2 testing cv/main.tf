module "ec2_instance" {
  source  = "terraform-aws-modules/ec2-instance/aws"

  name = "single-instance"

  instance_type          = "t3.micro"
  key_name               = "revanth123"
  monitoring             = true
  vpc_security_group_ids = ["sg-0bbbd9928423d7c0a"]
  subnet_id              = "subnet-09a8c8ec376000861"

  tags = {
    Terraform   = "true"
    Environment = "dev"
  }
}
