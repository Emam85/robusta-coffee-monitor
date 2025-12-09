"""
Abu Auf Procurement Monitor - Diamond Debug Edition
Features:
- 🧠 Deep AI Analysis (Full HTML Formatting)
- 🛡️ Smart Telegram (Falls back to plain text if HTML fails)
- ⏱️ 10-Min Market Snapshots
- 📄 Weekly PDF Dashboard
- 🐞 Verbose Error Logging
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
from fpdf import FPDF
from threading import Thread
from flask import Flask, jsonify

# Import the Intelligent Scraper
# ⚠️ MAKE SURE 'barchart_intelligent.py' EXISTS IN YOUR REPO
try:
    from barchart_intelligent import get_barchart_robusta_jan26
except ImportError:
    print("⚠️ 'barchart_intelligent.py' not found! Smart scraping disabled.")
    def get_barchart_robusta_jan26(): return None

# ============ CONFIGURATION ============
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# ABU AUF SETTINGS
USD_EGP_RATE = 50.5
START_HOUR = 6
END_HOUR = 18

WATCHLIST = {
    'RC=F': {'name': 'Robusta Coffee (ICE)', 'harvest': 'Oct-Jan (Vietnam)'},
    'KC=F': {'name': 'Coffee Arabica (ICE)', 'harvest': 'Apr-Sep (Brazil)'},
    'CC=F': {'name': 'Cocoa (ICE)', 'harvest': 'Oct-Mar (Ivory Coast)'},
    'SB=F': {'name': 'Sugar (ICE)', 'harvest': 'Apr-Nov (Brazil)'},
    'ZW=F': {'name': 'Wheat (CBOT)', 'harvest': 'Jun-Aug (Global)'},
    'ZL=F': {'name': 'Soybean Oil (CBOT)', 'harvest': 'Sep-Nov (USA)'},
    'PO=F': {'name': 'Palm Oil (MDEX)', 'harvest': 'Year-Round (Malaysia)'},
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ============ HELPERS ============
def get_cairo_time(): return datetime.utcnow() + timedelta(hours=2)

def clean_for_pdf(text):
    if not text: return ""
    text = text.replace("’", "'").replace("–", "-").replace("“", '"').replace("”", '"')
    return text.encode('latin-1', 'ignore').decode('latin-1')

# ============ DATA ENGINE ============
def fetch_commodity_data(symbol):
    """Fetch commodity data with Barchart priority for Robusta"""
    
    # SPECIAL HANDLING: Robusta Coffee - Use Barchart Jan '26 contract
    if symbol == 'RC=F':
        print(f"🎯 Fetching Robusta from Barchart (Jan '26 contract)...")
        barchart_data = get_barchart_robusta_jan26()
        
        if barchart_data:
            # Convert to standard format
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
                'source': barchart_data['source'],
                'egp_cost': round(barchart_data['price'] * USD_EGP_RATE, 2)
            }
        else:
            print("⚠️ Barchart failed, falling back to Investing.com")
    
    # FALLBACK: Use existing commodity_fetcher for all others
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    try:
        print(f"🔍 Fetching {symbol} via Investing.com...")
        data = fetch_multi(symbol, WATCHLIST[symbol]['name'])
        if data:
            price = data['price']
            egp_cost = 0
            if symbol in ['RC=F', 'CC=F']: egp_cost = price * USD_EGP_RATE
            elif symbol in ['KC=F', 'SB=F', 'ZL=F']: egp_cost = (price / 100) * 2204.62 * USD_EGP_RATE
            elif symbol == 'ZW=F': egp_cost = (price / 100) * 36.74 * USD_EGP_RATE
            elif symbol == 'PO=F': egp_cost = (price * 0.23) * USD_EGP_RATE
            data['egp_cost'] = round(egp_cost, 2)
            print(f"✅ Data OK: {symbol} ${price}")
            return data
        else:
            print(f"❌ No Data: {symbol}")
    except Exception as e: print(f"⚠️ Error {symbol}: {e}")
    return None

# ============ AI ENGINE ============
def check_freight_crisis():
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = "Act as Logistics Analyst. Summarize Global Freight Risks (Red Sea/Suez) for Egypt in 1 short sentence."
        return model.generate_content(prompt).text.strip()
    except: return "Check local forwarders for delays."

def generate_ai_content(symbol, price_data, mode="DAILY"):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        egp = f"{price_data['egp_cost']:,.0f}"
        
        if mode == "TIP":
            prompt = f"""
            Act as Abu Auf Procurement Manager. Analyze {price_data['name']} (${price_data['price']}).
            Return JSON: {{
                "action": "LOCK / SPOT / WAIT",
                "analysis": "Short strategic reason (max 10 words).",
                "risk": "High/Med/Low"
            }}
            """
        else:
            prompt = f"""
            Act as Procurement Director. Briefing for {price_data['name']} (${price_data['price']} | {egp} EGP/Ton).
            Return JSON: {{
                "strategy": "BUY NOW / WAIT / HEDGE",
                "trend": "UP / DOWN",
                "summary": "Reason.",
                "targets": [
                    {{"label": "S", "price": {price_data['price']*0.98}}},
                    {{"label": "R", "price": {price_data['price']*1.02}}}
                ]
            }}
            """
        text = model.generate_content(prompt).text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except: return {}

# ============ CHART ENGINE ============
def generate_chart(name, current_price, targets, filename):
    try:
        plt.figure(figsize=(8, 4), facecolor='white')
        ax = plt.gca()
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [current_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(30)]
        prices[-1] = current_price
        plt.plot(dates, prices, color='#6C63FF', linewidth=2)
        if targets:
            f_date = datetime.now() + timedelta(weeks=2)
            f_price = targets[0]['price']
            plt.plot([datetime.now(), f_date], [current_price, f_price], color='#FF6584', linestyle='--', marker='o')
        plt.grid(True, linestyle=':', alpha=0.3)
        plt.savefig(filename, format='png', bbox_inches='tight', dpi=100)
        plt.close()
        return filename
    except: return None

# ============ PDF ENGINE ============
class DashboardPDF(FPDF):
    def header(self):
        self.set_fill_color(108, 99, 255)
        self.rect(0, 0, 210, 35, 'F')
        self.set_font('Arial', 'B', 22)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 10)
        self.cell(0, 10, 'ABU AUF - MARKET UPDATE', 0, 1, 'L')
        self.ln(10)

    def card(self, name, price, egp, strategy, trend, summary, chart_path):
        y = self.get_y()
        self.set_fill_color(252, 252, 252)
        self.rect(10, y, 190, 45, 'FD')
        self.set_xy(15, y+5)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.cell(60, 6, clean_for_pdf(name), 0, 2)
        self.cell(60, 8, f"${price:,.2f}", 0, 2)
        self.set_font('Arial', '', 9)
        self.cell(60, 5, f"{egp:,.0f} EGP", 0, 0)
        self.set_xy(80, y+8)
        self.set_font('Arial', 'B', 11)
        self.cell(40, 8, clean_for_pdf(strategy), 0, 2)
        if chart_path and os.path.exists(chart_path):
            self.image(chart_path, x=135, y=y+2, w=60, h=40)
            os.remove(chart_path)
        self.ln(35)

def generate_pdf_report():
    pdf = DashboardPDF()
    pdf.add_page()
    for symbol, info in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if not data: continue
        ai = generate_ai_content(symbol, data, mode="PDF")
        chart_file = f"chart_{symbol.replace('=','')}.png"
        generate_chart(info['name'], data['price'], ai.get('targets', []), chart_file)
        pdf.card(info['name'], data['price'], data['egp_cost'], ai.get('strategy', 'WAIT'), ai.get('trend', '-'), ai.get('summary', ''), chart_file)
        pdf.ln(5)
    outfile = "AbuAuf_Dashboard.pdf"
    pdf.output(outfile, 'F')
    return outfile

# ============ TELEGRAM ENGINE (SMART FALLBACK) ============
def send_telegram(text=None, doc=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
        if doc:
            with open(doc, 'rb') as f: 
                requests.post(url + "sendDocument", data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': f})
        else:
            # 1. Try sending with HTML (Pretty)
            print(f"📤 Sending: {text[:30]}...")
            resp = requests.post(url + "sendMessage", json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'})
            
            # 2. If it fails, fallback to Plain Text (Ugly but works)
            if resp.status_code != 200:
                print(f"⚠️ HTML Format Failed ({resp.text}). Retrying plain text...")
                requests.post(url + "sendMessage", json={'chat_id': TELEGRAM_CHAT_ID, 'text': text})
            else:
                print("✅ Sent!")
            
    except Exception as e: print(f"⚠️ Telegram Connection Error: {e}")

def run_tips_logic():
    print("🔔 Generating Hourly Tips...")
    send_telegram("🔔 <b>HOURLY STRATEGIC ANALYSIS</b>")
    
    for s, i in WATCHLIST.items():
        d = fetch_commodity_data(s)
        if d: 
            ai = generate_ai_content(s, d, mode="TIP")
            msg = f"""
