"""
Robusta Coffee Monitor - 24/7 Cloud Monitoring System
With Advanced AI Charting
"""
import os
import json
import requests
import random
import io
import matplotlib
matplotlib.use('Agg') # backend for non-GUI server
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from threading import Thread
from flask import Flask, jsonify

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO', EMAIL_FROM)

WATCHLIST = {
    'KC=F': 'Coffee Arabica (ICE)',
    'RC=F': 'Robusta Coffee (ICE)',
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
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = f"""
        Act as a professional commodity analyst. Analyze {price_data['name']} at price ${price_data['price']}.
        
        Return ONLY valid JSON:
        {{
            "trend": "UPTREND 🟢" or "DOWNTREND 🔴",
            "action": "BUY" or "SELL",
            "prediction": "Short text forecast",
            "target_1": {{"price": {price_data['price'] * 1.02}, "date": "1 Week"}},
            "target_2": {{"price": {price_data['price'] * 1.05}, "date": "2 Weeks"}},
            "target_3": {{"price": {price_data['price'] * 1.08}, "date": "1 Month"}}
        }}
        """
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except:
        # Fallback if AI fails
        p = price_data['price']
        return {
            "trend": "NEUTRAL 🟡", "action": "HOLD", "prediction": "Data unavailable",
            "target_1": {"price": p, "date": "1 Week"},
            "target_2": {"price": p, "date": "2 Weeks"},
            "target_3": {"price": p, "date": "1 Month"}
        }

def generate_chart_image(name, current_price, analysis):
    """Generates a chart image resembling the Expana dashboard"""
    try:
        plt.figure(figsize=(10, 6), facecolor='#f8f9fa')
        ax = plt.gca()
        ax.set_facecolor('white')
        
        # 1. Simulate recent history (since we don't have database yet)
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [current_price * (1 + random.uniform(-0.05, 0.05)) for _ in range(29)]
        prices.append(current_price) # Connect to current
        
        # 2. Plot History (Solid Line)
        plt.plot(dates, prices, color='#0ea5e9', linewidth=2, label='History')
        
        # 3. Plot AI Forecast (Dotted Line)
        forecast_dates = [
            datetime.now(),
            datetime.now() + timedelta(days=7),
            datetime.now() + timedelta(days=14),
            datetime.now() + timedelta(days=30)
        ]
        forecast_prices = [
            current_price,
            analysis['target_1']['price'],
            analysis['target_2']['price'],
            analysis['target_3']['price']
        ]
        
        plt.plot(forecast_dates, forecast_prices, color='#f97316', linestyle='--', linewidth=2, marker='o', label='AI Forecast')
        
        # 4. Add Labels to Targets (Like screenshot)
        for i, (d, p) in enumerate(zip(forecast_dates[1:], forecast_prices[1:])):
            plt.annotate(f"Target {i+1}\n${p:.0f}", (d, p), 
                         xytext=(0, 10), textcoords='offset points', 
                         ha='center', fontsize=9, 
                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#f97316", alpha=0.9))

        # Styling
        plt.title(f"{name} - AI Price Projection", fontsize=14, pad=20, fontweight='bold', color='#1f2937')
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='upper left')
        
        # Format dates
        plt.gcf().autofmt_xdate()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f"Chart error: {e}")
        return None

def send_telegram_photo(caption, image_buffer):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': ('chart.png', image_buffer, 'image/png')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        requests.post(url, data=data, files=files, timeout=20)
    except Exception as e:
        print(f"Telegram photo error: {e}")

def monitor_all_commodities():
    print(f"\n🔄 Starting monitor cycle...")
    
    for symbol, name in WATCHLIST.items():
        print(f"Checking {name}...")
        data = fetch_commodity_data(symbol)
        
        if data:
            analysis = generate_analysis(symbol, data)
            
            # Generate Chart
            chart_img = generate_chart_image(name, data['price'], analysis)
            
            # Message
            msg = f"""
<b>{name}</b>
💰 <b>Price:</b> ${data['price']}
📊 <b>Trend:</b> {analysis['trend']}
🎯 <b>Action:</b> {analysis['action']}
🔮 <b>AI Forecast:</b> {analysis['prediction']}
"""
            if chart_img:
                send_telegram_photo(msg, chart_img)
            
    print("✅ Cycle complete")

# Flask App
app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'online', 'watchlist': list(WATCHLIST.values())})

@app.route('/monitor')
def trigger_monitor():
    Thread(target=monitor_all_commodities).start()
    return jsonify({'status': 'started', 'message': 'Generating charts in background...'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
