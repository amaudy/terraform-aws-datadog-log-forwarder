#!/bin/bash

# Replace these values with your actual values
FUNCTION_NAME="study-datadog-dev-forwarder"
REGION="us-east-1"

# Invoke the Lambda function
aws lambda invoke \
    --function-name $FUNCTION_NAME \
    --region $REGION \
    --payload '{"source":"aws.health"}' \
    --cli-binary-format raw-in-base64-out \
    response.json

# Check if the invocation was successful
if [ $? -eq 0 ]; then
    echo "Health check invoked successfully"
    echo "Response:"
    cat response.json
    rm response.json
else
    echo "Failed to invoke health check"
    exit 1
fi
