data "aws_route53_zone" "selected" {
  name = "cloudvishwakarma.in"
}

resource "aws_route53_record" "nlb" {
  zone_id = data.aws_route53_zone.selected.zone_id
  name    = "myapp.${data.aws_route53_zone.selected.name}"
  type    = "A"

  alias {
    name                   = aws_lb.alb.dns_name
    zone_id                = aws_lb.alb.zone_id
    evaluate_target_health = false
  }
}