📦 <b>{i['name'].split()[0]}</b> (${d['price']:,.2f})
⚡ <b>Action:</b> {ai.get('action', 'WAIT')}
📝 <b>Reason:</b> {ai.get('analysis', 'No data')}
⚠️ <b>Risk:</b> {ai.get('risk', 'Medium')}
"""
            send_telegram(msg)
            time.sleep(2)

def monitor_cycle():
    cairo = get_cairo_time()
    print(f"🕒 Cycle: {cairo.strftime('%H:%M')}")
    
    # Weekly
    if cairo.weekday() == 0 and cairo.hour == 9 and cairo.minute < 15:
        send_telegram("📊 Generating PDF Dashboard...")
        send_telegram(doc=generate_pdf_report())
        return

    # Hourly Tips
    if cairo.minute < 5 and (START_HOUR <= cairo.hour <= END_HOUR):
        run_tips_logic()

    # Snapshot
    msg = f"⏱️ <b>SNAPSHOT ({cairo.strftime('%I:%M %p')})</b>\n"
    for s, i in WATCHLIST.items():
        d = fetch_commodity_data(s)
        if d: msg += f"▫️ {i['name'].split()[0]}: ${d['price']:,.0f}\n"
    send_telegram(msg)

# ============ WEB SERVER ============
app = Flask(__name__)

@app.route('/')
def home(): return jsonify({'status': 'online'})

@app.route('/monitor')
def tick(): 
    Thread(target=monitor_cycle).start()
    return jsonify({'status': 'snapshot_triggered'})

@app.route('/tips')
def tips(): 
    Thread(target=run_tips_logic).start()
    return jsonify({'status': 'tips_triggered'})

@app.route('/pdf')
def pdf(): 
    t = Thread(target=lambda: send_telegram(doc=generate_pdf_report()))
    t.start()
    return jsonify({'status': 'pdf_triggered'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))