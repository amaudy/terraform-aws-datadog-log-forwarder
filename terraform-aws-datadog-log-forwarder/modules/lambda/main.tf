locals {
  lambda_function_name = var.function_name != "" ? var.function_name : "datadog-log-forwarder-${var.environment}"
  tags = merge(
    {
      Environment = var.environment
      Terraform   = "true"
      Module      = "datadog-log-forwarder"
    },
    var.tags
  )
}

# Create Lambda function zip file
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/dist/function.zip"
}

# Create IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${local.lambda_function_name}-role"

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

# Attach CloudWatch Logs policy to Lambda role
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${local.lambda_function_name}-policy"
  role = aws_iam_role.lambda_role.id

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
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Create Lambda function
resource "aws_lambda_function" "log_forwarder" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = local.lambda_function_name
  role            = aws_iam_role.lambda_role.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.9"
  timeout         = var.timeout
  memory_size     = var.memory_size

  environment {
    variables = {
      DD_API_KEY = var.datadog_api_key
      DD_SITE    = var.datadog_site
    }
  }

  tags = local.tags
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
