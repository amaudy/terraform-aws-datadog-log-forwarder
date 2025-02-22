#!/bin/bash

VERSION=${1:-"v1.0.0"}
S3_BUCKET=${2:-"my-lambda-artifacts"}
S3_PREFIX="datadog-forwarder"

# Package Lambda function
cd src
zip -r ../function.zip .
cd ..

# Upload to S3
aws s3 cp function.zip "s3://${S3_BUCKET}/${S3_PREFIX}/${VERSION}/function.zip"

rm function.zip

echo "Done! Lambda package uploaded to s3://${S3_BUCKET}/${S3_PREFIX}/${VERSION}/function.zip"
echo "lambda_s3_bucket = \"${S3_BUCKET}\""
echo "lambda_s3_key = \"${S3_PREFIX}/${VERSION}/function.zip\""
