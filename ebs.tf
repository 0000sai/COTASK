resource "aws_ebs_volume" "example" {
  availability_zone = "ap-south-1a"   # add the availability_zone  go to vpc and flow map the can see  availability_zone (0r)ec2 dashbode
  size              = 6

tags = {
    Name = "DEVOPSEBS"
  }
}
