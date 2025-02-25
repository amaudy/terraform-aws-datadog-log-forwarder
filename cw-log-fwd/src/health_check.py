import json
import os
import boto3
import urllib.request
import urllib.error
from typing import Dict, Any, Tuple

# Initialize AWS clients
secrets_client = boto3.client('secretsmanager', region_name='us-east-1')

def get_secret() -> Dict[str, str]:
    """Get secret from AWS Secrets Manager"""
    try:
        secret_arn = os.environ.get('DD_API_KEY_SECRET_ARN')
        if not secret_arn:
            raise ValueError("DD_API_KEY_SECRET_ARN environment variable not set")

        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response['SecretString'])
        return secret
    except Exception as e:
        print(f"Error getting secret: {str(e)}")
        raise

def get_api_key() -> str:
    """Get the Datadog API key from AWS Secrets Manager"""
    # First try environment variable
    api_key = os.environ.get('DD_API_KEY')
    if api_key:
        return api_key

    # Try AWS Secrets Manager
    try:
        secret = get_secret()
        api_key = secret.get('DD_API_KEY')
        if not api_key:
            raise ValueError("DD_API_KEY not found in secret")
        return api_key
    except Exception as e:
        raise ValueError(f"Failed to get API key: {str(e)}")

def get_dd_url() -> str:
    """Get the Datadog URL based on site configuration"""
    dd_site = os.environ.get('DD_SITE', 'datadoghq.com')
    return f"https://http-intake.logs.{dd_site}/api/v2/logs"

def check_dependencies() -> Tuple[bool, list]:
    """Check if all required dependencies are installed with correct versions"""
    required_packages = {
        'boto3': '1.20.0',
        'urllib3': '1.26.0'
    }
    
    missing = []
    for package, min_version in required_packages.items():
        try:
            import importlib
            module = importlib.import_module(package)
            if hasattr(module, '__version__'):
                if module.__version__ < min_version:
                    missing.append(f"{package} version {module.__version__} is lower than required {min_version}")
        except ImportError:
            missing.append(f"{package} is not installed")
    
    return len(missing) == 0, missing

def check_datadog_access() -> Tuple[bool, str]:
    """Check if we can access Datadog API."""
    try:
        api_key = get_api_key()
        dd_url = get_dd_url()
        
        # Test API access
        url = f"https://api.{dd_url}/api/v1/validate"
        request = urllib.request.Request(
            url,
            headers={
                "DD-API-KEY": api_key,
                "Content-Type": "application/json"
            }
        )
        
        with urllib.request.urlopen(request) as response:
            if response.status == 200:
                return True, "Successfully validated Datadog API key"
            else:
                return False, f"Failed to validate Datadog API key: HTTP {response.status}"
                
    except Exception as e:
        error_msg = str(e)
        if "DD_API_KEY_SECRET_ARN" in error_msg:
            return False, "DD_API_KEY_SECRET_ARN environment variable not set"
        elif "Access denied" in error_msg:
            raise  # Re-raise Secrets Manager access errors
        else:
            return False, f"Failed to get API key or URL: {error_msg}"

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Health check Lambda handler function."""
    try:
        # Check dependencies
        dependencies_status = check_dependencies()
        
        # Check Datadog access
        datadog_status = check_datadog_access()
        
        # Combine all checks
        all_checks = {
            'dependencies': {
                'status': 'ok' if dependencies_status[0] else 'error',
                'details': dependencies_status[1]
            },
            'datadog_access': {
                'status': 'ok' if datadog_status[0] else 'error',
                'details': datadog_status[1]
            }
        }
        
        # Determine overall status
        is_healthy = all(
            check.get('status') == 'ok' 
            for check in all_checks.values()
        )
        
        return {
            'statusCode': 200 if is_healthy else 500,
            'body': json.dumps({
                'status': 'ok' if is_healthy else 'error',
                'checks': all_checks,
                'error': None if is_healthy else next(
                    (details['details'] for details in all_checks.values() 
                     if details['status'] == 'error'),
                    'Unknown error'
                )
            })
        }
        
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': error_msg
            })
        }
