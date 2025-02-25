import json
import os
import pytest
from unittest.mock import patch, MagicMock
from src.health_check import lambda_handler, check_dependencies, check_datadog_access

@pytest.fixture
def mock_env():
    os.environ['DD_API_KEY'] = 'test-api-key'
    os.environ['DD_SITE'] = 'datadoghq.com'
    yield
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

def test_check_dependencies_success():
    """Test successful dependency check"""
    ok, missing = check_dependencies()
    assert ok is True
    assert len(missing) == 0

@patch('importlib.import_module')
def test_check_dependencies_missing(mock_import):
    """Test dependency check with missing package"""
    mock_import.side_effect = ImportError("No module named 'missing_package'")
    ok, missing = check_dependencies()
    assert ok is False
    assert len(missing) > 0
    assert "is not installed" in missing[0]

@patch('importlib.import_module')
def test_check_dependencies_old_version(mock_import):
    """Test dependency check with old version"""
    mock_module = MagicMock()
    mock_module.__version__ = '0.1.0'
    mock_import.return_value = mock_module
    ok, missing = check_dependencies()
    assert ok is False
    assert len(missing) > 0
    assert "is lower than required" in missing[0]

@patch('urllib.request.urlopen')
def test_check_datadog_access_success(mock_urlopen, mock_env):
    """Test successful Datadog access check"""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    ok, message = check_datadog_access()
    assert ok is True
    assert "Successfully" in message

def test_check_datadog_access_failure(mock_secrets_manager):
    """Test Datadog access check with missing configuration"""
    if 'DD_API_KEY' in os.environ:
        del os.environ['DD_API_KEY']
    mock_secrets_manager.get_secret_value.return_value = {
        'SecretString': json.dumps({})
    }
    ok, message = check_datadog_access()
    assert ok is False
    assert "DD_API_KEY_SECRET_ARN" in message

@patch('urllib.request.urlopen')
def test_lambda_handler_success(mock_urlopen, mock_env):
    """Test successful health check"""
    mock_response = MagicMock()
    mock_response.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = lambda_handler({}, None)
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['status'] == 'ok'
    assert all(check['status'] == 'ok' for check in body['checks'].values())

def test_lambda_handler_failure(mock_secrets_manager):
    """Test health check with failures"""
    if 'DD_API_KEY' in os.environ:
        del os.environ['DD_API_KEY']
    mock_secrets_manager.get_secret_value.return_value = {
        'SecretString': json.dumps({})
    }

    with patch('importlib.import_module') as mock_import:
        mock_import.side_effect = ImportError("No module named 'missing_package'")
        result = lambda_handler({}, None)

    assert result['statusCode'] == 500
    body = json.loads(result['body'])
    assert body['status'] == 'error'
    assert any(check['status'] == 'error' for check in body['checks'].values())

if __name__ == "__main__":
    pytest.main([__file__, '-v'])
