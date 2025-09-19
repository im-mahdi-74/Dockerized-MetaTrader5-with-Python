# reporter.py (نسخه نهایی با راه حل همگام‌سازی زمان و فیلدهای کامل)
import os
import time
import json
import logging
import sys
from datetime import datetime, timedelta
import pandas as pd
import MetaTrader5 as mt5
from flask import Flask, jsonify
from threading import Thread
from waitress import serve

# --- تنظیمات اولیه ---
MT5_ACCOUNT = int(os.environ.get("MT5_ACCOUNT", 0))
MT5_PASSWORD = os.environ.get("MT5_PASSWORD", "")
MT5_SERVER = os.environ.get("MT5_SERVER", "")
MT5_PATH = os.environ.get("MT5_PATH", r"C:\Program Files\meta\terminal64.exe")

# --- راه‌اندازی سیستم لاگینگ ---
log_formatter = logging.Formatter('%(asctime)s - REPORTER - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)

# --- وب سرور ---
health_app = Flask(__name__)

def initialize_mt5():
    """یک تابع کمکی برای برقراری اتصال که وضعیت را برمی‌گرداند"""
    logger.info("Attempting to initialize MetaTrader 5...")
    if not mt5.initialize(path=MT5_PATH, portable=True, login=MT5_ACCOUNT, password=MT5_PASSWORD, server=MT5_SERVER):
        logger.error(f"MT5 initialize() failed, error code: {mt5.last_error()}")
        mt5.shutdown()
        return False
    logger.info(f"Successfully initialized MT5 for account {MT5_ACCOUNT}")
    return True

@health_app.route('/health')
def health_check():
    if mt5.terminal_info():
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"status": "error", "message": "MT5 connection is not active"}), 503

@health_app.route('/history', methods=['GET'])
def get_history_endpoint():
    logger.info("HTTP request for history received.")
    # برخلاف نسخه قبل، دیگر نیازی به قطع و وصل اتصال نیست
    history_data = get_trade_history()
    logger.info(f"Returning {len(history_data)} history records via HTTP.")
    return jsonify({
        "type": "history_data",
        "account_number": MT5_ACCOUNT,
        "data": history_data
    }), 200

def run_health_check_server():
    serve(health_app, host='0.0.0.0', port=8080)

def get_trade_history():
    """
    تاریخچه معاملات را با استفاده از زمان سرور متاتریدر برای دقت بالا واکشی می‌کند.
    """
    logger.info("--- Starting get_trade_history (v6 with Server Time Sync) ---")
    try:
        # --- **راه حل هوشمندانه شما برای مشکل اختلاف زمانی** ---
        # یک نماد معاملاتی پرکاربرد را برای دریافت آخرین تیک انتخاب می‌کنیم
        symbol_for_time = "EURUSD" 
        last_tick = mt5.symbol_info_tick(symbol_for_time)
        
        if last_tick:
            # زمان حال را از سرور متاتریدر می‌گیریم
            to_date = datetime.fromtimestamp(last_tick.time)
            logger.info(f"Server time synchronized successfully using {symbol_for_time} tick: {to_date}")
        else:
            # اگر به هر دلیلی (مثل آخر هفته) تیکی وجود نداشت، به روش قبلی برمی‌گردیم و هشدار می‌دهیم
            to_date = datetime.now()
            logger.warning(f"Could not get last tick for {symbol_for_time}. Falling back to system time: {to_date}")
        
        from_date = to_date - timedelta(days=365)
        # ---------------------------------------------------------

        deals = mt5.history_deals_get(from_date, to_date)
        
        if not deals:
            logger.warning("mt5.history_deals_get returned no deals.")
            return []
        
        df = pd.DataFrame([d._asdict() for d in deals])
        if df.empty: return []

        ins = df[df['entry'] == 0].copy()
        outs = df[df['entry'] == 1].copy()
        if ins.empty or outs.empty: return []

        ins.rename(columns={'time': 'timeopen', 'price': 'priceopen', 'volume': 'volopen', 'ticket': 'ticket_in', 'type':'type_in'}, inplace=True)
        outs.rename(columns={'time': 'timeclose', 'price': 'priceclose', 'volume': 'volclose', 'ticket': 'ticket_out'}, inplace=True)
        
        merged = pd.merge(ins, outs, on='position_id', suffixes=('_in', '_out'))
        
        history_list = []
        for _, row in merged.iterrows():
            trade_type = "BUY" if row['type_in'] == mt5.ORDER_TYPE_BUY else "SELL"

            history_list.append({
                "position_id": int(row['position_id']),
                "ticket_in": int(row['ticket_in']),
                "ticket_out": int(row['ticket_out']),
                "type": trade_type, # <--- فیلد نوع معامله
                "timeopen": int(row['timeopen']), 
                "symbol": row.get('symbol_in', ''), 
                "volopen": row['volopen'], 
                "priceopen": row['priceopen'],
                "timeclose": int(row['timeclose']), 
                "volclose": row['volclose'], 
                "priceclose": row['priceclose'],
                "swap": row.get('swap_in', 0) + row.get('swap_out', 0),
                "commission": row.get('commission_in', 0) + row.get('commission_out', 0),
                "profit": row.get('profit_in', 0) + row.get('profit_out', 0),
                "comment": row.get('comment_in', '')
            })
        
        logger.info(f"Successfully processed and found {len(history_list)} closed trades.")
        return history_list

    except Exception as e:
        logger.exception(f"An exception occurred in get_trade_history: {e}")
        return []

if __name__ == "__main__":
    logger.info("Reporter bot starting up...")
    
    # سرور HTTP را در یک ترد جداگانه اجرا می‌کنیم
    health_thread = Thread(target=run_health_check_server, daemon=True)
    health_thread.start()
    logger.info("Health check and history HTTP server started on port 8080.")
    
    # یک اتصال اولیه و دائمی به متاتریدر برقرار می‌کنیم
    if not initialize_mt5():
        logger.critical("Could not initialize MT5. Reporter bot will exit.")
        sys.exit(1)
    
    logger.info("Reporter is running. Waiting for HTTP requests...")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Reporter bot stopped by user.")
    finally:
        logger.info("Shutting down MT5 connection.")
        mt5.shutdown()