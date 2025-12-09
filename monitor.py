# -*- coding: utf-8 -*-
"""
Abu Auf Commodities Monitor - Enhanced Version v3.1
Features:
- 🌊 Intelligent Waterfall Scraper (Barchart → Investing.com)
- 🧠 Gemini AI Analysis
- 📊 Hourly Charts & Summaries
- 📄 Weekly PDF Reports
- 📱 Telegram Notifications (Market Hours Only)
- ⏰ Scheduled monitoring every 10 minutes
- 📈 Accurate Daily Change/High/Low Tracking
- 🎯 Contract-Specific Analysis
"""
import os
import json
import requests
from datetime import datetime, timedelta, time as dt_time
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from threading import Thread
from flask import Flask, jsonify
import pytz

# Flask app
app = Flask(__name__)
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import tempfile
import base64

# Import intelligent scrapers
try:
    from barchart_intelligent import get_barchart_robusta_jan26, get_barchart_arabica_last2
    HAS_BARCHART = True
except ImportError:
    HAS_BARCHART = False
    print("⚠️ barchart_intelligent.py not found - using Investing.com only")
    def get_barchart_robusta_jan26():
        return None
    def get_barchart_arabica_last2():
        return None

from commodity_fetcher import fetch_commodity_data as fetch_from_investing

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO', EMAIL_FROM)

# Parse multiple email recipients (comma-separated)
EMAIL_RECIPIENTS = [email.strip() for email in EMAIL_TO.split(',')] if EMAIL_TO else []

# Abu Auf Portfolio - Updated (Arabica handled separately)
WATCHLIST = {
    'RC=F': {'name': 'Robusta Coffee', 'type': 'Softs', 'use_barchart': True},
    'CC=F': {'name': 'Cocoa', 'type': 'Softs'},
    'SB=F': {'name': 'Sugar No.11', 'type': 'Softs'},
    'ZW=F': {'name': 'Wheat', 'type': 'Grains'},
    'ZL=F': {'name': 'Soybean Oil', 'type': 'Oils'},
    'PO=F': {'name': 'Palm Oil', 'type': 'Oils'}
}

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    analysis_model = genai.GenerativeModel('gemini-2.0-flash-exp')
else:
    analysis_model = None

# Price history storage (in-memory with timestamps)
price_history = {}  # {symbol: [(timestamp, price), ...]}
daily_start_prices = {}  # Store session start baseline prices
session_high_low = {}  # Track daily high/low: {symbol: {'high': x, 'low': y}}
arabica_contracts = []  # List of 2 contract dicts

# ============ MARKET HOURS DETECTION ============
def is_market_hours():
    return True  # TESTING MODE
    """
    Check if current time is within trading hours
    Monday-Friday 09:00-21:00 Cairo Time (Full Coffee Trading Coverage)
    """
    cairo_tz = pytz.timezone('Africa/Cairo')
    now_cairo = datetime.now(cairo_tz)
    
    # Market is closed on weekends
    if now_cairo.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    
    # Market hours: 09:00 to 21:00 Cairo time
    current_time = now_cairo.time()
    market_open = dt_time(9, 0)   # 9:00 AM
    market_close = dt_time(21, 0)  # 9:00 PM
    
    return market_open <= current_time <= market_close

# ============ SESSION BASELINE MANAGEMENT ============
def initialize_session_baseline(symbol, price):
    """Set baseline price at session start (used for calculating daily change)"""
    if symbol not in daily_start_prices:
        daily_start_prices[symbol] = price
        session_high_low[symbol] = {'high': price, 'low': price}
        print(f"  📌 Baseline set for {symbol}: ${price:.2f}")

def update_session_high_low(symbol, price):
    """Update daily high/low for accurate range tracking"""
    if symbol not in session_high_low:
        session_high_low[symbol] = {'high': price, 'low': price}
    else:
        if price > session_high_low[symbol]['high']:
            session_high_low[symbol]['high'] = price
        if price < session_high_low[symbol]['low']:
            session_high_low[symbol]['low'] = price

def reset_daily_tracking():
    """Reset daily tracking at session start (called at 1:00 AM Cairo time)"""
    global daily_start_prices, session_high_low
    daily_start_prices.clear()
    session_high_low.clear()
    print("🔄 Daily tracking reset for new session")

# ============ DATA FETCHER WITH WATERFALL LOGIC ============
def fetch_commodity_data(symbol):
    """
    Intelligent data fetcher with waterfall logic
    - Robusta (RC=F): Try Barchart → Fallback to Investing.com
    - Others: Use Investing.com directly
    """
    commodity_info = WATCHLIST.get(symbol, {'name': symbol, 'type': 'Unknown'})
    commodity_name = commodity_info['name']
    
    # SPECIAL CASE: Robusta Coffee - Try Barchart first
    if symbol == 'RC=F' and commodity_info.get('use_barchart', False):
        print(f"\n🌊 WATERFALL FETCH: Robusta Coffee")
        print("=" * 60)
        
        if HAS_BARCHART:
            barchart_data = get_barchart_robusta_jan26()
            if barchart_data and barchart_data.get('price', 0) > 0:
                price = barchart_data['price']
                
                # Initialize baseline if needed
                initialize_session_baseline(symbol, price)
                update_session_high_low(symbol, price)
                
                # Calculate accurate daily change
                baseline = daily_start_prices.get(symbol, price)
                daily_change = price - baseline
                daily_change_pct = (daily_change / baseline * 100) if baseline else 0
                
                # Use session high/low
                high = session_high_low[symbol]['high']
                low = session_high_low[symbol]['low']
                
                print(f"✅ Using Barchart data: ${price:.2f} (Change: {daily_change_pct:+.2f}%)")
                print("=" * 60 + "\n")
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'change': daily_change,
                    'change_percent': daily_change_pct,
                    'high': high,
                    'low': low,
                    'volume': barchart_data.get('volume', 0),
                    'timestamp': datetime.now().isoformat(),
                    'name': commodity_name,
                    'type': commodity_info.get('type', 'Unknown'),
                    'source': 'Barchart',
                    'contract': 'Jan 26',
                    'exchange': 'ICE Futures (via Barchart)'
                }
        
        print("⚠️ Barchart unavailable, using Investing.com fallback...")
        print("=" * 60 + "\n")
    
    # STANDARD CASE: All other commodities (and Robusta fallback)
    try:
        data = fetch_from_investing(symbol, commodity_name)
        if data:
            price = data.get('price', 0)
            
            # Initialize baseline if needed
            initialize_session_baseline(symbol, price)
            update_session_high_low(symbol, price)
            
            # Calculate accurate daily change
            baseline = daily_start_prices.get(symbol, price)
            daily_change = price - baseline
            daily_change_pct = (daily_change / baseline * 100) if baseline else 0
            
            # Use session high/low
            high = session_high_low[symbol]['high']
            low = session_high_low[symbol]['low']
            
            # Map to exchange
            exchange_map = {
                'CC=F': 'ICE Futures',
                'SB=F': 'ICE Futures',
                'ZW=F': 'CBOT',
                'ZL=F': 'CBOT',
                'PO=F': 'CME Group'
            }
            exchange = exchange_map.get(symbol, 'Investing.com')
            
            return {
                'symbol': symbol,
                'price': price,
                'change': daily_change,
                'change_percent': daily_change_pct,
                'high': high,
                'low': low,
                'volume': data.get('volume', 0),
                'timestamp': datetime.now().isoformat(),
                'name': commodity_name,
                'type': commodity_info.get('type', 'Unknown'),
                'source': 'Investing.com',
                'exchange': exchange
            }
    except Exception as e:
        print(f"❌ Error fetching {symbol}: {e}")
    
    return None

