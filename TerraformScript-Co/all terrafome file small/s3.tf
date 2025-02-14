resource "aws_s3_bucket" "my_bucket" {
  bucket  = "gamingproject"              // bucker name is uniqe and      Bucket name must not contain uppercase characters  
  tags    = {
        Name          = "gaming"         // name to give the tags change it  
        Environment    = "Production"   
  }
}

