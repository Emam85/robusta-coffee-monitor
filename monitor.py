"""
Robusta Coffee Monitor - 24/7 Cloud Monitoring System
"""
import os
import json
import requests
from datetime import datetime
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from flask import Flask, jsonify

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO', EMAIL_FROM)

# Watchlist - ADDED ROBUSTA HERE
WATCHLIST = {
    'KC=F': 'Coffee Arabica (ICE)',
    'RC=F': 'Robusta Coffee (ICE)',  # <-- ADDED
    'CC=F': 'Cocoa (ICE)',
    'SB=F': 'Sugar (ICE)',
    'CT=F': 'Cotton (ICE)',
    'ZW=F': 'Wheat (CBOT)',
    'GC=F': 'Gold (COMEX)',
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def fetch_commodity_data(symbol):
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    try:
        return fetch_multi(symbol, WATCHLIST.get(symbol, symbol))
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return None

def generate_analysis(symbol, price_data):
    """Generate simple analysis using Gemini"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = f"""
        Act as a commodity trader. Analyze {price_data['name']} at price ${price_data['price']}.
        
        Return ONLY valid JSON:
        {{
            "trend": "UPTREND 🟢" or "DOWNTREND 🔴" or "SIDEWAYS 🟡",
            "prediction": "Price likely to reach $X next week",
            "action": "BUY" or "SELL" or "WAIT"
        }}
        """
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except:
        return {"trend": "UNKNOWN ⚪", "prediction": "No data", "action": "HOLD"}

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def monitor_all_commodities():
    print(f"\n🔄 Starting monitor cycle...")
    
    for symbol, name in WATCHLIST.items():
        print(f"Checking {name}...")
        data = fetch_commodity_data(symbol)
        
        if data:
            analysis = generate_analysis(symbol, data)
            
            # FORMAT MESSAGE WITH TREND
            msg = f"""
<b>{name}</b>
💰 <b>Price:</b> ${data['price']}
📊 <b>Trend:</b> {analysis['trend']}
🎯 <b>Action:</b> {analysis['action']}
🔮 <b>Forecast:</b> {analysis['prediction']}
"""
            send_telegram(msg)
            
    print("✅ Cycle complete")

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'online', 'watchlist': list(WATCHLIST.values())})

@app.route('/monitor')
def trigger_monitor():
    Thread(target=monitor_all_commodities).start()
    return jsonify({'status': 'started', 'message': 'Monitoring Robusta & others in background'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
