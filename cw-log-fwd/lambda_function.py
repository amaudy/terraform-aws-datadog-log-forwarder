import os
import json
import boto3
import base64
import gzip
from health_check import health_check

def get_api_key():
    """Get Datadog API key from AWS Secrets Manager."""
    secret_arn = os.environ.get('DD_API_KEY_SECRET_ARN')
    if not secret_arn:
        raise ValueError("DD_API_KEY_SECRET_ARN environment variable is not set")

    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response['SecretString'])
    return secret['api_key']

def lambda_handler(event, context):
    """Lambda function handler."""
    # Handle health check
    if event.get('healthCheck'):
        return health_check()

    # Get Datadog API key
    api_key = get_api_key()

    # Process CloudWatch Logs
    data = base64.b64decode(event['awslogs']['data'])
    log_event = json.loads(gzip.decompress(data))

    # TODO: Process and forward logs to Datadog
    # For now, just return success
    return {
        'statusCode': 200,
        'body': json.dumps('Successfully processed logs')
    }
