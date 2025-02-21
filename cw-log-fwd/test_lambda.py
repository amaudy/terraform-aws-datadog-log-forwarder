import json
import os
import gzip
import base64
import pytest
from unittest.mock import patch, MagicMock
from src.lambda_function import lambda_handler, parse_message
from datetime import datetime, timezone

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

@patch('requests.post')
def test_lambda_handler_success(mock_post, context, mock_env):
    """Test successful log forwarding"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    
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
    assert mock_post.called
    mock_post.assert_called_once()

@patch('requests.post')
def test_lambda_handler_api_error(mock_post, context, mock_env):
    """Test handling of Datadog API error"""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"
    mock_post.return_value = mock_response
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": "Test message"
    }]
    
    event = create_cloudwatch_event(log_events)
    result = lambda_handler(event, context)
    
    assert result['statusCode'] == 403
    assert 'error' in result
    assert mock_post.called

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

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
