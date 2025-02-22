output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.forwarder.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.forwarder.arn
}

output "lambda_role_arn" {
  description = "ARN of the Lambda IAM role"
  value       = aws_iam_role.lambda.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda IAM role"
  value       = aws_iam_role.lambda.name
}

output "secret_arn" {
  description = "ARN of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.datadog_api_key.arn
}

output "secret_name" {
  description = "Name of the Secrets Manager secret"
  value       = aws_secretsmanager_secret.datadog_api_key.name
}
