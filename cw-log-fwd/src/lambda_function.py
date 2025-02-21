import base64
import gzip
import json
import os
import urllib.request
from typing import Dict, Any, List
from datetime import datetime

# Datadog configuration
DD_API_KEY = os.environ.get('DD_API_KEY')
DD_SITE = os.environ.get('DD_SITE', 'datadoghq.com')
DD_URL = f"https://http-intake.logs.{DD_SITE}/v1/input"

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
            "timestamp": datetime.utcnow().isoformat(),
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

def send_to_datadog(logs: List[Dict[str, Any]]) -> bool:
    """Send logs to Datadog HTTP API."""
    if not DD_API_KEY:
        raise ValueError("DD_API_KEY environment variable is not set")
    
    headers = {
        'Content-Type': 'application/json',
        'DD-API-KEY': DD_API_KEY
    }
    
    try:
        print(f"Sending {len(logs)} logs to Datadog at {DD_URL}")
        print(f"Sample log entry: {json.dumps(logs[0], indent=2)}")
        
        req = urllib.request.Request(
            DD_URL,
            data=json.dumps(logs).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        with urllib.request.urlopen(req) as response:
            response_data = response.read().decode('utf-8')
            print(f"Datadog API response status: {response.status}")
            print(f"Datadog API response: {response_data}")
            return response.status == 200
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error sending logs to Datadog: {e.code} - {e.reason}")
        print(f"Response body: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"Error sending logs to Datadog: {str(e)}")
        return False

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Main Lambda handler function."""
    # Print event for debugging
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # CloudWatch Logs data is compressed and base64 encoded
        compressed_payload = base64.b64decode(event['awslogs']['data'])
        uncompressed_payload = gzip.decompress(compressed_payload)
        log_data = json.loads(uncompressed_payload)
        
        # Extract context information
        context_info = {
            'log_group_name': log_data.get('logGroup', ''),
            'log_stream_name': log_data.get('logStream', ''),
            'aws_region': context.invoked_function_arn.split(':')[3]
        }
        
        # Process the log events
        processed_logs = process_log_events(log_data.get('logEvents', []), context_info)
        
        # Send to Datadog
        if processed_logs:
            success = send_to_datadog(processed_logs)
            if not success:
                raise Exception("Failed to send logs to Datadog")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Logs forwarded successfully',
                'logs_processed': len(processed_logs)
            })
        }
        
    except Exception as e:
        print(f"Error processing logs: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
