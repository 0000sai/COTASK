resource "aws_apigatewayv2_api" "dev" {
  name          = "dev"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_stage" "staging" {
  name        = "staging"
  api_id      = aws_apigatewayv2_api.dev.id
  auto_deploy = true
}
