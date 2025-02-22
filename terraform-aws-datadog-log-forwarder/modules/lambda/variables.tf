variable "function_name" {
  description = "Name of the Lambda function. If not provided, will use datadog-log-forwarder-{environment}"
  type        = string
  default     = ""
}

variable "environment" {
  description = "Environment name (e.g., prod, staging, dev)"
  type        = string
}

variable "datadog_api_key" {
  description = "Datadog API key"
  type        = string
  sensitive   = true
}

variable "datadog_site" {
  description = "Datadog site (e.g., datadoghq.com, datadoghq.eu)"
  type        = string
  default     = "datadoghq.com"
}

variable "cloudwatch_log_groups" {
  description = "List of CloudWatch Log Group names to subscribe to"
  type        = list(string)
}

variable "filter_pattern" {
  description = "CloudWatch Logs filter pattern"
  type        = string
  default     = ""
}

variable "timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "memory_size" {
  description = "Lambda function memory size in MB"
  type        = number
  default     = 256
}

variable "tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
