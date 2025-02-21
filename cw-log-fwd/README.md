# CloudWatch Logs to Datadog Forwarder

Python Lambda function to forward CloudWatch logs to Datadog.

## Features

- Forwards CloudWatch logs to Datadog in real-time
- Preserves original log structure and metadata
- Adds AWS context (log group, stream, region)
- Handles both JSON and plain text logs
- Error handling and reporting
- No external dependencies (uses Python standard library)

## Setup

1. Create a Lambda function:
```bash
zip -r function.zip src/* requirements.txt
aws lambda create-function \
    --function-name cloudwatch-to-datadog \
    --runtime python3.9 \
    --handler src.lambda_function.lambda_handler \
    --role arn:aws:iam::<ACCOUNT_ID>:role/lambda-cloudwatch-datadog \
    --zip-file fileb://function.zip
```

2. Set environment variables:
```bash
aws lambda update-function-configuration \
    --function-name cloudwatch-to-datadog \
    --environment "Variables={DD_API_KEY=<your-api-key>,DD_SITE=datadoghq.com}"
```

3. Create CloudWatch subscription filter:
```bash
aws logs put-subscription-filter \
    --log-group-name "/poc/dd-log" \
    --filter-name "datadog-forwarder" \
    --filter-pattern "" \
    --destination-arn "arn:aws:lambda:<region>:<account-id>:function:cloudwatch-to-datadog"
```

## Required IAM Role Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```

## Environment Variables

- `DD_API_KEY`: Your Datadog API key
- `DD_SITE`: Datadog site (default: datadoghq.com)

## Log Format

The forwarder preserves the original log format and adds:

```json
{
    "ddsource": "cloudwatch",
    "service": "fastapi-app",
    "ddtags": "env:prod,source:cloudwatch",
    "cloudwatch": {
        "log_group": "<log-group-name>",
        "log_stream": "<log-stream-name>",
        "aws_region": "<region>"
    }
}
```
