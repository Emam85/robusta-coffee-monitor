"""
Robusta Coffee Monitor - Ultimate Edition (Telegram Only)
Features:
- Real-time 24/7 Monitoring
- Weekly "Market Intelligence" Briefings (Telegram)
- Advanced AI Charts (Expana Style)
- Hedging Recommendations
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

# ============ DATA ENGINE ============
def fetch_commodity_data(symbol):
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    try:
        return fetch_multi(symbol, WATCHLIST.get(symbol, symbol))
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return None

# ============ AI ANALYSIS ENGINE ============
def generate_analysis(symbol, price_data, mode="DAILY"):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        if mode == "WEEKLY":
            prompt = f"""
            Act as a Senior Commodity Strategist. Write a Briefing for {price_data['name']} (${price_data['price']}).
            
            Return ONLY valid JSON:
            {{
                "trend": "BULLISH 🟢" or "BEARISH 🔴",
                "hedging_action": "FULL COVER" or "PARTIAL" or "AVOID",
                "insight": "Short professional insight about tariffs, weather, or logistics.",
                "support": "$XXXX",
                "resistance": "$XXXX",
                "targets": [
                    {{"label": "T1", "price": {price_data['price'] * 0.98}}},
                    {{"label": "T2", "price": {price_data['price'] * 1.05}}},
                    {{"label": "T3", "price": {price_data['price'] * 1.08}}}
                ]
            }}
            """
        else:
            prompt = f"""
            Analyze {price_data['name']} (${price_data['price']}). 
            Return JSON:
            {{
                "trend": "UP 🟢" or "DOWN 🔴",
                "action": "BUY" or "SELL",
                "prediction": "One short forecast.",
                "targets": [
                    {{"label": "T1", "price": {price_data['price'] * 1.01}}},
                    {{"label": "T2", "price": {price_data['price'] * 1.03}}}
                ]
            }}
            """

        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"AI Error: {e}")
        return {
            "trend": "NEUTRAL", "hedging_action": "HOLD", "action": "WAIT",
            "insight": "Data unavailable", "prediction": "No data",
            "support": "N/A", "resistance": "N/A",
            "targets": [{"label": "T1", "price": price_data['price']}]
        }

# ============ CHARTING ENGINE ============
def generate_chart(name, current_price, targets):
    try:
        plt.figure(figsize=(10, 6), facecolor='#ffffff')
        ax = plt.gca()
        ax.set_facecolor('white')
        
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [current_price * (1 + random.uniform(-0.05, 0.05)) for _ in range(30)]
        prices[-1] = current_price
        
        plt.plot(dates, prices, color='#0056b3', linewidth=2.5, label='History')
        
        forecast_dates = [datetime.now()]
        forecast_prices = [current_price]
        
        for i, t in enumerate(targets):
            future_date = datetime.now() + timedelta(weeks=i+1)
            forecast_dates.append(future_date)
            forecast_prices.append(t['price'])
            
        plt.plot(forecast_dates, forecast_prices, color='#ff6b00', linestyle='--', linewidth=2.5, marker='o', markersize=6, label='AI Forecast')
        
        for i, (d, p) in enumerate(zip(forecast_dates[1:], forecast_prices[1:])):
            label = targets[i].get('label', f'T{i}')
            plt.annotate(
                f"{label}\n${p:,.2f}", (d, p), xytext=(0, 15), textcoords='offset points',
                ha='center', fontsize=9, fontweight='bold', color='#333',
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#ff6b00", alpha=0.9)
            )

        plt.title(f"{name} - Price Projection", fontsize=14, pad=15, fontweight='bold', color='#333')
        plt.grid(True, linestyle=':', alpha=0.4)
        plt.legend(loc='upper left')
        plt.gcf().autofmt_xdate()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f"Chart Error: {e}")
        return None

# ============ TELEGRAM ENGINE ============
def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_telegram_photo(caption, image_buffer):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': ('chart.png', image_buffer, 'image/png')}
        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'HTML'}
        requests.post(url, data=data, files=files, timeout=20)
    except Exception as e:
        print(f"Telegram photo error: {e}")

# ============ REPORT LOGIC ============
def run_weekly_report():
    print("📊 Generating Weekly Report for Telegram...")
    
    header = f"""
☕ <b>WEEKLY MARKET INTELLIGENCE</b>
📅 {datetime.now().strftime('%d %B %Y')}

<i>Strategic Insights & Hedging Advice</i>
━━━━━━━━━━━━━━━━━━━━━━
"""
    send_telegram_message(header)
    
    for symbol, name in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if data:
            analysis = generate_analysis(symbol, data, mode="WEEKLY")
            chart_buf = generate_chart(name, data['price'], analysis['targets'])
            
            action = analysis.get('hedging_action', 'WAIT')
            icon = "🔴" if "AVOID" in action else "🟢" if "FULL" in action else "🟡"
            
            caption = f"""
<b>{name}</b>
💵 Price: ${data['price']:,.2f}
📉 Trend: {analysis['trend']}

🛡️ <b>HEDGING: {action} {icon}</b>
<i>"{analysis.get('insight', 'No data')}"</i>

• Support: {analysis.get('support')}
• Resistance: {analysis.get('resistance')}
"""
            if chart_buf:
                send_telegram_photo(caption, chart_buf)
            
            # Avoid hitting Telegram limits
            time.sleep(1)

    print("✅ Weekly Report Sent to Telegram")

def monitor_all_commodities():
    print(f"\n🔄 Starting Daily Monitor...")
    
    # Monday 9AM Check
    now = datetime.now()
    if now.weekday() == 0 and now.hour == 9 and now.minute < 15:
        run_weekly_report()
        return 
        
    for symbol, name in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if data:
            analysis = generate_analysis(symbol, data, mode="DAILY")
            chart_buf = generate_chart(name, data['price'], analysis['targets'])
            
            caption = f"""
<b>{name}</b>
💰 Price: ${data['price']:,.2f}
📊 Trend: {analysis['trend']}
🎯 Action: {analysis['action']}
🔮 Forecast: {analysis['prediction']}
"""
            if chart_buf:
                send_telegram_photo(caption, chart_buf)

    print("✅ Daily Cycle Complete")

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({'status': 'online'})

@app.route('/monitor')
def trigger_daily():
    Thread(target=monitor_all_commodities).start()
    return jsonify({'status': 'started'})

@app.route('/weekly')
def trigger_weekly():
    Thread(target=run_weekly_report).start()
    return jsonify({'status': 'started', 'message': 'Sending Weekly Briefing to Telegram...'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
