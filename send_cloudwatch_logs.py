import boto3
import json
import random
import time
import os
from datetime import datetime
from typing import Dict, Any, List

# CloudWatch Logs configuration
LOG_GROUP = '/poc/dd-log'
# Generate Lambda-style log stream name
current_date = datetime.now().strftime('%Y/%m/%d')
function_id = ''.join(random.choices('0123456789abcdef', k=32))
LOG_STREAM = f"{current_date}/[$LATEST]{function_id}"
REGION = 'us-east-1'

# Initialize CloudWatch Logs client
client = boto3.client('logs', region_name=REGION)

# Sample data for simulation
ENDPOINTS = [
    '/api/users',
    '/api/orders',
    '/api/products',
    '/api/cart',
    '/api/checkout'
]

HTTP_METHODS = ['GET', 'POST', 'PUT', 'DELETE']

# Status code distributions for realistic simulation
STATUS_CODES = {
    '2xx': [200, 201, 204],  # Success (70% probability)
    '4xx': [400, 401, 403, 404, 422],  # Client errors (20% probability)
    '5xx': [500, 502, 503]  # Server errors (10% probability)
}

ERROR_DETAILS = {
    400: {'error': 'Bad Request', 'exception': 'ValidationError: Invalid input'},
    401: {'error': 'Unauthorized', 'exception': 'AuthError: Invalid token'},
    403: {'error': 'Forbidden', 'exception': 'PermissionError: Insufficient privileges'},
    404: {'error': 'Not Found', 'exception': 'NotFoundError: Resource does not exist'},
    422: {'error': 'Unprocessable Entity', 'exception': 'ValidationError: Invalid field format'},
    500: {'error': 'Internal Server Error', 'exception': 'ServerError: Unexpected error occurred'},
    502: {'error': 'Bad Gateway', 'exception': 'GatewayError: Upstream service error'},
    503: {'error': 'Service Unavailable', 'exception': 'ServiceError: Database connection failed'}
}

def get_random_status_code() -> int:
    """Return a status code based on probability distribution."""
    rand = random.random()
    if rand < 0.7:  # 70% success
        return random.choice(STATUS_CODES['2xx'])
    elif rand < 0.9:  # 20% client errors
        return random.choice(STATUS_CODES['4xx'])
    else:  # 10% server errors
        return random.choice(STATUS_CODES['5xx'])

def generate_log_event() -> Dict[str, Any]:
    """Generate a single log event with realistic data."""
    status_code = get_random_status_code()
    endpoint = random.choice(ENDPOINTS)
    method = random.choice(HTTP_METHODS)
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    trace_id = f"trace_{random.randint(1000, 9999)}"
    request_id = f"req_{random.randint(10000, 99999)}"
    
    log_event = {
        "timestamp": timestamp,
        "level": "ERROR" if status_code >= 400 else "INFO",
        "logger": "fastapi",
        "path": endpoint,
        "method": method,
        "status_code": status_code,
        "trace_id": trace_id,
        "request_id": request_id,
        "response_time": random.randint(10, 1000),  # ms
        "client_ip": f"192.168.1.{random.randint(1, 255)}"
    }

    # Add error details for non-200 status codes
    if status_code >= 400:
        error_info = ERROR_DETAILS.get(status_code, ERROR_DETAILS[500])
        log_event.update(error_info)

    return log_event

def send_logs_to_cloudwatch(events: List[Dict[str, Any]], sequence_token: str = None) -> str:
    """Send logs to CloudWatch and return the next sequence token."""
    log_events = [{
        'timestamp': int(time.time() * 1000),
        'message': json.dumps(event)
    } for event in events]

    # Sort events by timestamp as required by CloudWatch
    log_events.sort(key=lambda x: x['timestamp'])

    kwargs = {
        'logGroupName': LOG_GROUP,
        'logStreamName': LOG_STREAM,
        'logEvents': log_events
    }

    if sequence_token:
        kwargs['sequenceToken'] = sequence_token

    response = client.put_log_events(**kwargs)
    return response['nextSequenceToken']

def create_log_stream():
    """Create the log stream if it doesn't exist."""
    try:
        client.create_log_stream(
            logGroupName=LOG_GROUP,
            logStreamName=LOG_STREAM
        )
        print(f"Created log stream: {LOG_STREAM}")
    except client.exceptions.ResourceAlreadyExistsException:
        print(f"Log stream {LOG_STREAM} already exists")

def simulate_logs(duration_seconds: int = 60, batch_size: int = 5, interval: float = 1.0):
    """Simulate logs for a specified duration."""
    print(f"Starting log simulation for {duration_seconds} seconds...")
    create_log_stream()
    
    sequence_token = None
    start_time = time.time()
    
    try:
        while time.time() - start_time < duration_seconds:
            events = [generate_log_event() for _ in range(batch_size)]
            sequence_token = send_logs_to_cloudwatch(events, sequence_token)
            
            # Print sample of sent logs
            print(f"\nSent {batch_size} logs. Sample log:")
            print(json.dumps(events[0], indent=2))
            
            time.sleep(interval)
    
    except KeyboardInterrupt:
        print("\nLog simulation stopped by user")
    except Exception as e:
        print(f"Error during simulation: {str(e)}")
    
    print("\nLog simulation completed")

if __name__ == "__main__":
    # Datadog configuration
    DD_API_KEY = os.environ.get('DD_API_KEY')
    if not DD_API_KEY:
        raise ValueError("DD_API_KEY environment variable is required")

    DD_SITE = os.environ.get('DD_SITE', 'datadoghq.com')
    
    # Simulate logs for 1 minute, sending 5 logs every second
    simulate_logs(duration_seconds=60, batch_size=5, interval=1.0)
