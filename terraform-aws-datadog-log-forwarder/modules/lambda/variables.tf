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

variable "dd_api_key_secret_arn" {
  description = "ARN of the Secrets Manager secret containing the Datadog API key"
  type        = string
}

variable "datadog_site" {
  description = "Datadog site (datadoghq.com, datadoghq.eu, etc.)"
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

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
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

variable "function_name" {
  description = "Name of the Lambda function. If not provided, will use datadog-log-forwarder-{environment}"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name for the Lambda function"
  type        = string
  default     = "prod"
}

variable "cloudwatch_log_groups" {
  description = "List of CloudWatch Log Group names to subscribe to"
  type        = list(string)
  default     = []
}

variable "filter_pattern" {
  description = "CloudWatch Log Group subscription filter pattern"
  type        = string
  default     = ""
}
