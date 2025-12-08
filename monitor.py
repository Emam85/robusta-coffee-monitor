"""
Robusta Coffee Monitor - 24/7 Cloud Monitoring System
Includes:
1. Gemini 2.0 AI Analysis
2. Investing.com Data (Robusta/Arabica)
3. Matplotlib Chart Generation
4. Email Fix (Port 587)
"""
import os
import json
import requests
import random
import io
import matplotlib
matplotlib.use('Agg') # backend for non-GUI server
import matplotlib.pyplot as plt
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

# Watchlist
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
        p = price_data['price']
        return {
            "trend": "NEUTRAL 🟡", "action": "HOLD", "prediction": "Data unavailable",
            "target_1": {"price": p, "date": "1 Week"},
            "target_2": {"price": p, "date": "2 Weeks"},
            "target_3": {"price": p, "date": "1 Month"}
        }

def generate_chart_image(name, current_price, analysis):
    """Generates the advanced chart"""
    try:
        plt.figure(figsize=(10, 6), facecolor='#f8f9fa')
        ax = plt.gca()
        ax.set_facecolor('white')
        
        # Simulate History
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [current_price * (1 + random.uniform(-0.05, 0.05)) for _ in range(29)]
        prices.append(current_price)
        
        # Plot History
        plt.plot(dates, prices, color='#0ea5e9', linewidth=2, label='History')
        
        # Plot Forecast
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
        
        # Labels
        for i, (d, p) in enumerate(zip(forecast_dates[1:], forecast_prices[1:])):
            plt.annotate(f"Target {i+1}\n${p:.0f}", (d, p), 
                         xytext=(0, 10), textcoords='offset points', 
                         ha='center', fontsize=9, 
                         bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#f97316", alpha=0.9))

        plt.title(f"{name} - AI Price Projection", fontsize=14, pad=20, fontweight='bold', color='#1f2937')
        plt.grid(True, linestyle=':', alpha=0.6)
        plt.legend(loc='upper left')
        plt.gcf().autofmt_xdate()
        
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

def send_email_notification(subject, html_content):
    """Sends email using Port 587 (TLS) to fix Network Unreachable error"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO  # Handles multiple emails automatically
        msg.attach(MIMEText(html_content, 'html'))
        
        # === CRITICAL FIX: Use Port 587 ===
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def monitor_all_commodities():
    print(f"\n🔄 Starting monitor cycle...")
    watchlist_data = {}
    
    for symbol, name in WATCHLIST.items():
        print(f"Checking {name}...")
        data = fetch_commodity_data(symbol)
        
        if data:
            analysis = generate_analysis(symbol, data)
            chart_img = generate_chart_image(name, data['price'], analysis)
            
            # Store for email
            watchlist_data[symbol] = {'price_data': data, 'analysis': analysis}
            
            # Telegram with Chart
            msg = f"""
<b>{name}</b>
💰 <b>Price:</b> ${data['price']}
📊 <b>Trend:</b> {analysis['trend']}
🎯 <b>Action:</b> {analysis['action']}
🔮 <b>Forecast:</b> {analysis['prediction']}
"""
            if chart_img:
                send_telegram_photo(msg, chart_img)
    
    # Send Summary Email
    if watchlist_data and EMAIL_FROM:
        print("📧 Sending email...")
        html = "<h1>Commodity Market Update</h1><table border='1' cellpadding='5' style='border-collapse:collapse;'>"
        html += "<tr><th>Commodity</th><th>Price</th><th>Trend</th><th>Action</th></tr>"
        for sym, data in watchlist_data.items():
            html += f"<tr><td>{data['price_data']['name']}</td><td>${data['price_data']['price']}</td><td>{data['analysis']['trend']}</td><td>{data['analysis']['action']}</td></tr>"
        html += "</table>"
        
        if send_email_notification("Detailed Market Report", html):
            print("✅ Email sent successfully")
        else:
            print("⚠️ Email failed")
            
    print("✅ Cycle complete")

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
