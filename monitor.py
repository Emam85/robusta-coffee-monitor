#!/usr/bin/env python3
"""
Complete Commodity Price Monitor with Full Features
- 10-minute price updates via Telegram
- Hourly summary messages
- Weekly PDF reports
- Email notifications
- Price change alerts
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
import logging
import requests
from flask import Flask, jsonify, send_file
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration from environment variables
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
EMAIL_FROM = os.environ.get('EMAIL_FROM')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
EMAIL_TO = os.environ.get('EMAIL_TO', '').split(',')  # Support multiple recipients
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Commodity configuration
COMMODITIES = {
    'Robusta Coffee': {'source': 'barchart', 'symbol': 'RCF25', 'unit': 'USD/ton'},
    'Arabica Coffee': {'source': 'investing', 'id': '959214', 'unit': 'USd/lb'},
    'Sugar No.11': {'source': 'investing', 'id': '959209', 'unit': 'USd/lb'},
    'Cocoa': {'source': 'investing', 'id': '959206', 'unit': 'USD/ton'},
    'Wheat': {'source': 'investing', 'id': '959203', 'unit': 'USd/bu'},
    'Soybean Oil': {'source': 'investing', 'id': '959207', 'unit': 'USd/lb'},
    'Palm Oil': {'source': 'investing', 'id': '959233', 'unit': 'MYR/ton'}
}

# Global storage for price history
price_history = {}
last_hourly_update = None
last_weekly_report = None


def send_telegram_message(message):
    """Send a message via Telegram bot."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ Telegram credentials not configured!")
        return False
    
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        logger.info("📤 Sending Telegram message...")
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Telegram message sent! Message ID: {result['result']['message_id']}")
                return True
            else:
                logger.error(f"❌ Telegram API error: {result}")
                return False
        else:
            logger.error(f"❌ Telegram HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending Telegram message: {e}")
        return False


