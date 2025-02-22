variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "name_prefix" {
  description = "Name prefix for resources"
  type        = string
}

variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
  default     = ""
}

variable "lambda_s3_bucket" {
  description = "S3 bucket containing the Lambda package"
  type        = string
}

variable "lambda_s3_key" {
  description = "S3 key for the Lambda package"
  type        = string
}

variable "datadog_site" {
  description = "Datadog site (e.g., datadoghq.com, datadoghq.eu)"
  type        = string
  default     = "datadoghq.com"
}

variable "memory_size" {
  description = "Amount of memory in MB for the Lambda function"
  type        = number
  default     = 256
}

variable "timeout" {
  description = "Timeout in seconds for the Lambda function"
  type        = number
  default     = 300
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "dd_api_key_secret_arn" {
  description = "ARN of the secret containing the Datadog API key"
  type        = string
  sensitive   = true
}
