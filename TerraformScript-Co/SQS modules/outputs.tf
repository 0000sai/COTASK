output "sqs_queue_id" {
  description = "The URL for the created Amazon SQS queue"
  value       = aws_sqs_queue.main.id
}

output "sqs_queue_arn" {
  description = "The ARN of the SQS queue"
  value       = aws_sqs_queue.main.arn
}

output "sqs_queue_url" {
  description = "Same as `id`: The URL for the created Amazon SQS queue."
  value       = aws_sqs_queue.main.url
}

output "sqs_queue_tags_all" {
  description = "A map of tags assigned to the resource, including those inherited from the provider `default_tags` configuration block."
  value       = aws_sqs_queue.main.tags_all
}
