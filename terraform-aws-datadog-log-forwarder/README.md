# AWS CloudWatch to Datadog Log Forwarder Terraform Module

This Terraform module creates an AWS Lambda function that forwards CloudWatch logs to Datadog.

## Features

- Forwards CloudWatch logs to Datadog in real-time
- Supports multiple CloudWatch Log Groups
- Configurable Lambda function settings (memory, timeout)
- Proper IAM roles and permissions
- Customizable with tags and naming

## Usage

### Using Latest Version

```hcl
module "datadog_log_forwarder" {
  source = "git::https://github.com/yourusername/terraform-aws-datadog-log-forwarder.git//modules/lambda"

  environment         = "prod"
  datadog_api_key    = var.datadog_api_key
  cloudwatch_log_groups = [
    "/aws/lambda/my-application",
    "/aws/apigateway/my-api"
  ]

  tags = {
    Project     = "MyApp"
    Environment = "Production"
  }
}
```

### Using Specific Version

```hcl
module "datadog_log_forwarder" {
  source = "git::https://github.com/yourusername/terraform-aws-datadog-log-forwarder.git//modules/lambda?ref=v1.0.0"

  environment         = "prod"
  datadog_api_key    = var.datadog_api_key
  cloudwatch_log_groups = [
    "/aws/lambda/my-application",
    "/aws/apigateway/my-api"
  ]

  tags = {
    Project     = "MyApp"
    Environment = "Production"
  }
}
```

### Version Reference Options

You can pin to different types of Git refs:

- Tag: `?ref=v1.0.0`
- Branch: `?ref=main`
- Commit: `?ref=51d462976d84fdea54b47d80dcabbf680badcdb8`

For production use, we recommend pinning to specific tags for stability.

## Requirements

| Name | Version |
|------|---------|
| terraform | >= 1.0 |
| aws | >= 4.0 |

## Providers

| Name | Version |
|------|---------|
| aws | >= 4.0 |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| environment | Environment name (e.g., prod, staging, dev) | `string` | n/a | yes |
| datadog_api_key | Datadog API key | `string` | n/a | yes |
| datadog_site | Datadog site (e.g., datadoghq.com, datadoghq.eu) | `string` | `"datadoghq.com"` | no |
| cloudwatch_log_groups | List of CloudWatch Log Group names to subscribe to | `list(string)` | n/a | yes |
| function_name | Name of the Lambda function | `string` | `""` | no |
| filter_pattern | CloudWatch Logs filter pattern | `string` | `""` | no |
| timeout | Lambda function timeout in seconds | `number` | `300` | no |
| memory_size | Lambda function memory size in MB | `number` | `256` | no |
| tags | Additional tags to apply to resources | `map(string)` | `{}` | no |

## Outputs

| Name | Description |
|------|-------------|
| lambda_function_name | Name of the created Lambda function |
| lambda_function_arn | ARN of the created Lambda function |
| lambda_role_arn | ARN of the IAM role created for the Lambda function |
| lambda_role_name | Name of the IAM role created for the Lambda function |
| cloudwatch_log_subscription_arns | ARNs of the CloudWatch Log subscription filters |

## Security and Sensitive Data

This module requires access to sensitive data:

1. **Datadog API Key**: Must be stored in AWS Secrets Manager. Never commit API keys to version control.
   ```bash
   # Store the API key in AWS Secrets Manager
   aws secretsmanager create-secret \
     --name your-secret-name \
     --secret-string '{"DD_API_KEY":"your-api-key"}'
   ```

2. **Secret ARN**: The ARN of the secret containing your Datadog API key. Pass this as a variable:
   ```hcl
   dd_api_key_secret_arn = "arn:aws:secretsmanager:<region>:<account>:secret:<name>-<suffix>"
   ```

3. **Environment Variables**: For testing, set required environment variables:
   ```bash
   export DD_API_KEY_SECRET_ARN="your-secret-arn"
   ```

Never commit sensitive data to version control. Use:
- Environment variables for local development
- AWS Secrets Manager for production credentials
- `.gitignore` to prevent accidental commits of sensitive files
- AWS IAM roles and policies for secure access

## Versioning

This module follows semantic versioning. Each release is tagged with a version number (e.g., v1.0.0).

Major version changes (e.g., v1.0.0 -> v2.0.0) indicate breaking changes.
Minor version changes (e.g., v1.0.0 -> v1.1.0) indicate new features.
Patch version changes (e.g., v1.0.0 -> v1.0.1) indicate bug fixes.

## Notes

1. Make sure to never commit your Datadog API key to version control
2. Use AWS Secrets Manager or SSM Parameter Store to manage the API key
3. Consider the Lambda function's memory and timeout based on your log volume
4. Always pin to a specific version in production environments

## License

MIT Licensed. See LICENSE for full details.
