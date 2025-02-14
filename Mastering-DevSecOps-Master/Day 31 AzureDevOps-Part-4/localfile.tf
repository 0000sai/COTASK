resource "local_file" "foo" {
  content = templatefile("details.tpl",
    {

      master01 = aws_instance.web-1.0.public_ip
      master02 = aws_instance.web-1.1.public_ip
      master03 = aws_instance.web-1.2.public_ip
      #worker01 = aws_instance.worker-1.public_ip
      #worker02 = aws_instance.worker-2.public_ip
      #worker03 = aws_instance.worker-3.public_ip
      # worker04 = aws_instance.worker-4.public_ip
      # worker05 = aws_instance.worker-5.public_ip
    }
  )
  filename = "invfile"
}