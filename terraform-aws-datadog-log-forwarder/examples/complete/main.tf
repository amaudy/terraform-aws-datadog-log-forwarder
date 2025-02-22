provider "aws" {
  region = "us-east-1"
}

module "datadog_log_forwarder" {
  # Option 1: Using HTTPS
  source = "git::https://github.com/yourusername/terraform-aws-datadog-log-forwarder.git//modules/lambda?ref=v1.0.0"

  # Option 2: Using SSH (if you have SSH access configured)
  # source = "git::ssh://git@github.com/yourusername/terraform-aws-datadog-log-forwarder.git//modules/lambda?ref=v1.0.0"

  environment         = "prod"
  datadog_api_key    = var.datadog_api_key
  datadog_site       = "datadoghq.com"
  cloudwatch_log_groups = [
    "/aws/lambda/my-application",
    "/aws/apigateway/my-api"
  ]

  # Optional configurations
  function_name = "my-datadog-forwarder"
  memory_size  = 256
  timeout      = 300

  tags = {
    Project     = "MyApp"
    Environment = "Production"
  }
}
