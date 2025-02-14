resource "aws_lb" "alb" {
  name               = "app-nlb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = ["${aws_security_group.allow_all.id}"]
  subnets            = [aws_subnet.subnet1-public.id,aws_subnet.subnet2-public.id,aws_subnet.subnet3-public.id]
  enable_deletion_protection = false
  tags = {
    Environment = "Production"
  }
}

resource "aws_lb_target_group" "albtest" {
  name     = "app-tg"
  port     = 80
  protocol = "HTTP"
  vpc_id   = aws_vpc.default.id
}

resource "aws_lb_target_group" "albtest-flask" {
  name     = "app-tg-flask"
  port     = 5000
  protocol = "HTTP"
  vpc_id   = aws_vpc.default.id
}



resource "aws_lb_target_group_attachment" "albtest" {
  count = 3
  target_group_arn = aws_lb_target_group.albtest.arn
  target_id        = "${element(aws_instance.web-1.*.id, count.index)}"
  port             = 8000
}

resource "aws_lb_target_group_attachment" "albflask" {
  count = 3
  target_group_arn = aws_lb_target_group.albtest-flask.arn
  target_id        = "${element(aws_instance.web-1.*.id, count.index)}"
  port             = 5000
}