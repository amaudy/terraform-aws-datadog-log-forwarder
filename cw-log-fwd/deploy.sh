#!/bin/bash

# Configuration
REGION="us-east-1"
MAIN_FUNCTION_NAME="study-datadog-dev-forwarder"
HEALTH_FUNCTION_NAME="study-datadog-dev-health-check"
ROLE_NAME="study-datadog-lambda-role"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Creating deployment package..."
cd src
zip -r ../deployment.zip .
cd ..

echo "Creating IAM role..."
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document '{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }]
    }'

# Wait for role to be created
sleep 5

# Attach basic Lambda execution policy
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create and attach Secrets Manager policy
aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name SecretsManagerAccess \
    --policy-document file://iam/secrets-policy.json

# Get role ARN
ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

echo "Creating main Lambda function..."
aws lambda create-function \
    --function-name $MAIN_FUNCTION_NAME \
    --runtime python3.9 \
    --handler lambda_function.lambda_handler \
    --role $ROLE_ARN \
    --zip-file fileb://deployment.zip \
    --timeout 300 \
    --memory-size 256 \
    --environment "Variables={DD_SITE=datadoghq.com}" \
    --region $REGION

echo "Creating health check Lambda function..."
aws lambda create-function \
    --function-name $HEALTH_FUNCTION_NAME \
    --runtime python3.9 \
    --handler health_check.lambda_handler \
    --role $ROLE_ARN \
    --zip-file fileb://deployment.zip \
    --timeout 30 \
    --memory-size 128 \
    --environment "Variables={DD_SITE=datadoghq.com}" \
    --region $REGION

# Clean up
rm deployment.zip

echo "Deployment complete!"
echo "Main function ARN: arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${MAIN_FUNCTION_NAME}"
echo "Health check ARN: arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${HEALTH_FUNCTION_NAME}"
echo ""
echo "To test the health check, run:"
echo "./invoke-health-check.sh"