def send_telegram_document(document_bytes, filename, caption):
    """Send a document (PDF) via Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("❌ Telegram credentials not configured!")
        return False
    
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument'
        
        files = {
            'document': (filename, document_bytes, 'application/pdf')
        }
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'caption': caption,
            'parse_mode': 'Markdown'
        }
        
        logger.info(f"📤 Sending Telegram document: {filename}...")
        response = requests.post(url, files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Document sent successfully!")
                return True
            else:
                logger.error(f"❌ Telegram API error: {result}")
                return False
        else:
            logger.error(f"❌ HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error sending document: {e}")
        return False


def send_email(subject, body, attachment_bytes=None, attachment_name=None):
    """Send email notification with optional attachment."""
    if not EMAIL_FROM or not EMAIL_PASSWORD or not EMAIL_TO:
        logger.warning("⚠️  Email not configured, skipping...")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = ', '.join(EMAIL_TO)
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'html'))
        
        # Add attachment if provided
        if attachment_bytes and attachment_name:
            attachment = MIMEApplication(attachment_bytes)
            attachment.add_header('Content-Disposition', 'attachment', filename=attachment_name)
            msg.attach(attachment)
        
        # Send email
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Email sent to {len(EMAIL_TO)} recipient(s)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error sending email: {e}")
        return False


def fetch_barchart_price(symbol):
    """Fetch commodity price from Barchart using waterfall approach."""
    try:
        # Method 1: Try official API
        logger.info("  [Method 1] Trying Official API...")
        url = f"https://www.barchart.com/proxies/core-api/v1/quotes/get"
        params = {'symbol': symbol, 'fields': 'lastPrice'}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'results' in data and len(data['results']) > 0:
                price = data['results'][0].get('lastPrice')
                if price:
                    logger.info(f"✅ Using Barchart data: ${price}")
                    return float(price), 'Barchart API'
        
        # Method 2: Try TLS impersonation
        logger.info("  [Method 2] Trying TLS Impersonation (Chrome 120)...")
        url = f"https://www.barchart.com/futures/quotes/{symbol}/overview"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            import re
            text = response.text
            
            # Try multiple patterns
            patterns = [
                r'"lastPrice":\s*([0-9.]+)',
                r'data-last-price="([0-9.]+)"',
                r'<span class="last-change[^"]*">([0-9.]+)</span>'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    price = float(match.group(1))
                    logger.info(f"✅ Using Barchart data: ${price}")
                    return price, 'Barchart (TLS)'
        
        logger.error(f"❌ All methods failed for {symbol}")
        return None, None
        
    except Exception as e:
        logger.error(f"❌ Error fetching Barchart price: {e}")
        return None, None


def fetch_investing_price(commodity_name):
    """Fetch commodity price from Investing.com."""
    try:
        # Simplified scraping - you may need to adjust based on actual HTML structure
        commodity_id = COMMODITIES[commodity_name]['id']
        url = f"https://www.investing.com/commodities/{commodity_id}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            import re
            text = response.text
            
            # Try to find price in JSON data
            patterns = [
                r'"last":\s*([0-9.]+)',
                r'data-test="instrument-price-last">([0-9.]+)',
                r'<span[^>]*class="[^"]*text-2xl[^"]*">([0-9,]+\.?[0-9]*)</span>'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    price_str = match.group(1).replace(',', '')
                    price = float(price_str)
                    logger.info(f"✅ Got {commodity_name}: {price}")
                    return price, 'Investing.com'
        
        logger.error(f"❌ Failed to fetch {commodity_name}")
        return None, None
        
    except Exception as e:
        logger.error(f"❌ Error fetching Investing price: {e}")
        return None, None


def fetch_all_prices():
    """Fetch all commodity prices."""
    logger.info("🌊 WATERFALL FETCH: Robusta Coffee")
    logger.info("=" * 60)
    
    prices = {}
    
    for commodity, config in COMMODITIES.items():
        logger.info(f"  🔍 Fetching {commodity} from {config['source']}...")
        
        if config['source'] == 'barchart':
            price, source = fetch_barchart_price(config['symbol'])
        elif config['source'] == 'investing':
            price, source = fetch_investing_price(commodity)
        else:
            price, source = None, None
        
        if price:
            prices[commodity] = {
                'price': price,
                'source': source,
                'unit': config['unit'],
                'timestamp': datetime.now().isoformat()
            }
            logger.info(f"  ✅ {commodity}: ${price:.2f} ({source})")
        else:
            prices[commodity] = {
                'price': None,
                'source': None,
                'unit': config['unit'],
                'timestamp': datetime.now().isoformat()
            }
            logger.warning(f"  ⚠️  Failed to fetch {commodity}")
    
    logger.info("=" * 60)
    return prices


def calculate_price_change(commodity, current_price):
    """Calculate price change percentage from previous data."""
    if commodity not in price_history or len(price_history[commodity]) < 2:
        return None
    
    previous_price = price_history[commodity][-2]['price']
    if previous_price and current_price:
        change = ((current_price - previous_price) / previous_price) * 100
        return change
    return None


def format_10min_message(prices):
    """Format 10-minute update message."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    message = f"📊 **10-Min Price Update**\n"
    message += f"🕐 {timestamp}\n\n"
    
    for commodity, data in prices.items():
        if data['price']:
            # Get emoji
            emoji = {'Robusta Coffee': '☕', 'Arabica Coffee': '☕', 
                    'Sugar No.11': '🍬', 'Cocoa': '🍫', 
                    'Wheat': '🌾', 'Soybean Oil': '🌿', 
                    'Palm Oil': '🌴'}.get(commodity, '📦')
            
            # Calculate change
            change = calculate_price_change(commodity, data['price'])
            change_str = f" ({change:+.2f}%)" if change else ""
            arrow = "📈" if change and change > 0 else "📉" if change and change < 0 else ""
            
            message += f"{emoji} **{commodity}**: ${data['price']:.2f} {change_str} {arrow}\n"
        else:
            message += f"❌ **{commodity}**: _Unavailable_\n"
    
    message += "\n_Next update in 10 minutes_"
    return message


