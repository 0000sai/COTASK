resource "local_file" "ansible-inventory-file" {
  content = templatefile("publicservers.tpl",
    {

      testserver01    = aws_instance.webservers.0.public_ip
      testserver02    = aws_instance.webservers.1.public_ip
      testserver03    = aws_instance.webservers.2.public_ip
      pvttestserver01 = aws_instance.webservers.0.private_ip
      pvttestserver02 = aws_instance.webservers.1.private_ip
      pvttestserver03 = aws_instance.webservers.2.private_ip
    }
  )
  filename = "${path.module}/invfile"
}