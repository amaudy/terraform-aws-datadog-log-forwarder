import json
import sys
import importlib
from typing import Dict, Any, List, Tuple

from lambda_function import get_api_key, get_dd_url

REQUIRED_PACKAGES = [
    ('boto3', '1.26.0'),
    ('urllib3', '1.26.0'),
]

def check_dependencies() -> Tuple[bool, List[str]]:
    """Check if all required dependencies are installed with correct versions"""
    missing_deps = []
    for package, min_version in REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(package)
            version = getattr(module, '__version__', '0.0.0')
            if version < min_version:
                missing_deps.append(f"{package} version {version} is lower than required {min_version}")
        except ImportError:
            missing_deps.append(f"{package} is not installed")
    return len(missing_deps) == 0, missing_deps

def check_datadog_access() -> Tuple[bool, str]:
    """Check if we can access Datadog API key and URL"""
    try:
        api_key = get_api_key()
        dd_url = get_dd_url()
        return True, "Successfully retrieved Datadog configuration"
    except Exception as e:
        return False, f"Failed to access Datadog configuration: {str(e)}"

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Health check Lambda handler"""
    health_status = {
        'healthy': True,
        'checks': {
            'dependencies': {
                'status': 'ok',
                'details': []
            },
            'datadog_access': {
                'status': 'ok',
                'details': ''
            }
        }
    }

    # Check dependencies
    deps_ok, missing_deps = check_dependencies()
    if not deps_ok:
        health_status['healthy'] = False
        health_status['checks']['dependencies'] = {
            'status': 'error',
            'details': missing_deps
        }

    # Check Datadog access
    dd_ok, dd_message = check_datadog_access()
    if not dd_ok:
        health_status['healthy'] = False
        health_status['checks']['datadog_access'] = {
            'status': 'error',
            'details': dd_message
        }

    # Set response status code based on health
    status_code = 200 if health_status['healthy'] else 500

    return {
        'statusCode': status_code,
        'body': json.dumps(health_status, indent=2)
    }