def format_hourly_summary(prices):
    """Format hourly summary message with analysis."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
    
    message = f"📈 **HOURLY SUMMARY**\n"
    message += f"🕐 {timestamp}\n"
    message += "=" * 40 + "\n\n"
    
    # Calculate hourly statistics
    for commodity, data in prices.items():
        if commodity in price_history and len(price_history[commodity]) > 0:
            recent_prices = [p['price'] for p in price_history[commodity][-6:] if p['price']]
            
            if recent_prices:
                current = data['price'] if data['price'] else recent_prices[-1]
                avg = sum(recent_prices) / len(recent_prices)
                min_price = min(recent_prices)
                max_price = max(recent_prices)
                
                emoji = {'Robusta Coffee': '☕', 'Arabica Coffee': '☕', 
                        'Sugar No.11': '🍬', 'Cocoa': '🍫', 
                        'Wheat': '🌾', 'Soybean Oil': '🌿', 
                        'Palm Oil': '🌴'}.get(commodity, '📦')
                
                message += f"{emoji} **{commodity}**\n"
                message += f"   Current: ${current:.2f}\n"
                message += f"   Avg: ${avg:.2f}\n"
                message += f"   Range: ${min_price:.2f} - ${max_price:.2f}\n\n"
    
    # Get AI analysis if available
    if GEMINI_API_KEY:
        analysis = get_ai_analysis(prices)
        if analysis:
            message += "\n🤖 **AI Market Analysis**\n"
            message += analysis + "\n"
    
    message += "\n_Hourly summary · Next in 1 hour_"
    return message


def get_ai_analysis(prices):
    """Get AI-powered market analysis using Gemini."""
    if not GEMINI_API_KEY:
        return None
    
    try:
        # Prepare price data for analysis
        price_summary = "\n".join([
            f"{commodity}: ${data['price']:.2f}" 
            for commodity, data in prices.items() 
            if data['price']
        ])
        
        prompt = f"""Analyze these commodity prices and provide a brief market insight (2-3 sentences):

{price_summary}

