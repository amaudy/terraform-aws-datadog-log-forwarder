import base64
import gzip
import json
import os
import urllib.request
import urllib.error
import boto3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union

# Initialize AWS clients
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')

def get_secret() -> Dict[str, str]:
    """Get secret from AWS Secrets Manager"""
    secret_arn = os.environ.get('DD_API_KEY_SECRET_ARN')
    if not secret_arn:
        raise ValueError("DD_API_KEY_SECRET_ARN environment variable is not set")

    try:
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        if 'SecretString' in response:
            return json.loads(response['SecretString'])
        raise ValueError("Secret not found")
    except Exception as e:
        print(f"Error retrieving secret: {str(e)}")
        raise ValueError(f"Failed to retrieve secret: {str(e)}")

def get_api_key() -> str:
    """Get the Datadog API key from AWS Secrets Manager"""
    # First try environment variable for local development/testing
    api_key = os.environ.get('DD_API_KEY')
    if api_key:
        return api_key
    
    # If not in environment, get from Secrets Manager
    try:
        secrets = get_secret()
        api_key = secrets.get('DD_API_KEY')
        if not api_key:
            raise ValueError("DD_API_KEY not found in secret")
        return api_key
    except Exception as e:
        raise ValueError(f"DD_API_KEY not available: {str(e)}")

def get_dd_url() -> str:
    """Get the Datadog URL based on site configuration"""
    dd_site = os.environ.get('DD_SITE', 'datadoghq.com')
    return f"https://http-intake.logs.{dd_site}/v1/input"

def parse_message(message: str) -> Dict[str, Any]:
    """Parse the log message and extract relevant fields."""
    try:
        data = json.loads(message)
        # Add additional context that might be useful in Datadog
        data['ddsource'] = 'cloudwatch'
        data['ddtags'] = 'env:prod,source:cloudwatch,app_id:fastapi-demo,app_name:fastapi-demo-app'
        data['service'] = 'cloudwatch-logs'
        data['app_id'] = 'fastapi-demo'
        data['app_name'] = 'fastapi-demo-app'
        data['host'] = 'simulator'
        data['aws'] = {
            'logger': data.get('logger', 'fastapi'),
            'log_group': data.get('log_group', ''),
            'log_stream': data.get('log_stream', ''),
        }
        return data
    except json.JSONDecodeError:
        # If message is not JSON, wrap it in a standard format
        return {
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "info",
            "logger": "cloudwatch",
            "ddsource": "cloudwatch",
            "ddtags": "env:prod,source:cloudwatch,app_id:fastapi-demo,app_name:fastapi-demo-app",
            "service": "cloudwatch-logs",
            "app_id": "fastapi-demo",
            "app_name": "fastapi-demo-app",
            "host": "simulator"
        }

def process_log_events(log_events: List[Dict[str, Any]], context: Dict[str, str]) -> List[Dict[str, Any]]:
    """Process CloudWatch log events and format them for Datadog."""
    processed_events = []
    
    for event in log_events:
        try:
            # Decode and parse the message
            message = event.get('message', '')
            parsed_data = parse_message(message)
            
            # Add CloudWatch metadata
            parsed_data.update({
                'timestamp': event.get('timestamp', ''),
                'cloudwatch': {
                    'log_group': context.get('log_group_name', ''),
                    'log_stream': context.get('log_stream_name', ''),
                    'aws_region': context.get('aws_region', '')
                }
            })
            
            processed_events.append(parsed_data)
            
        except Exception as e:
            # If parsing fails, send the raw event with error context
            processed_events.append({
                'message': event.get('message', ''),
                'timestamp': event.get('timestamp', ''),
                'status': 'error',
                'error': str(e),
                'ddsource': 'cloudwatch',
                'service': 'cloudwatch-logs',
                'ddtags': 'env:prod,source:cloudwatch,error:parse_failure'
            })
    
    return processed_events

def send_to_datadog(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Send logs to Datadog HTTP API using urllib."""
    api_key = get_api_key()
    dd_url = get_dd_url()
    
    headers = {
        'Content-Type': 'application/json',
        'DD-API-KEY': api_key
    }
    
    try:
        print(f"Sending {len(logs)} logs to Datadog at {dd_url}")
        print(f"Sample log entry: {json.dumps(logs[0], indent=2)}")
        
        data = json.dumps(logs).encode('utf-8')
        req = urllib.request.Request(
            dd_url,
            data=data,
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            response_text = response.read().decode('utf-8')
            status_code = response.status
            print(f"Datadog API response status: {status_code}")
            print(f"Datadog API response: {response_text}")
            
            return {
                'statusCode': status_code,
                'body': response_text,
                'error': response_text if status_code >= 400 else None
            }
            
    except urllib.error.HTTPError as e:
        error_text = e.read().decode('utf-8')
        print(f"HTTP Error sending logs to Datadog: {e.code} - {e.reason}")
        print(f"Response body: {error_text}")
        return {
            'statusCode': e.code,
            'body': error_text,
            'error': f"HTTP Error: {e.code} - {e.reason}"
        }
    except Exception as e:
        error_msg = str(e)
        print(f"Error sending logs to Datadog: {error_msg}")
        return {
            'statusCode': 500,
            'body': error_msg,
            'error': error_msg
        }

def health_check() -> Dict[str, Any]:
    """Check the health and configuration of the log forwarder."""
    health_status = {
        "healthy": True,
        "checks": {
            "secrets_manager": {
                "status": "ok",
                "details": "Secrets Manager configuration is valid"
            },
            "datadog_api": {
                "status": "ok",
                "details": "Datadog API configuration is valid"
            }
        }
    }

    # Check if DD_API_KEY_SECRET_ARN is set
    secret_arn = os.environ.get('DD_API_KEY_SECRET_ARN')
    if not secret_arn:
        health_status["healthy"] = False
        health_status["checks"]["secrets_manager"] = {
            "status": "error",
            "details": "DD_API_KEY_SECRET_ARN environment variable is not set"
        }
        return health_status

    # Check if DD_SITE is set
    dd_site = os.environ.get('DD_SITE', 'datadoghq.com')
    if not dd_site:
        health_status["healthy"] = False
        health_status["checks"]["datadog_api"] = {
            "status": "error",
            "details": "DD_SITE environment variable is not set"
        }

    return health_status

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler function."""
    print(f"Received event: {json.dumps(event)}")
    
    # Handle health check
    if event.get('healthCheck'):
        health_status = health_check()
        return {
            'statusCode': 200,
            'body': json.dumps(health_status)
        }

    # Process CloudWatch Logs
    if 'awslogs' not in event:
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid event format')
        }

    # Get API key
    try:
        api_key = get_api_key()
    except ValueError as e:
        print(f"Error getting API key: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error getting API key: {str(e)}")
        }

    # Decode and decompress CloudWatch logs
    data = base64.b64decode(event['awslogs']['data'])
    compressed_data = gzip.decompress(data)
    log_data = json.loads(compressed_data)

    # Get context from log data
    context_info = {
        'log_group_name': log_data.get('logGroup', ''),
        'log_stream_name': log_data.get('logStream', ''),
        'aws_region': log_data.get('awsRegion', '')
    }

    # Process log events
    processed_events = process_log_events(log_data.get('logEvents', []), context_info)

    # Send logs to Datadog
    send_to_datadog(processed_events)

    return {
        'statusCode': 200,
        'body': json.dumps('Successfully processed logs')
    }
