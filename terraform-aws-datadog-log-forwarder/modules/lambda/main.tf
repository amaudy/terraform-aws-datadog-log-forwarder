locals {
  lambda_function_name = var.function_name != "" ? var.function_name : "datadog-log-forwarder-${var.environment}"
  lambda_role_name    = "${var.name_prefix}-lambda-role"
  tags = merge(
    {
      Environment = var.environment
      Terraform   = "true"
      Module      = "datadog-log-forwarder"
    },
    var.tags
  )
}

# Create AWS Secrets Manager secret for Datadog API key
resource "aws_secretsmanager_secret" "datadog_api_key" {
  name        = var.secret_name
  description = "Datadog API key for log forwarding"
  tags        = var.tags
}

resource "aws_secretsmanager_secret_version" "datadog_api_key" {
  secret_id     = aws_secretsmanager_secret.datadog_api_key.id
  secret_string = jsonencode({
    api_key = var.datadog_api_key
  })
}

# Create IAM role for Lambda
resource "aws_iam_role" "lambda" {
  name = local.lambda_role_name

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Allow Lambda to write logs to CloudWatch
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Allow Lambda to access Secrets Manager
resource "aws_iam_role_policy" "lambda_secrets" {
  name = "${local.lambda_role_name}-secrets"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = [
          aws_secretsmanager_secret.datadog_api_key.arn
        ]
      }
    ]
  })
}

# Create CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.lambda_function_name}"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

# Create Lambda function
resource "aws_lambda_function" "log_forwarder" {
  function_name = local.lambda_function_name
  role         = aws_iam_role.lambda.arn
  handler      = "lambda_function.lambda_handler"
  runtime      = "python3.9"
  timeout      = var.timeout
  memory_size  = var.memory_size

  s3_bucket = var.lambda_s3_bucket
  s3_key    = var.lambda_s3_key

  environment {
    variables = merge({
      DD_API_KEY = jsondecode(aws_secretsmanager_secret_version.datadog_api_key.secret_string)["api_key"]
      DD_SITE    = var.datadog_site
    }, var.environment_variables)
  }

  tags = local.tags

  depends_on = [
    aws_cloudwatch_log_group.lambda,
    aws_iam_role_policy_attachment.lambda_logs,
    aws_iam_role_policy.lambda_secrets
  ]
}

# Create CloudWatch Log subscription filter
resource "aws_cloudwatch_log_subscription_filter" "log_subscription" {
  count           = length(var.cloudwatch_log_groups)
  name            = "${local.lambda_function_name}-filter-${count.index}"
  log_group_name  = var.cloudwatch_log_groups[count.index]
  filter_pattern  = var.filter_pattern
  destination_arn = aws_lambda_function.log_forwarder.arn

  depends_on = [aws_lambda_permission.cloudwatch]
}

# Grant CloudWatch permission to invoke Lambda
resource "aws_lambda_permission" "cloudwatch" {
  statement_id  = "AllowCloudWatchInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.log_forwarder.function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:*"
}

# Get current AWS region and account ID
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
