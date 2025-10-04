# api_gateway.py

import os
import sys
import json
import logging
import functools
from datetime import datetime
import pandas as pd
import MetaTrader5 as mt5
from flask import Flask, request, jsonify
from waitress import serve

# --- Persian: تنظیمات اولیه از متغیرهای محیطی ---
# --- English: Initial settings from environment variables ---
MT5_ACCOUNT = int(os.environ.get("MT5_ACCOUNT", 0))
MT5_PASSWORD = os.environ.get("MT5_PASSWORD", "")
MT5_SERVER = os.environ.get("MT5_SERVER", "")
MT5_PATH = os.environ.get("MT5_PATH", r"C:\Program Files\meta\terminal64.exe")
API_KEY = os.environ.get("API_KEY", "") # --- Persian: کلید امنیتی جدید --- | --- English: The new security key ---

# --- Persian: لیست توابع ممنوعه برای جلوگیری از تغییر اتصال ---
# --- English: List of disallowed functions to prevent connection tampering ---
DISALLOWED_FUNCTIONS = ['initialize', 'login', 'shutdown']

# --- Persian: راه‌اندازی سیستم لاگینگ ---
# --- English: Setting up the logging system ---
log_formatter = logging.Formatter('%(asctime)s - API_GATEWAY - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

# --- Persian: راه‌اندازی وب سرور فلسک ---
# --- English: Initializing the Flask web server ---
app = Flask(__name__)

# --- Persian: تابع کمکی هوشمند و جهانی برای تبدیل انواع داده به JSON ---
# --- English: Smart and universal helper function to convert data types to JSON ---
def custom_json_encoder(obj):
    # --- Persian: اول از همه، سعی می‌کنیم آبجکت را به دیکشنری تبدیل کنیم. اکثر خروجی‌های mt5 این متد را دارند ---
    # --- English: First of all, try to convert the object to a dictionary. Most mt5 outputs have this method ---
    if hasattr(obj, '_asdict'):
        return obj._asdict()
    
    # --- Persian: اگر دیتافریم پانداز بود، آن را به لیست دیکشنری‌ها تبدیل کن ---
    # --- English: If it's a pandas DataFrame, convert it to a list of dictionaries ---
    if isinstance(obj, pd.DataFrame):
        return obj.to_dict(orient='records')

    # --- Persian: اگر تاریخ و زمان بود، به فرمت استاندارد ISO تبدیل کن ---
    # --- English: If it's a datetime object, convert it to standard ISO format ---
    if isinstance(obj, datetime):
        return obj.isoformat()

    # --- Persian: برای انواع دیگری که ممکن است _asdict نداشته باشند ---
    # --- English: For other types that might not have _asdict ---
    if hasattr(obj, '__dict__'):
        return obj.__dict__
        
    # --- Persian: اگر هیچ‌کدام نبود، اجازه می‌دهیم خطا رخ دهد تا متوجه نوع داده جدید شویم ---
    # --- English: If none of the above, let the error occur so we become aware of a new data type ---
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


# --- Persian: دکوراتور برای چک کردن API Key در هدر درخواست ---
# --- English: Decorator to check for the API Key in the request header ---
def require_api_key(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # --- Persian: هدر 'X-API-KEY' را بررسی می‌کنیم ---
        # --- English: We check the 'X-API-KEY' header ---
        if 'X-API-KEY' in request.headers and request.headers['X-API-KEY'] == API_KEY:
            return f(*args, **kwargs)
        else:
            logger.warning("Unauthorized access attempt detected.")
            return jsonify({"status": "error", "message": "Unauthorized: API Key is missing or invalid"}), 401
    return decorated_function

@app.route('/health')
def health_check():
    # --- Persian: وضعیت اتصال به ترمینال را برمی‌گرداند ---
    # --- English: Returns the connection status to the terminal ---
    if mt5.terminal_info():
        return jsonify({"status": "ok", "account": mt5.account_info().login}), 200
    else:
        return jsonify({"status": "error", "message": "MT5 connection is not active"}), 503

@app.route('/rpc', methods=['POST'])
@require_api_key
def rpc_handler():
    # --- Persian: بدنه درخواست JSON را دریافت می‌کند ---
    # --- English: Receives the JSON request body ---
    try:
        req_data = request.get_json()
        function_name = req_data.get('function_name')
        args = req_data.get('args', [])
        kwargs = req_data.get('kwargs', {})
    except Exception as e:
        logger.error(f"Invalid JSON request: {e}")
        return jsonify({"status": "error", "message": f"Invalid JSON request: {e}"}), 400

    logger.info(f"Received RPC call for function: '{function_name}'")

    # --- Persian: چک کردن اینکه آیا تابع فراخوانی شده مجاز است یا خیر ---
    # --- English: Check if the called function is allowed ---
    if function_name in DISALLOWED_FUNCTIONS:
        logger.warning(f"Attempt to call disallowed function: {function_name}")
        return jsonify({
            "status": "error",
            "function_name": function_name,
            "message": "Connection management functions are not allowed via RPC."
        }), 403 # 403 Forbidden

    # --- Persian: پیدا کردن و اجرای دینامیک تابع از کتابخانه mt5 ---
    # --- English: Dynamically find and execute the function from the mt5 library ---
    try:
        mt5_function = getattr(mt5, function_name)
        result = mt5_function(*args, **kwargs)

        # ------------------- START: THE DEFINITIVE FIX -------------------
        # --- Persian: اینجا به صورت دستی و پیشگیرانه نتیجه را به فرمت صحیح تبدیل می‌کنیم ---
        # --- English: Here we manually and proactively convert the result to the correct format ---
        
        final_result = result
        # --- Persian: اگر نتیجه یک آبجکت تکی با متد _asdict بود (مثل account_info) ---
        # --- English: If the result is a single object with the _asdict method (like account_info) ---
        if hasattr(result, '_asdict'):
            final_result = result._asdict()
        # --- Persian: اگر نتیجه یک لیست یا تاپل از آبجکت‌ها بود (مثل history_deals_get) ---
        # --- English: If the result is a list or tuple of objects (like history_deals_get) ---
        elif isinstance(result, (list, tuple)):
            final_result = [item._asdict() if hasattr(item, '_asdict') else item for item in result]

        # --- Persian: حالا json.dumps را روی نتیجه‌ای که خودمان فرمت کرده‌ایم، اجرا می‌کنیم ---
        # --- English: Now we run json.dumps on the result that we have formatted ourselves ---
        json_result = json.loads(json.dumps(final_result, default=custom_json_encoder))
        # -------------------- END: THE DEFINITIVE FIX --------------------

        logger.info(f"Successfully executed '{function_name}'.")
        return jsonify({
            "status": "success",
            "function_name": function_name,
            "data": json_result
        })

    except AttributeError:
        logger.error(f"Function '{function_name}' not found in MetaTrader5 library.")
        return jsonify({
            "status": "error",
            "function_name": function_name,
            "message": f"Function '{function_name}' not found in MetaTrader5 library."
        }), 404 # 404 Not Found
    except Exception as e:
        last_error = mt5.last_error()
        logger.error(f"An error occurred while executing '{function_name}': {e}. MT5 Last Error: {last_error}")
        return jsonify({
            "status": "error",
            "function_name": function_name,
            "message": str(e),
            "mt5_last_error": str(last_error)
        }), 500 # 500 Internal Server Error

if __name__ == "__main__":
    logger.info("API Gateway starting up...")

    # --- Persian: بررسی وجود کلید API قبل از راه‌اندازی ---
    # --- English: Check for API_KEY existence before starting ---
    if not API_KEY:
        logger.critical("CRITICAL: API_KEY environment variable is not set. Exiting.")
        sys.exit(1)
    
    # --- Persian: اتصال اولیه و دائمی به متاتریدر ---
    # --- English: Initial and persistent connection to MetaTrader ---
    if not mt5.initialize(path=MT5_PATH, portable=True, login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logger.critical(f"MT5 initialize() failed, error code: {mt5.last_error()}. Exiting.")
        mt5.shutdown()
        sys.exit(1)
    
    logger.info(f"Successfully connected to MT5 account {MT5_ACCOUNT}.")
    logger.info("API Gateway is running. Waiting for HTTP requests on port 8080...")
    
    try:
        # --- Persian: اجرای وب سرور با Waitress که برای پروداکشن مناسب‌تر است ---
        # --- English: Running the web server with Waitress, which is more suitable for production ---
        serve(app, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        logger.info("API Gateway stopped by user.")
    finally:
        logger.info("Shutting down MT5 connection.")
        mt5.shutdown()