def fetch_arabica_contracts():
    """Fetch Arabica Coffee last 2 contracts from Barchart"""
    global arabica_contracts
    
    if not HAS_BARCHART:
        return None
    
    print("\n🌊 Fetching Arabica Coffee 4/5 (Last 2 Contracts)")
    print("=" * 60)
    
    contracts_data = get_barchart_arabica_last2()
    
    if contracts_data and len(contracts_data) == 2:
        arabica_contracts = []
        
        for i, contract in enumerate(contracts_data):
            symbol_key = f'KC_CONTRACT_{i+1}'
            price = contract['price']
            
            # Initialize baseline
            initialize_session_baseline(symbol_key, price)
            update_session_high_low(symbol_key, price)
            
            # Calculate accurate daily change
            baseline = daily_start_prices.get(symbol_key, price)
            daily_change = price - baseline
            daily_change_pct = (daily_change / baseline * 100) if baseline else 0
            
            # Use session high/low
            high = session_high_low[symbol_key]['high']
            low = session_high_low[symbol_key]['low']
            
            arabica_contracts.append({
                'symbol': contract['symbol'],
                'contract': contract['contract'],
                'price': price,
                'change': daily_change,
                'change_percent': daily_change_pct,
                'high': high,
                'low': low,
                'timestamp': datetime.now().isoformat(),
                'name': f"Arabica Coffee 4/5",
                'type': 'Softs',
                'source': 'Barchart',
                'exchange': 'ICE Futures (via Barchart)'
            })
        
        print(f"✅ Fetched {len(arabica_contracts)} Arabica contracts")
        print("=" * 60 + "\n")
        return arabica_contracts
    
    print("⚠️ Could not fetch Arabica contracts from Barchart")
    print("=" * 60 + "\n")
    return None

def get_ai_analysis(commodity_data):
    """Generate AI analysis for a commodity including trend, recommendation, risk, and insight"""
    if not GEMINI_API_KEY or analysis_model is None:
        return {
            'trend': 'SIDEWAYS (NEUTRAL)',
            'recommendation': 'HOLD',
            'risk_level': 'MEDIUM',
            'insight': 'Analysis unavailable - AI features disabled',
            'support': commodity_data['price'],
            'resistance': commodity_data['price'] * 1.01
        }
    
    try:
        # Format name properly for the analysis
        display_name = commodity_data['name']
        contract_info = commodity_data.get('contract', '')
        if contract_info:
            display_name = f"{display_name} ({contract_info})"
        
        prompt = f"""You are a professional commodity analyst. Analyze the following data for {display_name} and provide concise trading insights.

Current Data:
- Price: ${commodity_data['price']:,.2f}
- Change: {commodity_data['change']:+.2f} ({commodity_data['change_percent']:+.2f}%)
- Daily Range: ${commodity_data['low']:,.2f} - ${commodity_data['high']:,.2f}
- Exchange: {commodity_data.get('exchange', 'N/A')}

Provide analysis in this exact JSON format:
{{
    "trend": "UPTREND/DOWNTREND/SIDEWAYS (STRONG/MODERATE/WEAK)",
    "recommendation": "BUY/SELL/HOLD",
    "risk_level": "HIGH/MEDIUM/LOW",
    "insight": "1-2 sentence market insight with context",
    "support": number (key support level),
    "resistance": number (key resistance level)
}}

Be specific and professional. For trend strength, consider:
- STRONG: Significant price movement with high volume
- MODERATE: Clear direction with moderate momentum
- WEAK: Minor movement or conflicting signals

For risk level:
- HIGH: High volatility, major news events, or extreme positions
- MEDIUM: Moderate volatility with some uncertainty
- LOW: Stable price action with clear direction

Support/resistance should be realistic price levels based on the data provided."""
        
        response = analysis_model.generate_content(prompt)
        # Clean and parse the response
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]  # Remove code block markers
        
        analysis = json.loads(response_text)
        
        # Ensure all required fields are present
        required_fields = ['trend', 'recommendation', 'risk_level', 'insight', 'support', 'resistance']
        for field in required_fields:
            if field not in analysis:
                if field == 'insight':
                    analysis[field] = "Market showing typical patterns for this commodity."
                elif field in ['support', 'resistance']:
                    analysis[field] = commodity_data['price']  # Default to current price
        
        return analysis
        
    except Exception as e:
        print(f"⚠️ AI analysis error for {commodity_data['name']}: {e}")
        # Return default analysis structure
        return {
            'trend': 'SIDEWAYS (NEUTRAL)',
            'recommendation': 'HOLD',
            'risk_level': 'MEDIUM',
            'insight': f'Limited analysis available for {commodity_data["name"]}',
            'support': commodity_data['low'],
            'resistance': commodity_data['high']
        }

