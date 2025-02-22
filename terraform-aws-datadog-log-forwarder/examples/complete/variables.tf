variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., prod, staging, dev)"
  type        = string
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing the Lambda deployment package"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key for the Lambda deployment package"
  type        = string
}

variable "datadog_api_key" {
  description = "Datadog API Key"
  type        = string
  sensitive   = true
}

variable "datadog_site" {
  description = "Datadog site (datadoghq.com, datadoghq.eu, etc.)"
  type        = string
  default     = "datadoghq.com"
}
