import requests
import time
import os
from datetime import datetime
import json
from typing import Dict, Any

# Datadog API configuration
DD_API_KEY = os.environ.get('DD_API_KEY')
DD_INTAKE_URL = "https://http-intake.logs.datadoghq.com/api/v2/logs"

# Common tags and attributes
COMMON_TAGS = "app_id:1234,app_name:dd-demo,env:production"

# Rate limiting configuration
RATE_LIMIT_LOGS_PER_SECOND = 5  # Maximum logs per second
RATE_LIMIT_RETRY_AFTER = 2      # Seconds to wait after hitting rate limit
MAX_RETRIES = 3                 # Maximum number of retries per log

class LogStats:
    def __init__(self):
        self.total_sent = 0
        self.successful = 0
        self.failed = 0
        self.rate_limited = 0
        self.last_send_time = 0

log_stats = LogStats()

def handle_rate_limit(retry_after: int = None) -> None:
    """Handle rate limiting by waiting appropriate time"""
    wait_time = retry_after if retry_after else RATE_LIMIT_RETRY_AFTER
    print(f"\nRate limit hit. Waiting {wait_time} seconds...")
    time.sleep(wait_time)

def send_log(status: str, message: str, additional_attributes: Dict[str, Any] = None) -> bool:
    if not DD_API_KEY:
        print("Error: DD_API_KEY environment variable is not set or empty")
        print("Current DD_API_KEY value:", DD_API_KEY)
        return False

    # Ensure we don't exceed rate limit
    time_since_last = time.time() - log_stats.last_send_time
    if time_since_last < 1.0 / RATE_LIMIT_LOGS_PER_SECOND:
        sleep_time = (1.0 / RATE_LIMIT_LOGS_PER_SECOND) - time_since_last
        time.sleep(sleep_time)

    headers = {
        "Content-Type": "application/json",
        "DD-API-KEY": DD_API_KEY
    }
    
    payload = {
        "ddsource": "python-script",
        "service": "error-monitoring",
        "hostname": "app-server-01",
        "status": status,
        "ddtags": COMMON_TAGS,
        "message": message
    }
    
    # Add timestamp in milliseconds
    payload["date"] = int(time.time() * 1000)
    
    if status == "error":
        error_obj = {
            "stack": additional_attributes.get("stack_trace", "No stack trace available"),
            "message": message,
            "kind": additional_attributes.get("error_type", "UnknownError")
        }
        payload["error"] = error_obj
        
        # Move error details to the root level for better visibility
        if additional_attributes:
            payload.update({
                "error_type": additional_attributes.get("error_type"),
                "error_code": additional_attributes.get("error_code"),
                "http_status": additional_attributes.get("http_status")
            })
    
    # Add custom attributes at root level for better indexing
    if additional_attributes:
        for key, value in additional_attributes.items():
            if key not in ["stack_trace", "error_type", "error_code", "http_status"]:
                payload[key] = value

    for attempt in range(MAX_RETRIES):
        try:
            print(f"\nSending log (attempt {attempt + 1}/{MAX_RETRIES}):")
            print(json.dumps(payload, indent=2))
            print(f"\nUsing headers:")
            print(f"DD-API-KEY: {'*' * 8}{DD_API_KEY[-4:] if DD_API_KEY else 'None'}")
            
            response = requests.post(DD_INTAKE_URL, headers=headers, json=payload)
            print(f"\nResponse Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
            
            log_stats.total_sent += 1
            log_stats.last_send_time = time.time()

            if response.status_code == 202:
                log_stats.successful += 1
                return True
            elif response.status_code == 429:  # Rate limit hit
                log_stats.rate_limited += 1
                retry_after = int(response.headers.get('Retry-After', RATE_LIMIT_RETRY_AFTER))
                handle_rate_limit(retry_after)
                continue
            else:
                print(f"Warning: Unexpected status code {response.status_code}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(1)  # Wait before retry
                    continue
                log_stats.failed += 1
                return False

        except requests.exceptions.RequestException as e:
            print(f"Error sending log: {str(e)}")
            log_stats.failed += 1
            if attempt < MAX_RETRIES - 1:
                time.sleep(1)  # Wait before retry
                continue
            return False

    return False

def simulate_logs():
    # Test log to verify connectivity
    success = send_log("info", "Test connection to Datadog", {
        "test": True,
        "timestamp": datetime.now().isoformat()
    })
    
    if not success:
        print("\nInitial test log failed. Please check your DD_API_KEY and connectivity.")
        return
    
    # ERROR log
    send_log("error", "Database connection failed", {
        "error_code": "DB_001",
        "connection_attempts": 3,
        "database": "users_db"
    })
    
    time.sleep(1)  # Add small delay between logs
    
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

def simulate_500_errors():
    # Database connection error with improved error details
    send_log("error", "Internal Server Error: Database Query Failed", {
        "error_type": "DatabaseError",
        "stack_trace": "Error: Connection refused at Database.query (/app/db.js:15)",
        "http_status": 500,
        "error_code": "DB_ERROR_001",
        "query_type": "SELECT",
        "table": "users",
        "response_time": 5000,
        "database_name": "users_db",
        "query_id": "q_123456"
    })
    
    time.sleep(1)
    
    # Memory overflow error
    send_log("error", "Internal Server Error: Memory limit exceeded", {
        "error_type": "MemoryError",
        "stack_trace": "Error: OutOfMemory: JavaScript heap out of memory at /app/server.js:123",
        "http_status": 500,
        "error_code": "MEM_ERROR_001",
        "memory_usage_mb": 2048,
        "memory_limit_mb": 2000,
        "process_id": "server_123",
        "host_memory_total": "8GB",
        "host_memory_free": "100MB"
    })
    
    time.sleep(1)
    
    # Payment processing error
    send_log("error", "Payment Processing Failed", {
        "error_type": "PaymentError",
        "stack_trace": "TypeError: Cannot read property 'amount' of undefined at PaymentProcessor.charge (/app/payments.js:89)",
        "http_status": 500,
        "error_code": "PAY_ERROR_001",
        "transaction_id": "tx_789012",
        "payment_provider": "Stripe",
        "amount": 999.99,
        "currency": "USD",
        "customer_id": "cust_456",
        "payment_method": "credit_card"
    })

def print_stats():
    print("\nLog Sending Statistics:")
    print(f"Total logs attempted: {log_stats.total_sent}")
    print(f"Successful: {log_stats.successful}")
    print(f"Failed: {log_stats.failed}")
    print(f"Rate limited: {log_stats.rate_limited}")

if __name__ == "__main__":
    if not DD_API_KEY:
        print("Error: DD_API_KEY environment variable not set")
        exit(1)
        
    print("Starting log simulation...")
    print(f"Using Datadog URL: {DD_INTAKE_URL}")
    print(f"Rate limit configuration: {RATE_LIMIT_LOGS_PER_SECOND} logs per second")
    
    print("\nSending 500 error logs...")
    simulate_500_errors()
    
    print("\nSending other logs...")
    simulate_logs()
    
    print_stats()
    print("\nLog simulation completed!")
