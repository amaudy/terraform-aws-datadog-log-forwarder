# Datadog Log Sender

Simple examples of sending logs to Datadog using Python and curl.

## Prerequisites

- Datadog account
- Datadog API key (set as environment variable `DD_API_KEY`)

## Quick Start

### Using Python

```python
import requests
import time
import os

DD_API_KEY = os.getenv('DD_API_KEY')
DD_URL = "https://http-intake.logs.datadoghq.com/api/v2/logs"

def send_log(status, message, attributes=None):
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DD_API_KEY
    }
    
    payload = {
        "ddsource": "python-script",
        "service": "my-app",
        "hostname": "my-host",
        "status": status,
        "message": message,
        "date": int(time.time() * 1000),  # milliseconds
        "ddtags": "env:prod,app:myapp"
    }
    
    # Add any additional attributes
    if attributes:
        payload.update(attributes)
    
    response = requests.post(DD_URL, headers=headers, json=[payload])
    return response.status_code == 202

# Example usage
send_log("info", "User logged in", {"user_id": "123"})
send_log("error", "Database connection failed", {
    "error_type": "ConnectionError",
    "database": "users_db"
})
```

### Using curl

```bash
# Info log
curl -X POST "https://http-intake.logs.datadoghq.com/api/v2/logs" \
     -H "Content-Type: application/json" \
     -H "DD-API-KEY: ${DD_API_KEY}" \
     -d @- << EOF
[{
  "ddsource": "curl",
  "service": "my-app",
  "hostname": "my-host",
  "status": "info",
  "message": "Test message",
  "ddtags": "env:prod,app:myapp"
}]
EOF

# Error log
curl -X POST "https://http-intake.logs.datadoghq.com/api/v2/logs" \
     -H "Content-Type: application/json" \
     -H "DD-API-KEY: ${DD_API_KEY}" \
     -d @- << EOF
[{
  "ddsource": "curl",
  "service": "my-app",
  "hostname": "my-host",
  "status": "error",
  "message": "Error occurred",
  "error": {
    "stack": "Error details here",
    "message": "Error occurred",
    "kind": "TypeError"
  }
}]
EOF
```

## Key Points

1. Required Fields:
   - `ddsource`: Source of the logs
   - `service`: Name of the service
   - `hostname`: Host generating the logs
   - `message`: Log message
   - `status`: Log level (error, warn, info, debug, trace)

2. Optional Fields:
   - `date`: Timestamp in milliseconds
   - `ddtags`: Tags for filtering
   - `error`: Error details (for error logs)

3. Status Codes:
   - 202: Log accepted
   - 403: Invalid API key
   - 429: Rate limit exceeded

## Rate Limiting

- Default: 5 logs per second
- Use time.sleep() or implement retry mechanism for higher volumes

For more examples and advanced usage, check `send_logs.py`.