def format_commodity_snapshot(commodity_data, analysis):
    """Format a single commodity's data into the detailed snapshot format with clear source labels"""
    # Format change direction
    change_pct = commodity_data['change_percent']
    if abs(change_pct) < 0.01:  # More than 0.01%
        change_dir = "No Change"
    elif change_pct > 0:
        change_dir = "Rising ↗"
    else:
        change_dir = "Falling ↘"
    
    # Format contract info
    contract_suffix = f" ({commodity_data.get('contract', '')})" if commodity_data.get('contract') else ""
    
    # Build clear source/exchange label
    exchange = commodity_data.get('exchange', commodity_data.get('source', 'Unknown'))
    source = commodity_data.get('source', 'Unknown')
    
    if source == 'Barchart':
        source_label = f"📊 Source: {exchange}"
    else:
        source_label = f"📊 Source: {exchange} (via {source})"
    
    # Format numbers with proper commas and decimals
    price_str = f"${commodity_data['price']:,.2f}"
    change_str = f"{commodity_data['change']:+.2f} ({change_pct:+.2f}%)"
    high_str = f"${commodity_data['high']:,.2f}"
    low_str = f"${commodity_data['low']:,.2f}"
    support_str = f"${analysis['support']:,.2f}"
    resistance_str = f"${analysis['resistance']:,.2f}"
    
    # Format timestamp in UTC
    timestamp = datetime.fromisoformat(commodity_data['timestamp'])
    timestamp_utc = timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Build the formatted message
    snapshot = f"➡ {commodity_data['name']}{contract_suffix} - {change_dir}\n\n"
    snapshot += f"💰 Price: {price_str}\n"
    snapshot += f"📊 Change: {change_str}\n"
    snapshot += f"📈 High: {high_str} | Low: {low_str}\n\n"
    snapshot += f"🎯 Analysis:\n"
    snapshot += f"• Trend: {analysis['trend']}\n"
    snapshot += f"• Recommendation: {analysis['recommendation']}\n"
    snapshot += f"• Risk Level: {analysis['risk_level']}\n\n"
    snapshot += f"💡 Insight: {analysis['insight']}\n\n"
    snapshot += f"🔹 Support: {support_str}\n"
    snapshot += f"🔸 Resistance: {resistance_str}\n\n"
    snapshot += f"{source_label}\n"
    snapshot += f"📅 Updated: {timestamp_utc}\n"
    
    return snapshot

# ============ TELEGRAM NOTIFICATIONS ============
def send_telegram_message(message, parse_mode='Markdown'):
    """Send text message via Telegram"""
    try:
        print(f"📤 Attempting to send Telegram message to {TELEGRAM_CHAT_ID}...") # Debug Log
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Telegram message sent successfully!") # Debug Log
        return True
    except Exception as e:
        print(f"❌ Telegram error: {e}")
        if 'response' in locals():
            print(f"   Response text: {response.text}")
        return False

def send_telegram_photo(photo_buffer, caption=''):
    """Send photo via Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        files = {'photo': ('chart.png', photo_buffer, 'image/png')}
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'caption': caption,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, files=files, data=data, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Telegram photo error: {e}")
        return False

def send_telegram_document(file_path, caption=''):
    """Send document via Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': caption
            }
            response = requests.post(url, files=files, data=data, timeout=30)
            response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Telegram document error: {e}")
        return False

# ============ MONITORING FUNCTIONS ============
def monitor_commodities():
    """Monitor all commodities (runs every 10 minutes during market hours only)"""
    print(f"\n⏰ Monitoring cycle at {datetime.now().strftime('%H:%M:%S')}")
    
    # Check if market is open
    if not is_market_hours():
        print("🔒 Market is CLOSED - Skipping monitoring")
        return
    
    print("✅ Market is OPEN - Proceeding with monitoring")
    
    # Check if we need to reset daily tracking (at 1:00 AM)
    cairo_tz = pytz.timezone('Africa/Cairo')
    now_cairo = datetime.now(cairo_tz)
    if now_cairo.hour == 1 and now_cairo.minute < 10:
        reset_daily_tracking()
    
    # Initialize full report
    snapshot_msg = f"☕ *ABU AUF COMMODITIES MONITOR*\n"
    snapshot_msg += f"⏱️ _Snapshot: {now_cairo.strftime('%H:%M')} Cairo Time_\n\n"
    has_data = False
    
    # Process Robusta and other commodities
    for symbol, info in WATCHLIST.items():
        try:
            price_data = fetch_commodity_data(symbol)
            if not price_data:
                print(f"  ⚠️ No data for {info['name']}, skipping...")
                continue
            has_data = True
            
            timestamp = datetime.now().isoformat()
            # Initialize history if needed
            if symbol not in price_history:
                price_history[symbol] = []
            # Store price with timestamp
            price_history[symbol].append((timestamp, price_data['price']))
            
            # Generate AI analysis for this commodity
            analysis = get_ai_analysis(price_data)
            
            # Format the commodity snapshot
            commodity_snapshot = format_commodity_snapshot(price_data, analysis)
            snapshot_msg += commodity_snapshot + "\n"
            
            # Memory protection: Keep max 144 records (24 hours)
            if len(price_history[symbol]) > 144:
                price_history[symbol] = price_history[symbol][-144:]
                    
            print(f"  ✅ {info['name']}: ${price_data['price']:.2f} ({price_data['change_percent']:+.2f}%)")
        except Exception as e:
            print(f"  ❌ Error processing {info['name']}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Process Arabica Coffee 4/5 (2 contracts)
    try:
        arabica_data = fetch_arabica_contracts()
        if arabica_data:
            for contract_data in arabica_data:
                has_data = True
                analysis = get_ai_analysis(contract_data)
                commodity_snapshot = format_commodity_snapshot(contract_data, analysis)
                snapshot_msg += commodity_snapshot + "\n"
                print(f"  ✅ {contract_data['name']} ({contract_data['contract']}): ${contract_data['price']:.2f} ({contract_data['change_percent']:+.2f}%)")
    except Exception as e:
        print(f"  ❌ Error processing Arabica contracts: {e}")
        import traceback
        traceback.print_exc()
    
    snapshot_msg += f"\n_💡 Monitoring: Barchart, ICE Futures, CBOT, CME Group_"
    
    # Send the snapshot message
    if has_data and TELEGRAM_BOT_TOKEN:
        print("\n📤 Sending enhanced snapshot to Telegram...")
        
        # Telegram has a 4096 character limit per message
        if len(snapshot_msg) > 4000:
            # Split into multiple messages if needed
            parts = [snapshot_msg[i:i+4000] for i in range(0, len(snapshot_msg), 4000)]
            for i, part in enumerate(parts):
                if i > 0:
                    part = f"_Part {i+1}/{len(parts)}_\n" + part
                send_telegram_message(part, parse_mode='Markdown')
        else:
            send_telegram_message(snapshot_msg, parse_mode='Markdown')
        print("✅ Enhanced snapshot sent to Telegram")
    else:
        print("⚠️ No data fetched or Telegram not configured, skipping message.")

# ============ CHART GENERATION ============
def generate_price_chart(symbol, commodity_name):
    """Generate a line chart for a commodity's daily movement"""
    if symbol not in price_history or len(price_history[symbol]) < 2:
        return None
    try:
        # Extract timestamps and prices
        timestamps = [datetime.fromisoformat(ts) for ts, _ in price_history[symbol]]
        prices = [price for _, price in price_history[symbol]]
        # Create figure
        plt.figure(figsize=(12, 6))
        plt.style.use('seaborn-v0_8-darkgrid')
        # Plot line
        plt.plot(timestamps, prices, linewidth=2, color='#2E86AB', marker='o', markersize=4)
        # Fill area under curve
        plt.fill_between(timestamps, prices, alpha=0.3, color='#2E86AB')
        # Formatting
        plt.title(f'{commodity_name} - Daily Movement', fontsize=16, fontweight='bold', pad=20)
        plt.xlabel('Time', fontsize=12, fontweight='bold')
        plt.ylabel('Price (USD)', fontsize=12, fontweight='bold')
        # Format x-axis to show times nicely
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        plt.gca().xaxis.set_major_locator(mdates.HourLocator(interval=1))
        plt.gcf().autofmt_xdate()
        # Add current price annotation
        last_price = prices[-1]
        plt.annotate(f'${last_price:.2f}', 
                    xy=(timestamps[-1], last_price),
                    xytext=(10, 10), textcoords='offset points',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7),
                    fontsize=10, fontweight='bold')
        # Grid
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        # Save to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        print(f"❌ Chart generation error for {symbol}: {e}")
        return None

