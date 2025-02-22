import json
import os
import gzip
import base64
import pytest
from unittest.mock import patch, MagicMock
from src.lambda_function import lambda_handler, parse_message
from datetime import datetime, timezone
import urllib.request
import urllib.error

# Mock AWS Lambda context
class MockContext:
    def __init__(self):
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"

@pytest.fixture
def context():
    return MockContext()

@pytest.fixture
def mock_env():
    os.environ['DD_API_KEY'] = 'test-api-key'
    os.environ['DD_SITE'] = 'datadoghq.com'
    yield
    # Clean up
    if 'DD_API_KEY' in os.environ:
        del os.environ['DD_API_KEY']

def create_cloudwatch_event(log_events):
    """Create a mock CloudWatch Logs event"""
    data = {
        "messageType": "DATA_MESSAGE",
        "owner": "123456789012",
        "logGroup": "/aws/lambda/test",
        "logStream": "2025/02/21/[$LATEST]",
        "subscriptionFilters": ["test-filter"],
        "logEvents": log_events
    }
    
    compressed = gzip.compress(json.dumps(data).encode('utf-8'))
    return {
        "awslogs": {
            "data": base64.b64encode(compressed).decode('utf-8')
        }
    }

def test_parse_message_json():
    """Test parsing a valid JSON message"""
    message = json.dumps({
        "level": "INFO",
        "path": "/api/users",
        "method": "GET",
        "status_code": 200
    })
    
    result = parse_message(message)
    
    assert result['ddsource'] == 'cloudwatch'
    assert 'app_id:fastapi-demo' in result['ddtags']
    assert 'app_name:fastapi-demo-app' in result['ddtags']
    assert result['host'] == 'simulator'
    assert result['app_id'] == 'fastapi-demo'
    assert result['app_name'] == 'fastapi-demo-app'

def test_parse_message_non_json():
    """Test parsing a non-JSON message"""
    message = "Plain text log message"
    
    result = parse_message(message)
    
    assert result['message'] == message
    assert result['ddsource'] == 'cloudwatch'
    assert 'app_id:fastapi-demo' in result['ddtags']
    assert result['host'] == 'simulator'

class MockResponse:
    def __init__(self, status=200, data=""):
        self.status = status
        self._data = data.encode('utf-8')

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

@patch('urllib.request.urlopen')
def test_lambda_handler_success(mock_urlopen, context, mock_env):
    """Test successful log forwarding"""
    mock_response = MockResponse(status=200, data="OK")
    mock_urlopen.return_value = mock_response
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": json.dumps({
            "level": "INFO",
            "path": "/api/users",
            "method": "GET",
            "status_code": 200
        })
    }]
    
    event = create_cloudwatch_event(log_events)
    result = lambda_handler(event, context)
    
    assert result['statusCode'] == 200
    assert mock_urlopen.called
    assert isinstance(mock_urlopen.call_args[0][0], urllib.request.Request)

@patch('urllib.request.urlopen')
def test_lambda_handler_api_error(mock_urlopen, context, mock_env):
    """Test handling of Datadog API error"""
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url='https://http-intake.logs.datadoghq.com/v1/input',
        code=403,
        msg='Forbidden',
        hdrs={},
        fp=None
    )
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": "Test message"
    }]
    
    event = create_cloudwatch_event(log_events)
    result = lambda_handler(event, context)
    
    assert result['statusCode'] == 403
    assert 'error' in result
    assert mock_urlopen.called

def test_lambda_handler_missing_env(context):
    """Test handling of missing environment variables"""
    # Ensure DD_API_KEY is not set
    if 'DD_API_KEY' in os.environ:
        del os.environ['DD_API_KEY']
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": "Test message"
    }]
    
    event = create_cloudwatch_event(log_events)
    
    with pytest.raises(ValueError) as excinfo:
        lambda_handler(event, context)
    assert "DD_API_KEY environment variable is not set" in str(excinfo.value)

@patch('urllib.request.urlopen')
def test_lambda_handler_network_error(mock_urlopen, context, mock_env):
    """Test handling of network errors"""
    mock_urlopen.side_effect = urllib.error.URLError('Network unreachable')
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": "Test message"
    }]
    
    event = create_cloudwatch_event(log_events)
    result = lambda_handler(event, context)
    
    assert result['statusCode'] == 500
    assert 'error' in result
    assert 'Network unreachable' in result['error']

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
