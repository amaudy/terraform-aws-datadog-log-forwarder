provider "aws" {
  region = var.aws_region
}

module "datadog_log_forwarder" {
  source = "../../modules/lambda"

  name_prefix           = var.name_prefix
  function_name         = var.function_name
  lambda_s3_bucket      = var.lambda_s3_bucket
  lambda_s3_key         = var.lambda_s3_key
  dd_api_key_secret_arn = var.dd_api_key_secret_arn
  datadog_site          = "datadoghq.com"
  memory_size           = 256
  timeout               = 300
  environment           = var.environment

  # CloudWatch Log Groups to subscribe to
  cloudwatch_log_groups = [
    "/poc/dd-log"
  ]
  filter_pattern = "" # Empty string means all logs

  environment_variables = {
    LOG_LEVEL = "INFO"
  }

  tags = {
    Environment = var.environment
    Project     = "datadog-log-forwarder"
    Service     = "datadog-log-forwarder"
  }
}

output "lambda_function_arn" {
  value = module.datadog_log_forwarder.lambda_function_arn
}

output "lambda_function_name" {
  value = module.datadog_log_forwarder.lambda_function_name
}

output "lambda_role_arn" {
  value = module.datadog_log_forwarder.lambda_role_arn
}

output "lambda_role_name" {
  value = module.datadog_log_forwarder.lambda_role_name
}