Focus on any notable trends or significant price movements."""
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                text = result['candidates'][0]['content']['parts'][0]['text']
                return text.strip()
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error getting AI analysis: {e}")
        return None


def generate_weekly_pdf(filename="weekly_report.pdf"):
    """Generate comprehensive weekly PDF report."""
    logger.info("📄 Generating weekly PDF report...")
    
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        title = Paragraph("Weekly Commodity Price Report", title_style)
        elements.append(title)
        
        # Date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_text = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        date_para = Paragraph(date_text, styles['Normal'])
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        # Summary table
        table_data = [['Commodity', 'Current Price', 'Week Avg', 'Week Change', 'Unit']]
        
        for commodity in COMMODITIES.keys():
            if commodity in price_history and len(price_history[commodity]) > 0:
                recent = [p['price'] for p in price_history[commodity] if p['price']]
                
                if recent:
                    current = recent[-1]
                    avg = sum(recent) / len(recent)
                    change = ((current - recent[0]) / recent[0] * 100) if len(recent) > 1 else 0
                    unit = COMMODITIES[commodity]['unit']
                    
                    change_str = f"{change:+.2f}%"
                    table_data.append([
                        commodity,
                        f"${current:.2f}",
                        f"${avg:.2f}",
                        change_str,
                        unit
                    ])
        
        table = Table(table_data, colWidths=[2*inch, 1.2*inch, 1.2*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 30))
        
        # Generate price charts
        for commodity in list(COMMODITIES.keys())[:3]:  # Limit to 3 charts for space
            if commodity in price_history and len(price_history[commodity]) > 0:
                chart_buffer = generate_price_chart(commodity)
                if chart_buffer:
                    elements.append(Paragraph(f"{commodity} - Weekly Trend", styles['Heading2']))
                    img = Image(chart_buffer, width=5*inch, height=2.5*inch)
                    elements.append(img)
                    elements.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        logger.info("✅ PDF report generated successfully")
        return buffer.getvalue()
        
    except Exception as e:
        logger.error(f"❌ Error generating PDF: {e}")
        return None


def generate_price_chart(commodity):
    """Generate price chart for a commodity."""
    try:
        if commodity not in price_history or len(price_history[commodity]) == 0:
            return None
        
        data = price_history[commodity]
        timestamps = [datetime.fromisoformat(p['timestamp']) for p in data if p['price']]
        prices = [p['price'] for p in data if p['price']]
        
        if not prices:
            return None
        
        plt.figure(figsize=(8, 4))
        plt.plot(timestamps, prices, marker='o', linewidth=2, markersize=4)
        plt.title(f'{commodity} Price Trend')
        plt.xlabel('Time')
        plt.ylabel(f'Price ({COMMODITIES[commodity]["unit"]})')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        plt.close()
        
        return buffer
        
    except Exception as e:
        logger.error(f"❌ Error generating chart for {commodity}: {e}")
        return None


def store_price_data(prices):
    """Store price data in history."""
    for commodity, data in prices.items():
        if commodity not in price_history:
            price_history[commodity] = []
        
        price_history[commodity].append(data)
        
        # Keep only last 7 days of data (7 * 24 * 6 = 1008 entries at 10-min intervals)
        if len(price_history[commodity]) > 1008:
            price_history[commodity] = price_history[commodity][-1008:]


def monitoring_cycle():
    """Run complete monitoring cycle."""
    global last_hourly_update, last_weekly_report
    
    now = datetime.now()
    logger.info(f"\n⏰ Monitoring cycle at {now.strftime('%H:%M:%S')}")
    logger.info("=" * 60)
    
    # Fetch all prices
    prices = fetch_all_prices()
    
    # Store in history
    store_price_data(prices)
    
    # Send 10-minute update
    message_10min = format_10min_message(prices)
    send_telegram_message(message_10min)
    
    # Check if hourly update is due
    if last_hourly_update is None or (now - last_hourly_update).seconds >= 3600:
        logger.info("📊 Sending hourly summary...")
        message_hourly = format_hourly_summary(prices)
        send_telegram_message(message_hourly)
        last_hourly_update = now
    
    # Check if weekly report is due (every Sunday at ~15:00)
    if last_weekly_report is None or (now - last_weekly_report).days >= 7:
        if now.weekday() == 6 and now.hour >= 15:  # Sunday, after 3 PM
            logger.info("📄 Generating weekly report...")
            pdf_bytes = generate_weekly_pdf()
            
            if pdf_bytes:
                # Send via Telegram
                send_telegram_document(
                    pdf_bytes,
                    f"weekly_report_{now.strftime('%Y%m%d')}.pdf",
                    "📊 Weekly Commodity Price Report"
                )
                
                # Send via Email
                if EMAIL_FROM and EMAIL_PASSWORD:
                    email_body = f"""
                    <h2>Weekly Commodity Price Report</h2>
                    <p>Please find attached the weekly commodity price report for {now.strftime('%Y-%m-%d')}.</p>
                    <p>This report includes price trends and analysis for all monitored commodities.</p>
                    """
                    send_email(
                        f"Weekly Commodity Report - {now.strftime('%Y-%m-%d')}",
                        email_body,
                        pdf_bytes,
                        f"weekly_report_{now.strftime('%Y%m%d')}.pdf"
                    )
                
                last_weekly_report = now
    
    logger.info("✅ Monitoring cycle completed")
    logger.info("=" * 60 + "\n")


def start_monitoring():
    """Start the monitoring loop."""
    logger.info("🚀 Starting Commodity Price Monitor")
    logger.info(f"📱 Telegram: {'✅' if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID else '❌'}")
    logger.info(f"📧 Email: {'✅' if EMAIL_FROM and EMAIL_PASSWORD else '❌'}")
    logger.info(f"🤖 AI Analysis: {'✅' if GEMINI_API_KEY else '❌'}")
    
    # Run initial cycle
    monitoring_cycle()
    
    # Continue every 10 minutes
    while True:
        time.sleep(600)  # 10 minutes
        try:
            monitoring_cycle()
        except Exception as e:
            logger.error(f"❌ Error in monitoring cycle: {e}")


@app.route('/')
def home():
    return jsonify({
        'status': 'running',
        'service': 'Commodity Price Monitor',
        'features': {
            'telegram': bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID),
            'email': bool(EMAIL_FROM and EMAIL_PASSWORD),
            'ai_analysis': bool(GEMINI_API_KEY)
        },
        'monitored_commodities': len(COMMODITIES),
        'data_points': sum(len(h) for h in price_history.values())
    })


@app.route('/monitor')
def monitor_endpoint():
    """Manual trigger endpoint."""
    try:
        monitoring_cycle()
        return jsonify({'status': 'success', 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/prices')
def get_prices():
    """Get current prices."""
    latest_prices = {}
    for commodity, history in price_history.items():
        if history:
            latest_prices[commodity] = history[-1]
    
    return jsonify(latest_prices)


@app.route('/history/<commodity>')
def get_history(commodity):
    """Get price history for a commodity."""
    if commodity in price_history:
        return jsonify(price_history[commodity])
    return jsonify({'error': 'Commodity not found'}), 404


@app.route('/report/generate')
def generate_report():
    """Generate and download weekly report."""
    try:
        pdf_bytes = generate_weekly_pdf()
        if pdf_bytes:
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'report_{datetime.now().strftime("%Y%m%d")}.pdf'
            )
        return jsonify({'error': 'Failed to generate report'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Start monitoring thread
    monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()
    
    # Start Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port)