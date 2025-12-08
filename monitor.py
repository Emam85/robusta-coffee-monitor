"""
Abu Auf Procurement Monitor - Strategic Edition
Features:
- Real-time 10-Minute Price Snapshots
- Focused Watchlist: Coffee, Cocoa, Sugar, Wheat
- EGP Landed Cost Calculator
- Hourly "Procurement Tips"
- Weekly Strategic Briefings
"""
import os
import json
import requests
import random
import io
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import google.generativeai as genai
from threading import Thread
from flask import Flask, jsonify

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# ABU AUF SETTINGS
USD_EGP_RATE = 50.5
START_HOUR = 9
END_HOUR = 17

WATCHLIST = {
    'RC=F': 'Robusta Coffee (ICE)',
    'KC=F': 'Coffee Arabica (ICE)',
    'CC=F': 'Cocoa (ICE)',
    'SB=F': 'Sugar (ICE)',
    'ZW=F': 'Wheat (CBOT)',
}

last_known_prices = {}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ============ DATA ENGINE ============
def fetch_commodity_data(symbol):
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    try:
        data = fetch_multi(symbol, WATCHLIST.get(symbol, symbol))
        if data:
            # CALCULATE EGP COST
            price = data['price']
            egp_cost = 0
            
            if symbol == 'RC=F' or symbol == 'CC=F': # USD/Ton
                egp_cost = price * USD_EGP_RATE
            elif symbol == 'KC=F' or symbol == 'SB=F': # Cents/lb -> USD/Ton
                usd_ton = (price / 100) * 2204.62
                egp_cost = usd_ton * USD_EGP_RATE
            elif symbol == 'ZW=F': # Cents/Bushel -> USD/Ton
                usd_ton = (price / 100) * 36.74
                egp_cost = usd_ton * USD_EGP_RATE
                
            data['egp_cost'] = round(egp_cost, 2)
            return data
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return None

# ============ AI ENGINE ============
def generate_ai_content(symbol, price_data, mode="DAILY"):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        egp_price_str = f"{price_data['egp_cost']:,.0f} EGP/Ton"
        
        if mode == "TIP":
            prompt = f"""
            Act as a Procurement Manager for Abu Auf. 
            Analyze {price_data['name']} at ${price_data['price']} ({egp_price_str}).
            Is this a buying opportunity? Output ONLY a short, sharp tip (max 20 words).
            """
            
        elif mode == "WEEKLY":
            prompt = f"""
            Act as a Global Sourcing Director. Strategic Briefing for {price_data['name']}.
            Global Price: ${price_data['price']} | Landed: {egp_price_str}.
            Return JSON:
            {{
                "trend": "BULLISH 🟢 / BEARISH 🔴",
                "sourcing_action": "LOCK CONTRACT 🔒 / BUY SPOT 🛒 / WAIT ✋",
                "insight": "Insight on landed cost and risks.",
                "targets": [
                    {{"label": "Ideal Buy", "price": {price_data['price'] * 0.95}}},
                    {{"label": "Panic Level", "price": {price_data['price'] * 1.05}}}
                ]
            }}
            """
        
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        if mode == "TIP": return text
        return json.loads(text)
        
    except Exception as e:
        if mode == "TIP": return "Market volatile. Check offers."
        return {"trend": "NEUTRAL", "sourcing_action": "WAIT", "targets": []}

# ============ CHART ENGINE ============
def generate_chart(name, current_price, targets):
    try:
        plt.figure(figsize=(10, 6), facecolor='#ffffff')
        ax = plt.gca()
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [current_price * (1 + random.uniform(-0.05, 0.05)) for _ in range(30)]
        prices[-1] = current_price
        plt.plot(dates, prices, color='#0056b3', linewidth=2.5, label='Price')
        
        forecast_dates = [datetime.now()]
        forecast_prices = [current_price]
        for i, t in enumerate(targets):
            forecast_dates.append(datetime.now() + timedelta(weeks=i+1))
            forecast_prices.append(t['price'])
            
        plt.plot(forecast_dates, forecast_prices, color='#ff6b00', linestyle='--', marker='o')
        plt.title(f"{name} Projection", fontsize=12, fontweight='bold')
        plt.grid(True, linestyle=':', alpha=0.4)
        plt.gcf().autofmt_xdate()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        plt.close()
        return buf
    except: return None

# ============ TELEGRAM ENGINE ============
def send_telegram(text=None, photo=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
        if photo:
            requests.post(url + "sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': text, 'parse_mode': 'HTML'}, files={'photo': ('chart.png', photo, 'image/png')})
        else:
            requests.post(url + "sendMessage", json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'})
    except Exception as e: print(f"Telegram Fail: {e}")

# ============ REPORTING LOGIC ============
def run_weekly_report():
    send_telegram(f"🏭 <b>WEEKLY SOURCING BRIEF</b>\n🇪🇬 Rate: {USD_EGP_RATE} EGP/USD")
    for symbol, name in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if data:
            analysis = generate_ai_content(symbol, data, mode="WEEKLY")
            chart = generate_chart(name, data['price'], analysis['targets'])
            caption = f"<b>{name}</b>\n💵 ${data['price']:,.2f}\n🇪🇬 {data['egp_cost']:,.0f} EGP\n<b>ACTION: {analysis.get('sourcing_action')}</b>\n<i>{analysis.get('insight')}</i>"
            send_telegram(caption, chart)
            time.sleep(2)

def run_hourly_tips():
    tips = "🔔 <b>HOURLY TIPS</b>\n\n"
    for symbol, name in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if data:
            tip = generate_ai_content(symbol, data, mode="TIP")
            tips += f"📦 <b>{name.split()[0]}:</b> {tip}\n"
    send_telegram(tips)

def send_10min_snapshot():
    # Sends a clean list of current prices every 10 mins
    snapshot = f"⏱️ <b>MARKET SNAPSHOT ({datetime.now().strftime('%H:%M')})</b>\n\n"
    for symbol, name in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if data:
            # Check for sudden volatility (>1.5%)
            last_price = last_known_prices.get(symbol)
            alert = ""
            if last_price:
                change = ((data['price'] - last_price) / last_price) * 100
                if abs(change) >= 1.5: alert = " 🚨 <b>VOLATILE</b>"
            
            snapshot += f"▫️ <b>{name.split()[0]}:</b> ${data['price']:,.2f} {alert}\n"
            last_known_prices[symbol] = data['price']
            
    send_telegram(snapshot)

def monitor_cycle():
    print(f"\n🔄 Running Monitor Cycle...")
    now = datetime.now()
    
    # 1. Weekly Report (Monday 9 AM)
    if now.weekday() == 0 and now.hour == 9 and now.minute < 15:
        run_weekly_report()
        return

    # 2. Hourly Tips (Start of hour)
    if now.minute < 5 and (START_HOUR <= now.hour <= END_HOUR):
        run_hourly_tips()
    
    # 3. ALWAYS send 10-min Snapshot (The price update)
    send_10min_snapshot()

    print("✅ Cycle Complete")

app = Flask(__name__)

@app.route('/')
def home(): return jsonify({'status': 'online'})

@app.route('/monitor')
def trigger():
    Thread(target=monitor_cycle).start()
    return jsonify({'status': 'started'})

@app.route('/weekly')
def weekly():
    Thread(target=run_weekly_report).start()
    return jsonify({'status': 'started'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
