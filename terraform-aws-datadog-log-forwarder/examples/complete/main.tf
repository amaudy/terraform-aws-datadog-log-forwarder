provider "aws" {
  region = var.aws_region
}

module "datadog_log_forwarder" {
  source = "../../modules/lambda"

  name_prefix      = "datadog-${var.environment}"
  lambda_s3_bucket = var.lambda_s3_bucket
  lambda_s3_key    = var.lambda_s3_key
  datadog_api_key  = var.datadog_api_key
  datadog_site     = "datadoghq.com"
  memory_size      = 256
  timeout          = 300

  # Optional configurations
  secret_name        = "datadog-api-key-${var.environment}"
  log_retention_days = 30

  # CloudWatch Log Groups to subscribe to
  cloudwatch_log_groups = [
    "/aws/lambda/example-function",
    "/aws/apigateway/example-api"
  ]
  filter_pattern = "" # Empty string means all logs

  environment_variables = {
    LOG_LEVEL = "INFO"
  }

  tags = {
    Environment = var.environment
    Terraform   = "true"
    Service     = "datadog-log-forwarder"
  }
}