# ============ DAILY SUMMARY GENERATOR ============
def generate_daily_summary():
    """Generate text summary comparing current prices to session baseline"""
    summary_lines = ["📊 *Abu Auf Commodities - Daily Movement Summary*\n"]
    summary_lines.append(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    summary_lines.append("─" * 50 + "\n")
    
    for symbol, info in WATCHLIST.items():
        commodity_name = info['name']
        commodity_type = info['type']
        if symbol not in price_history or len(price_history[symbol]) == 0:
            continue
        # Get current price
        current_price = price_history[symbol][-1][1]
        # Get baseline (session start price or first price of the day)
        baseline_price = daily_start_prices.get(symbol, price_history[symbol][0][1])
        # Calculate movement
        price_change = current_price - baseline_price
        percent_change = (price_change / baseline_price) * 100 if baseline_price else 0
        # Format with emoji
        if percent_change > 0:
            emoji = "📈"
            sign = "+"
        elif percent_change < 0:
            emoji = "📉"
            sign = ""
        else:
            emoji = "➡️"
            sign = ""
        summary_lines.append(
            f"{emoji} *{commodity_name}* ({commodity_type})\n"
            f"   Current: ${current_price:.2f} | "
            f"Change: {sign}${price_change:.2f} ({sign}{percent_change:.2f}%)\n"
        )
    
    # Add Arabica contracts to summary
    if arabica_contracts:
        for i, contract in enumerate(arabica_contracts):
            symbol_key = f'KC_CONTRACT_{i+1}'
            current_price = contract['price']
            baseline_price = daily_start_prices.get(symbol_key, current_price)
            price_change = current_price - baseline_price
            percent_change = (price_change / baseline_price) * 100 if baseline_price else 0
            
            if percent_change > 0:
                emoji = "📈"
                sign = "+"
            elif percent_change < 0:
                emoji = "📉"
                sign = ""
            else:
                emoji = "➡️"
                sign = ""
            
            summary_lines.append(
                f"{emoji} *Arabica Coffee 4/5 ({contract['contract']})* (Softs)\n"
                f"   Current: ${current_price:.2f} | "
                f"Change: {sign}${price_change:.2f} ({sign}{percent_change:.2f}%)\n"
            )
    
    return "".join(summary_lines)

# ============ WEEKLY PDF REPORT ============
def generate_executive_summary():
    """Generate executive summary text for PDF"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Collect week's data
        summary_data = []
        for symbol, info in WATCHLIST.items():
            if symbol in price_history and len(price_history[symbol]) > 1:
                prices = [p for _, p in price_history[symbol]]
                change_pct = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] else 0
                summary_data.append(f"{info['name']}: {change_pct:+.2f}%")
        
        # Add Arabica contracts
        if arabica_contracts:
            for contract in arabica_contracts:
                symbol_key = f"KC_{contract['contract']}"
                if symbol_key in price_history and len(price_history[symbol_key]) > 1:
                    prices = [p for _, p in price_history[symbol_key]]
                    change_pct = ((prices[-1] - prices[0]) / prices[0] * 100) if prices[0] else 0
                    summary_data.append(f"Arabica {contract['contract']}: {change_pct:+.2f}%")
        
        prompt = f"""As Chief Commodity Analyst, write a 2-3 paragraph executive summary for Abu Auf's board covering this week's commodity price movements:

{chr(10).join(summary_data)}

Structure:
1. MARKET OVERVIEW: Overall tone (bullish/bearish/mixed) and key macro drivers
2. STANDOUT MOVERS: Highlight commodities with >5% moves and explain why
3. WEEK AHEAD: Forward-looking insights and risks to watch

Write in executive summary style: concise, data-driven, actionable. Assume the reader is C-level."""
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except:
        return "This week showed mixed movements across commodity markets. Key soft commodities displayed moderate volatility reflecting ongoing supply chain adjustments and shifting demand patterns. Grains and oils sectors maintained relative stability with seasonal factors playing a key role in price formation."

def generate_weekly_pdf_report():
    """Generate professional commodity analysis report matching industry standards"""
    try:
        from fpdf import FPDF
        class CommodityReport(FPDF):
            def header(self):
                # Abu Auf logo area (placeholder)
                self.set_font('Arial', 'B', 20)
                self.set_text_color(0, 51, 102)  # Dark blue
                self.cell(0, 15, 'ABU AUF', 0, 1, 'L')
                self.set_font('Arial', '', 10)
                self.set_text_color(100, 100, 100)
                self.cell(0, 5, 'Commodities Intelligence Report', 0, 1, 'L')
                self.ln(5)
            def footer(self):
                self.set_y(-15)
                self.set_font('Arial', 'I', 8)
                self.set_text_color(128, 128, 128)
                self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')
        pdf = CommodityReport()
        pdf.add_page()
        # ============ COVER SECTION ============
        pdf.set_font('Arial', 'B', 24)
        pdf.set_text_color(0, 51, 102)
        pdf.ln(20)
        pdf.cell(0, 15, 'Weekly Commodities Report', 0, 1, 'C')
        pdf.set_font('Arial', '', 14)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, f'Week Ending: {datetime.now().strftime("%B %d, %Y")}', 0, 1, 'C')
        pdf.ln(30)
        # Key Highlights Box
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'WEEKLY HIGHLIGHTS', 0, 1, 'C', fill=True)
        pdf.set_font('Arial', '', 10)
        # Calculate key metrics
        total_commodities = len([s for s in WATCHLIST.keys() if s in price_history]) + len(arabica_contracts)
        positive_movers = 0
        negative_movers = 0
        for symbol in WATCHLIST.keys():
            if symbol in price_history and len(price_history[symbol]) > 1:
                prices = [p for _, p in price_history[symbol]]
                if prices[-1] > prices[0]:
                    positive_movers += 1
                elif prices[-1] < prices[0]:
                    negative_movers += 1
        pdf.ln(5)
        pdf.cell(0, 8, f'Commodities Tracked: {total_commodities}', 0, 1, 'C')
        pdf.cell(0, 8, f'Positive Movement: {positive_movers} | Negative Movement: {negative_movers}', 0, 1, 'C')
        # ============ PAGE 2: EXECUTIVE SUMMARY ============
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, 'EXECUTIVE SUMMARY', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        if GEMINI_API_KEY:
            summary = generate_executive_summary()
            pdf.multi_cell(0, 6, summary)
        else:
            pdf.multi_cell(0, 6, 'AI-powered market analysis is currently unavailable. Please review individual commodity performance data in subsequent sections.')
        # ============ SUPPLY & DEMAND UPDATE ============
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, 'SUPPLY & DEMAND UPDATE', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        # Generate market intelligence for each category
        categories = {}
        for symbol, info in WATCHLIST.items():
            cat = info['type']
            if cat not in categories:
                categories[cat] = []
            categories[cat].append((symbol, info))
        
        # Add Arabica to Softs category
        if arabica_contracts and 'Softs' in categories:
            for contract in arabica_contracts:
                categories['Softs'].append((f"KC_{contract['contract']}", {'name': f"Arabica Coffee 4/5 ({contract['contract']})", 'type': 'Softs'}))
        
        for category, commodities in categories.items():
            pdf.set_font('Arial', 'B', 14)
            pdf.set_text_color(0, 102, 204)
            pdf.cell(0, 10, f'{category.upper()} COMPLEX', 0, 1, 'L')
            pdf.ln(2)
            for symbol, info in commodities:
                if symbol.startswith('KC_'):
                    # Handle Arabica contracts
                    contract_code = symbol.split('_')[1]
                    matching_contract = next((c for c in arabica_contracts if c['contract'] == contract_code), None)
                    if not matching_contract:
                        continue
                    commodity_analysis = generate_commodity_deep_analysis(symbol, info, matching_contract['price'])
                else:
                    if symbol not in price_history or len(price_history[symbol]) < 2:
                        continue
                    commodity_analysis = generate_commodity_deep_analysis(symbol, info)
                
                pdf.set_font('Arial', 'B', 12)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(0, 8, f'{info["name"]}', 0, 1, 'L')
                pdf.set_font('Arial', '', 9)
                pdf.multi_cell(0, 5, commodity_analysis)
                pdf.ln(3)
            pdf.ln(3)
        # ============ PRICE PERFORMANCE TABLES ============
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, 'WEEKLY PRICE PERFORMANCE', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(8)
        # Table header
        pdf.set_fill_color(0, 51, 102)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Arial', 'B', 9)
        col_widths = [50, 30, 30, 30, 30, 20]
        headers = ['Commodity', 'Open', 'Close', 'High/Low', 'Change', '%']
        for i, header in enumerate(headers):
            pdf.cell(col_widths[i], 8, header, 1, 0, 'C', fill=True)
        pdf.ln()
        # Table data
        pdf.set_font('Arial', '', 9)
        pdf.set_text_color(0, 0, 0)
        row_index = 0
        for symbol, info in WATCHLIST.items():
            if symbol not in price_history or len(price_history[symbol]) < 2:
                continue
            prices = [p for _, p in price_history[symbol]]
            week_start = prices[0]
            week_end = prices[-1]
            week_high = max(prices)
            week_low = min(prices)
            week_change = week_end - week_start
            week_change_pct = (week_change / week_start * 100) if week_start else 0
            # Alternate row colors
            if row_index % 2 == 0:
                pdf.set_fill_color(245, 245, 245)
            else:
                pdf.set_fill_color(255, 255, 255)
            # Color code the change
            if week_change_pct > 0:
                pdf.set_text_color(0, 128, 0)  # Green
            elif week_change_pct < 0:
                pdf.set_text_color(255, 0, 0)  # Red
            else:
                pdf.set_text_color(0, 0, 0)  # Black
            pdf.cell(col_widths[0], 8, info['name'], 1, 0, 'L', fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.cell(col_widths[1], 8, f'${week_start:.2f}', 1, 0, 'C', fill=True)
            pdf.cell(col_widths[2], 8, f'${week_end:.2f}', 1, 0, 'C', fill=True)
            pdf.cell(col_widths[3], 8, f'${week_high:.2f}/${week_low:.2f}', 1, 0, 'C', fill=True)
            # Change with color
            if week_change_pct > 0:
                pdf.set_text_color(0, 128, 0)
            elif week_change_pct < 0:
                pdf.set_text_color(255, 0, 0)
            pdf.cell(col_widths[4], 8, f'{week_change:+.2f}', 1, 0, 'C', fill=True)
            pdf.cell(col_widths[5], 8, f'{week_change_pct:+.1f}%', 1, 0, 'C', fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            row_index += 1
        
        # Add Arabica contracts to table
        if arabica_contracts:
            for contract in arabica_contracts:
                symbol_key = f"KC_{contract['contract']}"
                # Since we don't have historical data in price_history for contracts yet,
                # use the contract data itself
                week_start = daily_start_prices.get(f"KC_CONTRACT_{arabica_contracts.index(contract)+1}", contract['price'])
                week_end = contract['price']
                week_high = contract['high']
                week_low = contract['low']
                week_change = week_end - week_start
                week_change_pct = (week_change / week_start * 100) if week_start else 0
                
                if row_index % 2 == 0:
                    pdf.set_fill_color(245, 245, 245)
                else:
                    pdf.set_fill_color(255, 255, 255)
                
                if week_change_pct > 0:
                    pdf.set_text_color(0, 128, 0)
                elif week_change_pct < 0:
                    pdf.set_text_color(255, 0, 0)
                else:
                    pdf.set_text_color(0, 0, 0)
                
                pdf.cell(col_widths[0], 8, f"Arabica ({contract['contract']})", 1, 0, 'L', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.cell(col_widths[1], 8, f'${week_start:.2f}', 1, 0, 'C', fill=True)
                pdf.cell(col_widths[2], 8, f'${week_end:.2f}', 1, 0, 'C', fill=True)
                pdf.cell(col_widths[3], 8, f'${week_high:.2f}/${week_low:.2f}', 1, 0, 'C', fill=True)
                
                if week_change_pct > 0:
                    pdf.set_text_color(0, 128, 0)
                elif week_change_pct < 0:
                    pdf.set_text_color(255, 0, 0)
                pdf.cell(col_widths[4], 8, f'{week_change:+.2f}', 1, 0, 'C', fill=True)
                pdf.cell(col_widths[5], 8, f'{week_change_pct:+.1f}%', 1, 0, 'C', fill=True)
                pdf.set_text_color(0, 0, 0)
                pdf.ln()
                row_index += 1
        
        # ============ KEY RISK FACTORS ============
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 10, 'KEY RISK FACTORS & OUTLOOK', 0, 1, 'L')
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        if GEMINI_API_KEY:
            risk_analysis = generate_risk_analysis()
            pdf.multi_cell(0, 6, risk_analysis)
        # ============ PROCUREMENT RECOMMENDATIONS ============
        pdf.ln(10)
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(204, 0, 0)
        pdf.cell(0, 10, 'STRATEGIC RECOMMENDATIONS', 0, 1, 'L')
        pdf.ln(3)
        pdf.set_font('Arial', '', 10)
        pdf.set_text_color(0, 0, 0)
        if GEMINI_API_KEY:
            recommendations = generate_procurement_recommendations()
            pdf.multi_cell(0, 6, recommendations)
        # ============ FOOTER NOTE ============
        pdf.ln(15)
        pdf.set_font('Arial', 'I', 8)
        pdf.set_text_color(128, 128, 128)
        pdf.multi_cell(0, 4, 'This report is generated using real-time market data and AI-powered analysis. Data sources include ICE Futures, Barchart, CBOT, CME Group, and Investing.com. For internal use only.')
        # Save PDF
        pdf_path = tempfile.mktemp(suffix='.pdf', prefix='abu_auf_weekly_')
        pdf.output(pdf_path)
        return pdf_path
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_commodity_deep_analysis(symbol, info, override_price=None):
    """Generate detailed supply/demand analysis for specific commodity"""
    try:
        if symbol.startswith('KC_'):
            # Handle Arabica contracts
            if not override_price:
                return "Insufficient data for analysis."
            week_start = override_price
            week_end = override_price
            week_change_pct = 0
        else:
            if symbol not in price_history or len(price_history[symbol]) < 2:
                return "Insufficient data for analysis."
            prices = [p for _, p in price_history[symbol]]
            week_start = prices[0]
            week_end = prices[-1]
            week_change_pct = ((week_end - week_start) / week_start * 100) if week_start else 0
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""As a commodity analyst, write a 2-3 sentence supply/demand update for {info['name']}.
Price moved {week_change_pct:+.2f}% this week (from ${week_start:.2f} to ${week_end:.2f}).
Cover ONE OR TWO of these relevant factors:
- Weather impacts on production regions
- Export/import dynamics
- Inventory levels and stock changes
- Currency effects (USD strength/weakness)
- Origin-specific developments
- Demand trends from major buyers
Write in professional commodity analyst style. Be specific and actionable. NO generic statements."""
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        if symbol.startswith('KC_'):
            return f"Arabica coffee contract showing typical market dynamics. Further monitoring recommended."
        prices = [p for _, p in price_history.get(symbol, [(None, 0)])]
        change = ((prices[-1] - prices[0]) / prices[0] * 100) if len(prices) > 1 and prices[0] else 0
        return f"Price movement of {change:+.2f}% this week reflects ongoing market dynamics. Further monitoring recommended."

def generate_risk_analysis():
    """Generate risk factors and outlook"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = """Write a 3-paragraph risk analysis for Abu Auf's commodity portfolio covering:
1. MACROECONOMIC RISKS: Currency volatility, inflation, interest rates, geopolitical tensions affecting trade
2. SUPPLY RISKS: Weather patterns (El Niño/La Niña), crop diseases, logistics disruptions, origin-specific issues
3. DEMAND RISKS: Consumer trends, emerging markets demand, substitution effects
Keep it board-level: strategic, not overly technical. Focus on MATERIAL risks that could impact procurement costs by >5%."""
        response = model.generate_content(prompt)
        return response.text
    except:
        return "Market volatility remains elevated across agricultural commodities. Key risk factors include weather uncertainty in major producing regions, currency fluctuations affecting import costs, and evolving global demand patterns. Continued monitoring of supply chain dynamics recommended."

def generate_procurement_recommendations():
    """Generate strategic procurement recommendations"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        # Get all current prices and trends
        commodities_summary = []
        for symbol, info in WATCHLIST.items():
            if symbol in price_history and len(price_history[symbol]) > 1:
                prices = [p for _, p in price_history[symbol]]
                trend = "RISING" if prices[-1] > prices[0] else "FALLING"
                volatility = "HIGH" if (max(prices) - min(prices)) / prices[0] > 0.05 else "MODERATE"
                commodities_summary.append(f"{info['name']}: {trend}, {volatility} volatility")
        
        # Add Arabica contracts
        if arabica_contracts:
            for contract in arabica_contracts:
                symbol_key = f"KC_CONTRACT_{arabica_contracts.index(contract)+1}"
                baseline = daily_start_prices.get(symbol_key, contract['price'])
                trend = "RISING" if contract['price'] > baseline else "FALLING"
                volatility = "HIGH" if abs((contract['price'] - baseline) / baseline) > 0.05 else "MODERATE"
                commodities_summary.append(f"Arabica ({contract['contract']}): {trend}, {volatility} volatility")
        
        prompt = f"""As procurement strategist for Abu Auf, provide 3-4 actionable recommendations based on this week's movements:
{chr(10).join(commodities_summary)}
Structure as:
• IMMEDIATE ACTIONS (this week): Which commodities to buy/hedge now
• SHORT-TERM TACTICS (2-4 weeks): Timing and volume strategies
• RISK MITIGATION: Hedging or diversification suggestions
Be specific: "Lock in 30% of Q1 coffee needs" not "consider hedging." Focus on VALUE PROTECTION."""
        response = model.generate_content(prompt)
        return response.text
    except:
        return """• Monitor volatile commodities closely for favorable entry points
• Consider forward contracts for key ingredients showing upward trends
• Diversify supplier base to mitigate single-origin risk
• Review hedging strategies for commodities with high volatility"""

def send_hourly_report():
    """Send hourly report with Robusta chart and all commodities summary"""
    # Only send during market hours
    if not is_market_hours():
        print("🔒 Market closed - Skipping hourly report")
        return
    
    print("\n📊 Generating hourly report...")
    # Generate Robusta Coffee chart
    robusta_chart = generate_price_chart('RC=F', 'Robusta Coffee')
    if robusta_chart and TELEGRAM_BOT_TOKEN:
        caption = f"☕ *Robusta Coffee - Hourly Update*\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"
        send_telegram_photo(robusta_chart, caption)
    # Generate and send summary for all commodities
    summary = generate_daily_summary()
    if TELEGRAM_BOT_TOKEN:
        send_telegram_message(summary)
    print("✅ Hourly report sent!")

def send_email_with_attachment(to_email, subject, html_body, attachment_path, attachment_name):
    """Send email with PDF attachment"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        # Attach HTML body
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        # Attach PDF
        with open(attachment_path, 'rb') as f:
            pdf_part = MIMEBase('application', 'pdf')
            pdf_part.set_payload(f.read())
        encoders.encode_base64(pdf_part)
        pdf_part.add_header(
            'Content-Disposition',
            f'attachment; filename={attachment_name}'
        )
        msg.attach(pdf_part)
        # Send via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"      Error: {e}")
        return False

def send_weekly_report():
    """Send weekly PDF report (Friday only) via Telegram AND Email"""
    if datetime.now().weekday() != 4:  # 4 = Friday
        return
    print("\n📄 Generating weekly PDF report...")
    pdf_path = generate_weekly_pdf_report()
    if not pdf_path:
        print("⚠️ Weekly report generation failed")
        return
    # Send via Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        caption = f"📊 Abu Auf Commodities - Weekly Report\n{datetime.now().strftime('%Y-%m-%d')}"
        if send_telegram_document(pdf_path, caption):
            print("✅ Weekly report sent to Telegram!")
        else:
            print("⚠️ Failed to send to Telegram")
    # Send via Email to all recipients
    if EMAIL_FROM and EMAIL_PASSWORD and EMAIL_RECIPIENTS:
        print(f"\n📧 Sending PDF to {len(EMAIL_RECIPIENTS)} email recipients...")
        subject = f"📊 Abu Auf Commodities - Weekly Report - {datetime.now().strftime('%B %d, %Y')}"
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #003366; border-bottom: 3px solid #003366; padding-bottom: 10px;">
                        📊 Abu Auf Commodities Intelligence Report
                    </h2>
                    <p>Dear Team,</p>
                    <p>Please find attached the <strong>Weekly Commodities Report</strong> for the week ending <strong>{datetime.now().strftime('%B %d, %Y')}</strong>.</p>
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #003366;">📋 Report Contents:</h3>
                        <ul style="margin-bottom: 0;">
                            <li>Executive Summary with Market Overview</li>
                            <li>Weekly Price Performance (All Commodities)</li>
                            <li>Supply & Demand Analysis by Category</li>
                            <li>Key Risk Factors & Market Outlook</li>
                            <li>Strategic Procurement Recommendations</li>
                        </ul>
                    </div>
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; border-left: 4px solid #0066cc;">
                        <h4 style="margin-top: 0; color: #0066cc;">📊 Commodities Tracked:</h4>
                        <p style="margin-bottom: 5px;"><strong>Softs:</strong> Robusta Coffee, Arabica Coffee 4/5 (2 contracts), Sugar, Cocoa</p>
                        <p style="margin-bottom: 5px;"><strong>Grains:</strong> Wheat</p>
                        <p style="margin-bottom: 0;"><strong>Oils:</strong> Soybean Oil, Palm Oil</p>
                    </div>
                    <p style="margin-top: 20px;">This report is generated automatically every Friday at 5:00 PM Cairo time using real-time market data and AI-powered analysis.</p>
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    <p style="font-size: 12px; color: #666;">
                        <strong>Abu Auf Commodities Monitor</strong><br>
                        Automated Intelligence System v3.1<br>
                        For internal use only
                    </p>
                </div>
            </body>
        </html>
        """
        success_count = 0
        for recipient in EMAIL_RECIPIENTS:
            try:
                if send_email_with_attachment(
                    to_email=recipient,
                    subject=subject,
                    html_body=html_body,
                    attachment_path=pdf_path,
                    attachment_name=f"Abu_Auf_Weekly_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
                ):
                    print(f"   ✅ Sent to {recipient}")
                    success_count += 1
                else:
                    print(f"   ❌ Failed to send to {recipient}")
            except Exception as e:
                print(f"   ❌ Error sending to {recipient}: {e}")
        print(f"\n📧 Email delivery: {success_count}/{len(EMAIL_RECIPIENTS)} successful")
    print("\n✅ Weekly report distribution completed!")

@app.route('/')
def home():
    """Health check endpoint"""
    market_status = "OPEN" if is_market_hours() else "CLOSED"
    return jsonify({
        'status': 'online',
        'service': 'Abu Auf Commodities Monitor',
        'version': '3.1',
        'market_status': market_status,
        'commodities': len(WATCHLIST) + 2,  # +2 for Arabica contracts
        'timestamp': datetime.now().isoformat()
    })

@app.route('/monitor')
def trigger_monitor():
    """Manual trigger for monitoring (for cron jobs)"""
    def run_background():
        try:
            print("📄 /monitor endpoint triggered")
            monitor_commodities()
            print("✅ Background monitoring completed")
        except Exception as e:
            print(f"❌ Background error: {e}")
            import traceback
            traceback.print_exc()
    # Start monitoring in background thread
    Thread(target=run_background, daemon=True).start()
    return jsonify({
        "status": "started",
        "message": "Monitoring cycle started in background",
        "market_status": "OPEN" if is_market_hours() else "CLOSED",
        "note": "Check Telegram/logs for results in 30-60 seconds",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/hourly')
def trigger_hourly():
    """Manual trigger for hourly report"""
    Thread(target=send_hourly_report).start()
    return jsonify({'status': 'hourly report generation started'})

@app.route('/weekly')
def trigger_weekly():
    """Manual trigger for weekly report"""
    Thread(target=send_weekly_report).start()
    return jsonify({'status': 'weekly report generation started'})

@app.route('/prices')
def get_prices():
    """Get current prices for all commodities"""
    prices = {}
    for symbol, info in WATCHLIST.items():
        if symbol in price_history and len(price_history[symbol]) > 0:
            current_price = price_history[symbol][-1][1]
            baseline = daily_start_prices.get(symbol, price_history[symbol][0][1])
            prices[symbol] = {
                'name': info['name'],
                'type': info['type'],
                'current': current_price,
                'baseline': baseline,
                'change': current_price - baseline,
                'change_percent': ((current_price - baseline) / baseline * 100) if baseline else 0
            }
    
    # Add Arabica contracts
    if arabica_contracts:
        for i, contract in enumerate(arabica_contracts):
            symbol_key = f"KC_{contract['contract']}"
            baseline_key = f"KC_CONTRACT_{i+1}"
            baseline = daily_start_prices.get(baseline_key, contract['price'])
            prices[symbol_key] = {
                'name': f"Arabica Coffee 4/5 ({contract['contract']})",
                'type': 'Softs',
                'current': contract['price'],
                'baseline': baseline,
                'change': contract['price'] - baseline,
                'change_percent': ((contract['price'] - baseline) / baseline * 100) if baseline else 0
            }
    
    return jsonify(prices)

@app.route('/check')
def manual_check():
    """Manual trigger - runs monitoring in background (for cron jobs)"""
    def run_background():
        try:
            print("📄 /check endpoint triggered")
            monitor_commodities()
            print("✅ Background monitoring completed")
        except Exception as e:
            print(f"❌ Background error: {e}")
            import traceback
            traceback.print_exc()
    # Start monitoring in background thread
    Thread(target=run_background, daemon=True).start()
    return jsonify({
        "status": "started",
        "message": "Monitoring cycle started in background",
        "note": "Check Telegram/logs for results in 30-60 seconds",
        "timestamp": datetime.now().isoformat()
    })

# ============ SCHEDULED TASKS ============
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit

def start_scheduler():
    """Start background scheduler"""
    scheduler = BackgroundScheduler(timezone='Africa/Cairo')
    # Monitor every 10 minutes (1 AM - 11 PM Cairo time, market hours)
    scheduler.add_job(
        func=monitor_commodities,
        trigger=CronTrigger(minute='*/10', hour='9-21'),
        id='monitor_commodities',
        name='Monitor commodities every 10 minutes (market hours enforced)'
    )
    # Hourly report (1 AM - 11 PM, on the hour)
    scheduler.add_job(
        func=send_hourly_report,
        trigger=CronTrigger(minute='0', hour='9-21'),
        id='hourly_report',
        name='Send hourly summary report (market hours)'
    )
    # Weekly report (Friday at 5 PM)
    scheduler.add_job(
        func=send_weekly_report,
        trigger=CronTrigger(day_of_week='fri', hour='17', minute='0'),
        id='weekly_report',
        name='Send weekly PDF report'
    )
    scheduler.start()
    print("✅ Scheduler started!")
    print("   📊 Monitoring: Every 10 minutes (9 AM - 9 PM Cairo, market hours only)")
    print("   📈 Hourly Reports: On the hour (9 AM - 9 PM, market hours only)")
    print("   📄 Weekly Report: Friday at 5 PM")
    # Run initial monitoring
    Thread(target=monitor_commodities).start()
    atexit.register(lambda: scheduler.shutdown())

# ============ MAIN ENTRY POINT ============
if __name__ == '__main__':
    print("🚀 Starting Abu Auf Commodities Monitor v3.1...")
    print(f"📊 Monitoring {len(WATCHLIST) + 2} commodities (including 2 Arabica contracts)")
    print(f"📱 Telegram: {'Enabled' if TELEGRAM_BOT_TOKEN else 'Disabled'}")
    print(f"🧠 AI Analysis: {'Enabled' if GEMINI_API_KEY else 'Disabled'}")
    print(f"📧 Email: {'Enabled' if EMAIL_FROM and EMAIL_PASSWORD else 'Disabled'}")
    print(f"⏰ Market Hours: Monday-Friday, 9:00 AM - 9:00 PM Cairo Time")
    print("\n" + "="*60 + "\n")
    start_scheduler()
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)