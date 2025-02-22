import json
import os
import gzip
import base64
import pytest
from unittest.mock import patch, MagicMock
from src.lambda_function import lambda_handler, parse_message, health_check
from datetime import datetime, timezone
import urllib.request
import urllib.error
import boto3

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

@pytest.fixture
def mock_secrets_manager():
    with patch('src.lambda_function.secrets_client') as mock_client:
        mock_client.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'DD_API_KEY': 'test-secret-api-key'
            })
        }
        yield mock_client

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
def test_lambda_handler_success(mock_urlopen, context, mock_env, mock_secrets_manager):
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
def test_lambda_handler_api_error(mock_urlopen, context, mock_env, mock_secrets_manager):
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

def test_lambda_handler_missing_env(context, mock_secrets_manager):
    """Test handling of missing environment variables"""
    # Ensure DD_API_KEY is not set
    if 'DD_API_KEY' in os.environ:
        del os.environ['DD_API_KEY']
    
    # Make secret manager return empty secret
    mock_secrets_manager.get_secret_value.return_value = {
        'SecretString': json.dumps({})
    }
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": "Test message"
    }]
    
    event = create_cloudwatch_event(log_events)
    
    with pytest.raises(ValueError) as excinfo:
        lambda_handler(event, context)
    assert "DD_API_KEY not found in secret" in str(excinfo.value)

def test_lambda_handler_missing_env_and_secret(context, mock_secrets_manager):
    """Test handling of missing environment variables and secret"""
    # Ensure DD_API_KEY is not set
    if 'DD_API_KEY' in os.environ:
        del os.environ['DD_API_KEY']
    
    # Make secret manager return empty secret
    mock_secrets_manager.get_secret_value.return_value = {
        'SecretString': json.dumps({})
    }
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": "Test message"
    }]
    
    event = create_cloudwatch_event(log_events)
    
    with pytest.raises(ValueError) as excinfo:
        lambda_handler(event, context)
    assert "DD_API_KEY not found in secret" in str(excinfo.value)

@patch('urllib.request.urlopen')
def test_lambda_handler_network_error(mock_urlopen, context, mock_env, mock_secrets_manager):
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

def test_lambda_handler_secret_manager_error(context, mock_secrets_manager):
    """Test handling of Secrets Manager error"""
    # Ensure DD_API_KEY is not set
    if 'DD_API_KEY' in os.environ:
        del os.environ['DD_API_KEY']
    
    # Make secret manager raise an error
    mock_secrets_manager.get_secret_value.side_effect = Exception("Failed to get secret")
    
    log_events = [{
        "id": "event1",
        "timestamp": int(datetime.now(timezone.utc).timestamp() * 1000),
        "message": "Test message"
    }]
    
    event = create_cloudwatch_event(log_events)
    
    with pytest.raises(ValueError) as excinfo:
        lambda_handler(event, context)
    assert "Failed to retrieve secret" in str(excinfo.value)

@patch('urllib.request.urlopen')
@patch('boto3.session.Session')
def test_lambda_handler_health_check_success(mock_session, mock_urlopen, context, mock_env, mock_secrets_manager):
    """Test successful health check"""
    # Mock Secrets Manager
    mock_client = MagicMock()
    mock_session.return_value.client.return_value = mock_client

    # Mock API validation response
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response

    # Test health check
    event = {"source": "aws.health"}
    response = lambda_handler(event, context)
    
    assert response["healthy"]
    assert response["checks"]["api_key"]["status"] == "ok"
    assert response["checks"]["dd_site"]["status"] == "ok"
    assert response["checks"]["secrets_manager"]["status"] == "ok"

@patch('urllib.request.urlopen')
@patch('boto3.session.Session')
def test_lambda_handler_health_check_api_key_failure(mock_session, mock_urlopen, context, mock_env, mock_secrets_manager):
    """Test health check API key failure"""
    # Remove API key
    if "DD_API_KEY" in os.environ:
        del os.environ["DD_API_KEY"]

    # Mock Secrets Manager to return no key
    mock_client = MagicMock()
    mock_client.get_secret_value.side_effect = Exception("Secret not found")
    mock_session.return_value.client.return_value = mock_client

    # Test health check
    event = {"source": "aws.health"}
    response = lambda_handler(event, context)
    
    assert not response["healthy"]
    assert response["checks"]["api_key"]["status"] == "error"

@patch('boto3.session.Session')
def test_lambda_handler_health_check_secrets_manager_failure(mock_session, context, mock_env, mock_secrets_manager):
    """Test health check Secrets Manager failure"""
    # Mock Secrets Manager failure
    mock_client = MagicMock()
    mock_client.describe_secret.side_effect = Exception("Access denied")
    mock_session.return_value.client.return_value = mock_client

    # Test health check
    event = {"source": "aws.health"}
    response = lambda_handler(event, context)
    
    assert not response["healthy"]
    assert response["checks"]["secrets_manager"]["status"] == "error"

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
