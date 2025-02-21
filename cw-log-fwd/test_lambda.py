import json
import os
from src.lambda_function import lambda_handler

# Mock AWS Lambda context
class MockContext:
    def __init__(self):
        self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-function"

def test_lambda():
    # Load test event
    with open('test_event.json', 'r') as f:
        test_event = json.load(f)
    
    # Set environment variables
    os.environ['DD_API_KEY'] = 'your-api-key'  # Replace with your Datadog API key
    os.environ['DD_SITE'] = 'datadoghq.com'
    
    # Create mock context
    context = MockContext()
    
    # Run lambda handler
    try:
        result = lambda_handler(test_event, context)
        print("\nLambda execution result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"\nError executing lambda: {str(e)}")

if __name__ == "__main__":
    test_lambda()
