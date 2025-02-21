import requests
import time
import os
from datetime import datetime

# Datadog API configuration
DD_API_KEY = os.environ.get('DD_API_KEY')
DD_INTAKE_URL = "https://http-intake.logs.datadoghq.com/api/v2/logs"

# Common tags and attributes
COMMON_TAGS = "app_id:1234,app_name:dd-demo,env:development"

def send_log(status, message, additional_attributes=None):
    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DD_API_KEY
    }
    
    payload = {
        "ddsource": "python",
        "service": "log-simulator",
        "hostname": "local-test",
        "status": status,
        "ddtags": COMMON_TAGS,
        "message": message,
        "timestamp": int(time.time()),
    }
    
    if additional_attributes:
        payload["attributes"] = additional_attributes
        
    response = requests.post(DD_INTAKE_URL, headers=headers, json=payload)
    print(f"Sent {status} log: {message} - Status Code: {response.status_code}")
    return response.status_code

def simulate_logs():
    # ERROR log
    send_log("error", "Database connection failed", {
        "error_code": "DB_001",
        "connection_attempts": 3,
        "database": "users_db"
    })
    
    # WARN log
    send_log("warn", "High memory usage detected", {
        "memory_usage": "85%",
        "threshold": "80%",
        "process": "web_server"
    })
    
    # INFO log
    send_log("info", "User login successful", {
        "user_id": "12345",
        "login_method": "oauth",
        "ip_address": "192.168.1.1"
    })
    
    # DEBUG log
    send_log("debug", "Cache miss for user profile", {
        "cache_key": "user:12345:profile",
        "cache_type": "redis",
        "query_time_ms": 150
    })
    
    # TRACE log
    send_log("trace", "HTTP request processed", {
        "method": "GET",
        "path": "/api/v1/users",
        "processing_time_ms": 45,
        "response_size_bytes": 2048
    })

if __name__ == "__main__":
    if not DD_API_KEY:
        print("Error: DD_API_KEY environment variable not set")
        exit(1)
        
    print("Starting log simulation...")
    simulate_logs()
    print("Log simulation completed!")
