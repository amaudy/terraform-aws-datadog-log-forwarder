output "lambda_function_name" {
  description = "Name of the created Lambda function"
  value       = aws_lambda_function.log_forwarder.function_name
}

output "lambda_function_arn" {
  description = "ARN of the created Lambda function"
  value       = aws_lambda_function.log_forwarder.arn
}

output "lambda_role_arn" {
  description = "ARN of the IAM role created for the Lambda function"
  value       = aws_iam_role.lambda_role.arn
}

output "lambda_role_name" {
  description = "Name of the IAM role created for the Lambda function"
  value       = aws_iam_role.lambda_role.name
}

output "cloudwatch_log_subscription_arns" {
  description = "ARNs of the CloudWatch Log subscription filters"
  value       = aws_cloudwatch_log_subscription_filter.log_subscription[*].arn
}
