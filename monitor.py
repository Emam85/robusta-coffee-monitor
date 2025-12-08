"""
Robusta Coffee Monitor - 24/7 Cloud Monitoring System
Sends Telegram + Email notifications with AI-powered analysis
"""

import os
import json
import requests
from datetime import datetime, timedelta
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import io
import base64

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO', EMAIL_FROM)

# Working hours (Cairo timezone - EET)
WORK_START_HOUR = 0
WORK_END_HOUR = 23

# Watchlist symbols
WATCHLIST = {
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

def fetch_commodity_data(symbol, period='5d'):
    """Fetch commodity data from multiple sources with fallback"""
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    
    try:
        # Use multi-source fetcher
        data = fetch_multi(symbol, WATCHLIST.get(symbol, symbol))
        
        if data:
            # Ensure all required fields
            return {
                'symbol': data.get('symbol', symbol),
                'price': data.get('price', 0),
                'change': data.get('change', 0),
                'change_percent': data.get('change_percent', 0),
                'high': data.get('high', data.get('price', 0)),
                'low': data.get('low', data.get('price', 0)),
                'volume': data.get('volume', 0),
                'open': data.get('price', 0),
                'prev_close': data.get('price', 0) - data.get('change', 0),
                'timestamp': datetime.now().isoformat(),
                'name': WATCHLIST.get(symbol, symbol),
                'history': [data.get('price', 0)] * 20,
            }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    
    return None

def generate_price_targets(symbol, price_data, history):
    """Use Gemini AI to generate price targets and predictions"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        recent_prices = [round(p, 2) for p in history[-10:]]
        high_52w = max(history) if history else price_data['high']
        low_52w = min(history) if history else price_data['low']
        
        prompt = f"""As a commodity technical analyst, analyze {price_data['name']} and provide price targets.

Current Data:
- Price: ${price_data['price']}
- Change: {price_data['change']:+.2f} ({price_data['change_percent']:+.2f}%)
- High: ${price_data['high']} | Low: ${price_data['low']}
- 52W High: ${high_52w:.2f} | 52W Low: ${low_52w:.2f}
- Recent prices: {recent_prices}

Provide EXACTLY in this JSON format (no extra text):
{{
  "trend": "UPTREND/DOWNTREND/SIDEWAYS",
  "strength": "STRONG/MODERATE/WEAK",
  "targets": [
    {{"period": "1 week", "price": 4520, "probability": "high"}},
    {{"period": "2 weeks", "price": 4580, "probability": "medium"}},
    {{"period": "1 month", "price": 4650, "probability": "medium"}},
    {{"period": "3 months", "price": 4800, "probability": "low"}}
  ],
  "recommendation": "BUY/HOLD/SELL",
  "risk_level": "LOW/MEDIUM/HIGH",
  "key_insight": "One sentence insight",
  "support": 4400,
  "resistance": 4700
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
        print(f"Gemini analysis error: {e}")
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

def create_chart_ascii(price_data, analysis):
    """Create ASCII chart representation for notifications"""
    price = price_data['price']
    high = price_data['high']
    low = price_data['low']
    
    # Simple ASCII chart
    chart = f"""
📊 Price Movement
━━━━━━━━━━━━━━━━━━━━━━
High   ${high}  ━━━━━━━━┓
                      │
Price  ${price}   ━━━━●
                      │
Low    ${low}   ━━━━━━━━┛

Support    : ${analysis.get('support', low)}
Resistance : ${analysis.get('resistance', high)}
"""
    return chart

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
        print(f"Telegram error: {e}")
        return False

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
        print(f"Email error: {e}")
        return False

def format_telegram_message(symbol, price_data, analysis):
    """Format message for Telegram"""
    
    # Determine emoji
    if price_data['change_percent'] > 1:
        emoji = "🔥📈"
        alert = "STRONG INCREASE"
    elif price_data['change_percent'] > 0:
        emoji = "📈"
        alert = "Price Up"
    elif price_data['change_percent'] < -1:
        emoji = "⚠️📉"
        alert = "STRONG DECREASE"
    elif price_data['change_percent'] < 0:
        emoji = "📉"
        alert = "Price Down"
    else:
        emoji = "➡️"
        alert = "Stable"
    
    # Format targets
    targets_text = ""
    for i, target in enumerate(analysis.get('targets', [])[:3], 1):
        targets_text += f"  Target {i} ({target['period']}): ${target['price']} [{target['probability']}]\n"
    
    chart = create_chart_ascii(price_data, analysis)
    
    message = f"""
{emoji} <b>{price_data['name']}</b> {emoji}
<b>{alert}</b> | {datetime.now().strftime('%I:%M %p')}

💰 <b>Current Price:</b> ${price_data['price']}
📊 <b>Change:</b> {price_data['change']:+.2f} ({price_data['change_percent']:+.2f}%)
📈 <b>High:</b> ${price_data['high']} | 📉 <b>Low:</b> ${price_data['low']}
📦 <b>Volume:</b> {price_data['volume']:,}

🎯 <b>AI Price Targets:</b>
{targets_text}

🤖 <b>Analysis (Gemini):</b>
• Trend: <b>{analysis['trend']}</b> ({analysis['strength']})
• Recommendation: <b>{analysis['recommendation']}</b>
• Risk Level: <b>{analysis['risk_level']}</b>
• Insight: {analysis['key_insight']}
{chart}
━━━━━━━━━━━━━━━━━━━━━━
<i>Symbol: {symbol}</i>
"""
    return message

def format_email_html(watchlist_data):
    """Format comprehensive email with all watchlist data"""
    
    rows = ""
    for symbol, data in watchlist_data.items():
        price_data = data['price_data']
        analysis = data['analysis']
        
        color = '#10b981' if price_data['change'] >= 0 else '#ef4444'
        arrow = '▲' if price_data['change'] >= 0 else '▼'
        
        targets_html = "<br>".join([
            f"<small>{t['period']}: ${t['price']} ({t['probability']})</small>"
            for t in analysis.get('targets', [])[:3]
        ])
        
        rows += f"""
        <tr>
            <td style="padding: 15px; border-bottom: 1px solid #e5e7eb;">
                <strong>{price_data['name']}</strong><br>
                <small style="color: #6b7280;">{symbol}</small>
            </td>
            <td style="padding: 15px; border-bottom: 1px solid #e5e7eb;">
                <strong style="font-size: 1.2em;">${price_data['price']}</strong>
            </td>
            <td style="padding: 15px; border-bottom: 1px solid #e5e7eb; color: {color};">
                <strong>{arrow} {price_data['change']:+.2f}</strong><br>
                <small>({price_data['change_percent']:+.2f}%)</small>
            </td>
            <td style="padding: 15px; border-bottom: 1px solid #e5e7eb;">
                <strong>{analysis['recommendation']}</strong><br>
                <small>{analysis['trend']}</small>
            </td>
            <td style="padding: 15px; border-bottom: 1px solid #e5e7eb;">
                {targets_html}
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px;">
            <h1 style="margin: 0;">☕ Commodity Market Update</h1>
            <p style="margin: 10px 0 0 0; opacity: 0.9;">{datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}</p>
        </div>
        
        <table style="width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden;">
            <thead>
                <tr style="background: #f9fafb;">
                    <th style="padding: 15px; text-align: left; border-bottom: 2px solid #e5e7eb;">Commodity</th>
                    <th style="padding: 15px; text-align: left; border-bottom: 2px solid #e5e7eb;">Price</th>
                    <th style="padding: 15px; text-align: left; border-bottom: 2px solid #e5e7eb;">Change</th>
                    <th style="padding: 15px; text-align: left; border-bottom: 2px solid #e5e7eb;">Analysis</th>
                    <th style="padding: 15px; text-align: left; border-bottom: 2px solid #e5e7eb;">Targets</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        
        <div style="margin-top: 20px; padding: 20px; background: #f0f9ff; border-left: 4px solid #3b82f6; border-radius: 5px;">
            <p style="margin: 0;"><strong>🤖 Powered by Google Gemini AI</strong></p>
            <p style="margin: 5px 0 0 0; color: #6b7280; font-size: 0.9em;">Analysis updated every 10 minutes during working hours (8 AM - 5 PM)</p>
        </div>
        
        <div style="margin-top: 20px; text-align: center; color: #9ca3af; font-size: 0.85em;">
            <p>Robusta Coffee Monitor | Built with ❤️ using Python & AI</p>
        </div>
    </body>
    </html>
    """
    return html

def is_within_working_hours():
    """Check if current time is within working hours (Cairo timezone)"""
    current_hour = datetime.now().hour
    return WORK_START_HOUR <= current_hour < WORK_END_HOUR

def monitor_all_commodities():
    """Main monitoring function for all watchlist items"""
    
    if not is_within_working_hours():
        print(f"Outside working hours ({WORK_START_HOUR}:00 - {WORK_END_HOUR}:00)")
        return {'status': 'skipped', 'reason': 'outside_working_hours'}
    
    print(f"\n{'='*60}")
    print(f"🔄 Starting commodity monitor - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    watchlist_data = {}
    
    # Fetch data for all symbols
    for symbol in WATCHLIST:
        print(f"📊 Fetching {WATCHLIST[symbol]} ({symbol})...")
        
        price_data = fetch_commodity_data(symbol)
        if not price_data:
            print(f"   ❌ Failed to fetch data")
            continue
        
        print(f"   ✅ Price: ${price_data['price']} ({price_data['change_percent']:+.2f}%)")
        
        # Store history
        if symbol not in price_history:
            price_history[symbol] = []
        price_history[symbol].append(price_data['price'])
        if len(price_history[symbol]) > 100:
            price_history[symbol].pop(0)
        
        # Get AI analysis
        print(f"   🤖 Generating AI analysis...")
        analysis = generate_price_targets(symbol, price_data, price_history[symbol])
        print(f"   📈 Trend: {analysis['trend']} | Recommendation: {analysis['recommendation']}")
        
        watchlist_data[symbol] = {
            'price_data': price_data,
            'analysis': analysis
        }
        
        # Send individual Telegram notification for significant changes
        if abs(price_data['change_percent']) > 0.5:
            telegram_msg = format_telegram_message(symbol, price_data, analysis)
            if send_telegram_notification(telegram_msg):
                print(f"   ✅ Telegram notification sent")
            else:
                print(f"   ⚠️ Telegram notification failed")
    
    # Send comprehensive email with all data
    if watchlist_data and EMAIL_FROM and EMAIL_PASSWORD:
        print(f"\n📧 Sending comprehensive email report...")
        email_html = format_email_html(watchlist_data)
        subject = f"Commodity Market Update - {datetime.now().strftime('%I:%M %p')}"
        
        if send_email_notification(subject, email_html):
            print(f"   ✅ Email sent successfully")
        else:
            print(f"   ⚠️ Email failed")
    
    print(f"\n{'='*60}")
    print(f"✅ Monitor cycle complete - {len(watchlist_data)} commodities updated")
    print(f"{'='*60}\n")
    
    return {
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'commodities_updated': len(watchlist_data),
        'data': watchlist_data
    }

# Flask app for Render.com cron job
from flask import Flask, jsonify
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        'status': 'online',
        'service': 'Robusta Coffee Monitor',
        'watchlist': list(WATCHLIST.values())
    })

@app.route('/monitor')
def trigger_monitor():
    """Endpoint that Render cron job will call"""
    result = monitor_all_commodities()
    return jsonify(result)

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})


@app.route('/check')
def manual_check():
    """Manual trigger for monitoring cycle - runs in background"""
    def run_in_background():
        try:
            print("🔄 Manual check triggered via /check endpoint (background)")
            monitor_all_commodities()
            print("✅ Background monitoring completed")
        except Exception as e:
            print(f"❌ Error in background monitor: {e}")
            import traceback
            traceback.print_exc()
    
    # Start monitoring in background thread
    thread = Thread(target=run_in_background, daemon=True)
    thread.start()
    
    return jsonify({
        "status": "started",
        "message": "Monitoring cycle started in background",
        "note": "Check Telegram/Email in 30-60 seconds for notifications",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == '__main__':
    # For local testing
    if os.environ.get('LOCAL_TEST'):
        result = monitor_all_commodities()
        print(json.dumps(result, indent=2))
    else:
        # Run Flask server for Render
        port = int(os.environ.get('PORT', 10000))
        app.run(host='0.0.0.0', port=port)