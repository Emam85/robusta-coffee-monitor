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

# Working hours
WORK_START_HOUR = 0
WORK_END_HOUR = 23

# Watchlist
WATCHLIST = {
    'KC=F': 'Coffee Arabica (ICE)',
    'CC=F': 'Cocoa (ICE)',
    'SB=F': 'Sugar (ICE)',
    'CT=F': 'Cotton (ICE)',
    'ZW=F': 'Wheat (CBOT)',
    'GC=F': 'Gold (COMEX)',
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# History storage
price_history = {}

def fetch_commodity_data(symbol, period='5d'):
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    try:
        data = fetch_multi(symbol, WATCHLIST.get(symbol, symbol))
        if data:
            return {
                'symbol': data.get('symbol', symbol),
                'price': data.get('price', 0),
                'change': data.get('change', 0),
                'change_percent': data.get('change_percent', 0),
                'high': data.get('high', data.get('price', 0)),
                'low': data.get('low', data.get('price', 0)),
                'volume': data.get('volume', 0),
                'name': WATCHLIST.get(symbol, symbol),
            }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return None

def generate_price_targets(symbol, price_data):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = f"""Analyze {price_data['name']}. Price: ${price_data['price']}.
        Return JSON: {{"trend": "UP/DOWN", "recommendation": "BUY/SELL", "targets": [], "risk_level": "MED", "key_insight": "short text"}}"""
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except:
        return {'trend': 'UNKNOWN', 'recommendation': 'HOLD', 'risk_level': 'LOW', 'key_insight': 'AI unavailable', 'targets': []}

def send_telegram_notification(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        requests.post(url, json=payload, timeout=10)
        return True
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def send_email_notification(subject, html_content):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg.attach(MIMEText(html_content, 'html'))
        
        # FIX: Use Port 587 (TLS) instead of 465 (SSL)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def format_telegram_message(symbol, price_data, analysis):
    return f"""
📈 <b>{price_data['name']}</b>
💰 Price: ${price_data['price']}
📊 Trend: {analysis['trend']}
🤖 Rec: {analysis['recommendation']}
"""

def monitor_all_commodities():
    print(f"\n🔄 Starting monitor cycle...")
    watchlist_data = {}
    
    for symbol in WATCHLIST:
        print(f"Checking {symbol}...")
        price_data = fetch_commodity_data(symbol)
        if price_data:
            analysis = generate_price_targets(symbol, price_data)
            watchlist_data[symbol] = {'price_data': price_data, 'analysis': analysis}
            
            # Send Telegram
            msg = format_telegram_message(symbol, price_data, analysis)
            send_telegram_notification(msg)

    # Send Email
    if watchlist_data and EMAIL_FROM:
        print("📧 Sending email...")
        # Simple HTML for email
        html = "<h1>Market Update</h1>"
        for sym, data in watchlist_data.items():
            html += f"<p><b>{data['price_data']['name']}</b>: ${data['price_data']['price']} - {data['analysis']['recommendation']}</p>"
        send_email_notification("Commodity Update", html)
        
    print("✅ Cycle complete")
    return {'status': 'success', 'count': len(watchlist_data)}

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'online', 'service': 'Robusta Monitor'})

@app.route('/monitor')
def trigger_monitor():
    # FIX: Run in background thread to prevent Timeout
    thread = Thread(target=monitor_all_commodities)
    thread.start()
    return jsonify({'status': 'started', 'message': 'Monitoring running in background'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
