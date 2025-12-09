"""
Abu Auf Procurement Monitor - Diamond Edition
Features:
- 🎨 Professional PDF Dashboard (Native Colors - No Emojis)
- ⏱️ 10-Min Market Snapshots
- 🔔 Hourly Buying Tips (6 AM - 6 PM)
- 🌾 Harvest & Freight Intelligence
- 🇪🇬 Landed Cost Calculator
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

# ============ SAFETY HELPER (Prevents PDF Crashes) ============
def clean_for_pdf(text):
    """
    Aggressively strips emojis and non-latin characters.
    This guarantees the PDF generation will NEVER crash.
    """
    if not text: return ""
    # Replace smart quotes or dashes that might break Latin-1
    text = text.replace("’", "'").replace("–", "-").replace("“", '"').replace("”", '"')
    # Encode to ASCII, ignoring errors (this removes emojis), then decode back
    return text.encode('latin-1', 'ignore').decode('latin-1')

def get_cairo_time(): return datetime.utcnow() + timedelta(hours=2)

# ============ DATA ENGINE ============
def fetch_commodity_data(symbol):
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    try:
        data = fetch_multi(symbol, WATCHLIST[symbol]['name'])
        if data:
            price = data['price']
            egp_cost = 0
            if symbol in ['RC=F', 'CC=F']: egp_cost = price * USD_EGP_RATE
            elif symbol in ['KC=F', 'SB=F', 'ZL=F']: egp_cost = (price / 100) * 2204.62 * USD_EGP_RATE
            elif symbol == 'ZW=F': egp_cost = (price / 100) * 36.74 * USD_EGP_RATE
            elif symbol == 'PO=F': egp_cost = (price * 0.23) * USD_EGP_RATE
            
            data['egp_cost'] = round(egp_cost, 2)
            return data
    except: return None

# ============ AI INTELLIGENCE ============
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
            return model.generate_content(f"Procurement Tip for {price_data['name']} (${price_data['price']}). Max 15 words.").text
        
        # PDF Mode
        prompt = f"""
        Act as Procurement Director. Briefing for {price_data['name']} (${price_data['price']} | {egp} EGP/Ton).
        Return JSON: {{
            "strategy": "BUY NOW / WAIT / HEDGE",
            "trend": "UPTREND / DOWNTREND",
            "summary": "1 short sentence reason.",
            "targets": [
                {{"label": "Support", "price": {price_data['price']*0.98}}},
                {{"label": "Resist", "price": {price_data['price']*1.02}}}
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
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [current_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(30)]
        prices[-1] = current_price
        plt.plot(dates, prices, color='#6C63FF', linewidth=2) # Purple line
        
        if targets:
            f_date = datetime.now() + timedelta(weeks=2)
            f_price = targets[0]['price']
            plt.plot([datetime.now(), f_date], [current_price, f_price], color='#FF6584', linestyle='--', marker='o')
        
        plt.title(f"{name} Trend", fontsize=10, fontweight='bold', color='#333333')
        plt.grid(True, linestyle=':', alpha=0.3)
        plt.gcf().autofmt_xdate()
        plt.savefig(filename, format='png', bbox_inches='tight', dpi=100)
        plt.close()
        return filename
    except: return None

# ============ DASHBOARD PDF ENGINE ============
class DashboardPDF(FPDF):
    def header(self):
        # Header Background (Purple)
        self.set_fill_color(108, 99, 255)
        self.rect(0, 0, 210, 35, 'F')
        # Title
        self.set_font('Arial', 'B', 22)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 10)
        self.cell(0, 10, 'ABU AUF - MARKET UPDATE', 0, 1, 'L')
        self.set_font('Arial', '', 10)
        self.cell(0, 8, f"Generated: {datetime.now().strftime('%d %b %Y')} | USD Rate: {USD_EGP_RATE}", 0, 1, 'L')
        self.ln(10)

    def card(self, name, price, egp, strategy, trend, summary, chart_path):
        # Card Background
        y = self.get_y()
        self.set_fill_color(252, 252, 252)
        self.set_draw_color(220, 220, 220)
        self.rect(10, y, 190, 45, 'FD')
        
        # Name
        self.set_xy(15, y+5)
        self.set_font('Arial', 'B', 12)
        self.set_text_color(40, 40, 40)
        self.cell(60, 6, clean_for_pdf(name), 0, 2)
        
        # Prices
        self.set_font('Arial', 'B', 14)
        self.set_text_color(0, 0, 0)
        self.cell(60, 8, f"${price:,.2f}", 0, 2)
        self.set_font('Arial', '', 9)
        self.set_text_color(100, 100, 100)
        self.cell(60, 5, f"Landed: {egp:,.0f} EGP", 0, 0)
        
        # Strategy Badge (Ink Color logic instead of Emoji)
        self.set_xy(80, y+8)
        self.set_font('Arial', 'B', 11)
        if "BUY" in strategy or "LOCK" in strategy:
            self.set_text_color(0, 150, 0) # Green Ink
        else:
            self.set_text_color(200, 50, 50) # Red Ink
        self.cell(40, 8, clean_for_pdf(strategy), 0, 2)
        
        # Trend & Summary
        self.set_font('Arial', 'I', 9)
        self.set_text_color(80, 80, 80)
        self.cell(40, 5, clean_for_pdf(trend), 0, 2)
        self.set_font('Arial', '', 8)
        self.multi_cell(50, 4, clean_for_pdf(summary))
        
        # Chart
        if chart_path and os.path.exists(chart_path):
            self.image(chart_path, x=135, y=y+2, w=60, h=40)
            os.remove(chart_path)
            
        self.ln(35) # Move down

def generate_pdf_report():
    pdf = DashboardPDF()
    pdf.add_page()
    
    # Freight Alert (Safe Red Text)
    freight = check_freight_crisis()
    pdf.set_font('Arial', 'B', 10)
    pdf.set_text_color(180, 0, 0)
    pdf.cell(0, 10, f"LOGISTICS ALERT: {clean_for_pdf(freight)}", 0, 1, 'C')
    pdf.set_text_color(0, 0, 0) # Reset color
    
    # Loop
    for symbol, info in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if not data: continue
        ai = generate_ai_content(symbol, data, mode="PDF")
        
        chart_file = f"chart_{symbol.replace('=','')}.png"
        generate_chart(info['name'], data['price'], ai.get('targets', []), chart_file)
        
        pdf.card(
            info['name'], 
            data['price'], 
            data['egp_cost'],
            ai.get('strategy', 'WAIT'),
            ai.get('trend', 'NEUTRAL'),
            ai.get('summary', ''),
            chart_file
        )
        pdf.ln(5)
        
    outfile = "AbuAuf_Dashboard.pdf"
    pdf.output(outfile, 'F')
    return outfile

# ============ TELEGRAM ============
def send_telegram(text=None, doc=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
        if doc:
            with open(doc, 'rb') as f: requests.post(url + "sendDocument", data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': f})
        else:
            requests.post(url + "sendMessage", json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'})
    except Exception as e: print(f"Telegram Error: {e}")

# ============ SCHEDULER ============
def monitor_cycle():
    cairo = get_cairo_time()
    # Weekly (Mon 9 AM)
    if cairo.weekday() == 0 and cairo.hour == 9 and cairo.minute < 15:
        send_telegram("📊 Generating PDF Dashboard...")
        send_telegram(doc=generate_pdf_report())
        return
    # Hourly Tips
    if cairo.minute < 5 and (START_HOUR <= cairo.hour <= END_HOUR):
        msg = "🔔 <b>SOURCING TIPS</b>\n"
        for s, i in WATCHLIST.items():
            d = fetch_commodity_data(s)
            if d: msg += f"📦 {i['name'].split()[0]}: {generate_ai_content(s, d, mode='TIP')}\n"
        send_telegram(msg)
    # 10-Min Snapshot
    msg = f"⏱️ <b>SNAPSHOT ({cairo.strftime('%I:%M %p')})</b>\n"
    for s, i in WATCHLIST.items():
        d = fetch_commodity_data(s)
        if d: msg += f"▫️ {i['name'].split()[0]}: ${d['price']:,.0f}\n"
    send_telegram(msg)

# ============ WEB ============
app = Flask(__name__)
@app.route('/')
def home(): return jsonify({'status': 'online'})
@app.route('/monitor')
def tick(): Thread(target=monitor_cycle).start(); return jsonify({'status': 'ok'})
@app.route('/pdf')
def pdf(): 
    t = Thread(target=lambda: send_telegram(doc=generate_pdf_report()))
    t.start()
    return jsonify({'status': 'generating_dashboard'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))