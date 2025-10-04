# tests/test_api_connection.py

import os
import sys
import json
import requests

# --- Persian: تنظیمات تست از متغیرهای محیطی خوانده می‌شود ---
# --- English: Test settings are read from environment variables ---
API_URL = os.environ.get("API_URL", "http://localhost:8080")
API_KEY = os.environ.get("API_KEY", "") # --- Persian: کلید API باید ست شود --- | --- English: API Key must be set

def run_api_test():
    """
    Persian: یک تست ساده برای اطمینان از صحت عملکرد API Gateway.
    English: A simple test to ensure the API Gateway is functioning correctly.
    """
    print(f"🧪 --- Running API test against: {API_URL} ---")

    if not API_KEY:
        print("❌ ERROR: API_KEY environment variable is not set. Cannot run test.")
        sys.exit(1)

    # --- Persian: داده‌های لازم برای فراخوانی تابع account_info ---
    # --- English: The necessary data to call the account_info function ---
    request_payload = {
        "function_name": "account_info"
    }

    # --- Persian: هدرهای درخواست، شامل کلید API ---
    # --- English: Request headers, including the API key ---
    request_headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY
    }

    try:
        # --- Persian: ارسال درخواست POST به endpoint ---
        # --- English: Sending a POST request to the endpoint ---
        response = requests.post(f"{API_URL}/rpc", headers=request_headers, json=request_payload, timeout=10)

        # --- Persian: بررسی کد وضعیت HTTP ---
        # --- English: Checking the HTTP status code ---
        if response.status_code != 200:
            print(f"❌ TEST FAILED: Received status code {response.status_code}")
            print(f"   Response: {response.text}")
            sys.exit(1)

        # --- Persian: بررسی محتوای پاسخ JSON ---
        # --- English: Checking the content of the JSON response ---
        response_data = response.json()

        assert response_data.get("status") == "success", "Response status is not 'success'"
        assert response_data.get("function_name") == "account_info", "Function name in response is incorrect"
        assert "data" in response_data, "Response is missing 'data' field"
        assert "login" in response_data["data"], "Account data is missing 'login' field"
        assert "balance" in response_data["data"], "Account data is missing 'balance' field"

        print("✅ --- TEST PASSED ---")
        print(f"Successfully connected and received account info for login: {response_data['data']['login']}")
        # print(json.dumps(response_data, indent=2)) # Uncomment to see the full response

    except requests.exceptions.ConnectionError as e:
        print(f"❌ TEST FAILED: Could not connect to the API Gateway at {API_URL}.")
        print(f"   Error: {e}")
        print("   Is the Docker container running and the port correctly mapped?")
        sys.exit(1)
    except Exception as e:
        print(f"❌ TEST FAILED: An unexpected error occurred.")
        print(f"   Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_api_test()