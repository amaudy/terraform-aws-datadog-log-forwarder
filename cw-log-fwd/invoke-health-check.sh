#!/bin/bash
set -e

# Configuration
ENVIRONMENT=${ENVIRONMENT:-"dev"}
FUNCTION_NAME=${FUNCTION_NAME:-"datadog-forwarder-${ENVIRONMENT}"}
REGION=${REGION:-"us-east-1"}

# Invoke Lambda function with health check payload
aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --region $REGION \
  --payload '{"healthCheck": true}' \
  --cli-binary-format raw-in-base64-out \
  response.json

echo "Health check response:"
cat response.json
rm response.json
