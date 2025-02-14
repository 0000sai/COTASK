resource "aws_lb_listener" "alb-https" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-FS-1-2-Res-2020-10"
  certificate_arn   = "arn:aws:acm:us-east-1:211125710812:certificate/13300e95-ddf9-40d0-b807-977f157d59d2"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.albtest.arn
  }
}

resource "aws_lb_listener" "alb-https-redirect" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

resource "aws_lb_listener" "alb-flask" {
  load_balancer_arn = aws_lb.alb.arn
  port              = "5000"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-FS-1-2-Res-2020-10"
  certificate_arn   = "arn:aws:acm:us-east-1:211125710812:certificate/13300e95-ddf9-40d0-b807-977f157d59d2"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.albtest-flask.arn
  }
}