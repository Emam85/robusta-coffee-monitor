"""
Robusta Coffee Monitor - Waterfall Edition
Features:
- 🌊 Intelligent Waterfall Scraper (Barchart → Investing.com)
- 🧠 Gemini AI Analysis
- 📱 Telegram Notifications
- 📧 Email Reports
- ⏰ Scheduled monitoring every 10 minutes
"""
import os
import json
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from flask import Flask, jsonify

# Import intelligent scrapers
try:
    from barchart_intelligent import get_barchart_robusta_jan26
    HAS_BARCHART = True
except ImportError:
    HAS_BARCHART = False
    print("⚠️ barchart_intelligent.py not found - using Investing.com only")
    def get_barchart_robusta_jan26():
        return None

from commodity_fetcher import fetch_commodity_data as fetch_from_investing

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO', EMAIL_FROM)

# Working hours (Cairo timezone)
WORK_START_HOUR = 6
WORK_END_HOUR = 18

# Watchlist symbols
WATCHLIST = {
    'RC=F': 'Robusta Coffee (ICE)',
    'KC=F': 'Coffee Arabica (ICE)',
    'CC=F': 'Cocoa (ICE)',
    'SB=F': 'Sugar (ICE)',
    'CT=F': 'Cotton (ICE)',
    'ZW=F': 'Wheat (CBOT)',
    'GC=F': 'Gold (COMEX)',
}

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# Price history storage (in-memory)
price_history = {}

# ============ DATA FETCHER WITH WATERFALL LOGIC ============
def fetch_commodity_data(symbol):
    """
    Intelligent data fetcher with waterfall logic
    - Robusta (RC=F): Try Barchart Jan'26 → Fallback to Investing.com
    - Others: Use Investing.com directly
    """
    
    # SPECIAL CASE: Robusta Coffee - Try Barchart first
    if symbol == 'RC=F':
        print(f"\n🌊 WATERFALL FETCH: Robusta Coffee")
        print("=" * 60)
        
        # Layer 1: Try Barchart (Jan '26 contract)
        if HAS_BARCHART:
            barchart_data = get_barchart_robusta_jan26()
            
            if barchart_data and barchart_data.get('price', 0) > 0:
                print(f"✅ Using Barchart data: ${barchart_data['price']}")
                print("=" * 60 + "\n")
                
                return {
                    'symbol': symbol,
                    'price': barchart_data['price'],
                    'change': barchart_data.get('change', 0),
                    'change_percent': barchart_data.get('percent', 0),
                    'high': barchart_data.get('high', barchart_data['price']),
                    'low': barchart_data.get('low', barchart_data['price']),
                    'volume': barchart_data.get('volume', 0),
                    'open': barchart_data['price'],
                    'prev_close': barchart_data['price'] - barchart_data.get('change', 0),
                    'timestamp': datetime.now().isoformat(),
                    'name': 'Robusta Coffee Jan 26 (Barchart)',
                    'history': [barchart_data['price']] * 20,
                    'source': barchart_data['source']
                }
        
        # Layer 2: Fallback to Investing.com
        print("⚠️ Barchart unavailable, using Investing.com fallback...")
        print("=" * 60 + "\n")
    
    # STANDARD CASE: All other commodities (and Robusta fallback)
    try:
        data = fetch_from_investing(symbol, WATCHLIST.get(symbol, symbol))
        
        if data:
            # Standardize format
            return {
                'symbol': data.get('symbol', symbol),
                'price': data.get('price', 0),
                'change': data.get('change', 0),
                'change_percent': data.get('percent', 0),
                'high': data.get('high', data.get('price', 0)),
                'low': data.get('low', data.get('price', 0)),
                'volume': data.get('volume', 0),
                'open': data.get('price', 0),
                'prev_close': data.get('price', 0) - data.get('change', 0),
                'timestamp': datetime.now().isoformat(),
                'name': WATCHLIST.get(symbol, symbol),
                'history': [data.get('price', 0)] * 20,
                'source': data.get('source', 'Unknown')
            }
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
    
    return None

# ============ AI ANALYSIS ============
def generate_price_targets(symbol, price_data, history):
    """Use Gemini AI to generate price targets and predictions"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        recent_prices = [round(p, 2) for p in history[-10:]] if history else [price_data['price']]
        high_52w = max(history) if history else price_data['high']
        low_52w = min(history) if history else price_data['low']
        
        prompt = f"""As a commodity technical analyst, analyze {price_data['name']} and provide price targets.

Current Data:
- Price: ${price_data['price']}
- Change: {price_data['change']:+.2f} ({price_data['change_percent']:+.2f}%)
- High: ${price_data['high']} | Low: ${price_data['low']}
- 52W High: ${high_52w:.2f} | 52W Low: ${low_52w:.2f}
- Recent prices: {recent_prices}
- Data source: {price_data.get('source', 'Market')}

Provide EXACTLY in this JSON format (no extra text):
{{
  "trend": "UPTREND/DOWNTREND/SIDEWAYS",
  "strength": "STRONG/MODERATE/WEAK",
  "targets": [
    {{"period": "1 week", "price": {price_data['price'] * 1.02}, "probability": "high"}},
    {{"period": "2 weeks", "price": {price_data['price'] * 1.04}, "probability": "medium"}},
    {{"period": "1 month", "price": {price_data['price'] * 1.06}, "probability": "medium"}}
  ],
  "recommendation": "BUY/HOLD/SELL",
  "risk_level": "LOW/MEDIUM/HIGH",
  "key_insight": "One sentence insight about market conditions",
  "support": {price_data['low']},
  "resistance": {price_data['high']}
}}"""
        
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Extract JSON from response
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0]
        elif '```' in text:
            text = text.split('```')[1].split('```')[0]
        
        analysis = json.loads(text)
        return analysis
        
    except Exception as e:
        print(f"⚠️ Gemini analysis error: {e}")
        return {
            'trend': 'UNKNOWN',
            'strength': 'MODERATE',
            'targets': [],
            'recommendation': 'HOLD',
            'risk_level': 'MEDIUM',
            'key_insight': 'AI analysis temporarily unavailable',
            'support': price_data['low'],
            'resistance': price_data['high']
        }

# ============ TELEGRAM NOTIFICATIONS ============
def send_telegram_notification(message):
    """Send notification via Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': True
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        return False

