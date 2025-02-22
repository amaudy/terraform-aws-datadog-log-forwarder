locals {
  lambda_function_name = var.function_name != "" ? var.function_name : "datadog-log-forwarder-${var.environment}"
  lambda_role_name     = "${var.name_prefix}-lambda-role"
  tags = merge(
    {
      Environment = var.environment
      Project     = "datadog-log-forwarder"
      ManagedBy   = "terraform"
    },
    var.tags
  )
}

# Get current AWS region and account ID
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Get existing CloudWatch log group
data "aws_cloudwatch_log_group" "target" {
  count = length(var.cloudwatch_log_groups)
  name  = var.cloudwatch_log_groups[count.index]
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

  tags = local.tags
}

# Allow Lambda to write its own logs
resource "aws_iam_role_policy" "lambda_logging" {
  name = "${local.lambda_role_name}-logging"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.lambda_function_name}:*"
      }
    ]
  })
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
          var.dd_api_key_secret_arn
        ]
      }
    ]
  })
}

# Allow Lambda to read from CloudWatch Logs
resource "aws_iam_role_policy" "lambda_cloudwatch" {
  name = "${local.lambda_role_name}-cloudwatch"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents"
        ]
        Resource = concat(
          [for group in var.cloudwatch_log_groups : "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:${group}:*"]
        )
      }
    ]
  })
}

# Create CloudWatch log group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.lambda_function_name}"
  retention_in_days = var.log_retention_days
  tags              = local.tags
}

# Create Lambda function
resource "aws_lambda_function" "forwarder" {
  function_name = local.lambda_function_name
  description   = "Forwards CloudWatch logs to Datadog"

  s3_bucket = var.lambda_s3_bucket
  s3_key    = var.lambda_s3_key

  runtime = "python3.9"
  handler = "lambda_function.lambda_handler"

  role = aws_iam_role.lambda.arn

  memory_size = var.memory_size
  timeout     = var.timeout

  environment {
    variables = merge(
      {
        DD_API_KEY_SECRET_ARN = var.dd_api_key_secret_arn
        DD_SITE               = var.datadog_site
      },
      var.environment_variables
    )
  }

  depends_on = [
    aws_iam_role_policy.lambda_logging,
    aws_iam_role_policy.lambda_secrets,
    aws_iam_role_policy.lambda_cloudwatch,
    aws_cloudwatch_log_group.lambda
  ]

  tags = local.tags
}

# Grant CloudWatch Logs permission to invoke Lambda for each log group
resource "aws_lambda_permission" "cloudwatch" {
  count = length(var.cloudwatch_log_groups)

  statement_id  = "AllowCloudWatchInvoke-${count.index}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.forwarder.function_name
  principal     = "logs.amazonaws.com"
  source_arn    = "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:${var.cloudwatch_log_groups[count.index]}:*"
}

# Create CloudWatch Log subscription filter
resource "aws_cloudwatch_log_subscription_filter" "log_subscription" {
  count = length(var.cloudwatch_log_groups)

  name            = "${local.lambda_function_name}-filter-${count.index}"
  log_group_name  = var.cloudwatch_log_groups[count.index]
  filter_pattern  = var.filter_pattern
  destination_arn = aws_lambda_function.forwarder.arn

  depends_on = [
    aws_lambda_permission.cloudwatch,
    aws_lambda_function.forwarder
  ]
}
