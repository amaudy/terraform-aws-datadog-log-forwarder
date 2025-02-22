variable "name_prefix" {
  description = "Name prefix for resources"
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

variable "lambda_memory_size" {
  description = "Memory size for Lambda function (MB)"
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Timeout for Lambda function (seconds)"
  type        = number
  default     = 300
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "secret_name" {
  description = "Name of the AWS Secrets Manager secret to store Datadog API key"
  type        = string
  default     = "datadog-api-key"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 30
}

variable "environment_variables" {
  description = "Additional environment variables for Lambda function"
  type        = map(string)
  default     = {}
}