# ============ EMAIL NOTIFICATIONS ============
def send_email_notification(subject, html_content):
    """Send notification via Email"""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"❌ Email error: {e}")
        return False

# ============ FORMATTING ============
def format_telegram_message(price_data, analysis):
    """Format message for Telegram"""
    
    # Determine emoji based on change
    if price_data['change_percent'] > 1:
        emoji = "🔥📈"
        alert = "STRONG INCREASE"
    elif price_data['change_percent'] > 0:
        emoji = "📈"
        alert = "Price Up"
    elif price_data['change_percent'] < -1:
        emoji = "📉❄️"
        alert = "STRONG DECREASE"
    elif price_data['change_percent'] < 0:
        emoji = "📉"
        alert = "Price Down"
    else:
        emoji = "➡️"
        alert = "No Change"
    
    message = f"""
{emoji} <b>{price_data['name']} - {alert}</b>

💰 <b>Price:</b> ${price_data['price']:,.2f}
📊 <b>Change:</b> {price_data['change']:+.2f} ({price_data['change_percent']:+.2f}%)
📈 <b>High:</b> ${price_data['high']:,.2f} | <b>Low:</b> ${price_data['low']:,.2f}

🎯 <b>Analysis:</b>
• Trend: {analysis.get('trend', 'N/A')} ({analysis.get('strength', 'N/A')})
• Recommendation: {analysis.get('recommendation', 'HOLD')}
• Risk Level: {analysis.get('risk_level', 'MEDIUM')}

💡 <b>Insight:</b> {analysis.get('key_insight', 'No insight available')}

🔹 Support: ${analysis.get('support', price_data['low']):,.2f}
🔸 Resistance: ${analysis.get('resistance', price_data['high']):,.2f}

📅 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
🔗 Source: {price_data.get('source', 'Market Data')}
"""
    return message

# ============ MONITORING LOOP ============
def monitor_commodities():
    """Main monitoring function"""
    print("\n" + "="*60)
    print(f"🚀 Monitoring Cycle Started - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    for symbol, name in WATCHLIST.items():
        print(f"\n📊 Checking {name}...")
        
        # Fetch data
        price_data = fetch_commodity_data(symbol)
        
        if not price_data:
            print(f"  ⚠️ No data available for {symbol}")
            continue
        
        # Store in history
        if symbol not in price_history:
            price_history[symbol] = []
        price_history[symbol].append(price_data['price'])
        
        # Keep only last 100 records
        if len(price_history[symbol]) > 100:
            price_history[symbol] = price_history[symbol][-100:]
        
        # Generate AI analysis
        if GEMINI_API_KEY:
            analysis = generate_price_targets(symbol, price_data, price_history.get(symbol, []))
        else:
            analysis = {
                'trend': 'N/A',
                'strength': 'N/A',
                'recommendation': 'HOLD',
                'risk_level': 'MEDIUM',
                'key_insight': 'AI analysis not configured',
                'support': price_data['low'],
                'resistance': price_data['high']
            }
        
        # Send notification
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            message = format_telegram_message(price_data, analysis)
            send_telegram_notification(message)
        
        print(f"  ✅ {name}: ${price_data['price']:,.2f} | {analysis.get('recommendation', 'HOLD')}")
    
    print("\n" + "="*60)
    print("✅ Monitoring Cycle Completed")
    print("="*60 + "\n")

# ============ FLASK WEB SERVER ============
app = Flask(__name__)

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'online',
        'service': 'Robusta Coffee Monitor',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/monitor')
def trigger_monitor():
    """Manual trigger for monitoring"""
    Thread(target=monitor_commodities).start()
    return jsonify({'status': 'monitoring started'})

@app.route('/prices')
def get_prices():
    """Get current prices for all commodities"""
    prices = {}
    for symbol, name in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if data:
            prices[symbol] = {
                'name': name,
                'price': data['price'],
                'change': data['change'],
                'change_percent': data['change_percent'],
                'source': data.get('source', 'Unknown')
            }
    return jsonify(prices)

@app.route('/history/<symbol>')
def get_history(symbol):
    """Get price history for a specific symbol"""
    if symbol in price_history:
        return jsonify({
            'symbol': symbol,
            'name': WATCHLIST.get(symbol, symbol),
            'history': price_history[symbol]
        })
    return jsonify({'error': 'No history available'}), 404

# ============ MAIN ENTRY POINT ============
if __name__ == '__main__':
    print("🚀 Starting Robusta Coffee Monitor...")
    print(f"📊 Monitoring {len(WATCHLIST)} commodities")
    print(f"🔔 Telegram: {'Enabled' if TELEGRAM_BOT_TOKEN else 'Disabled'}")
    print(f"🧠 AI Analysis: {'Enabled' if GEMINI_API_KEY else 'Disabled'}")
    print("\n" + "="*60 + "\n")
    
    # Start Flask server
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)