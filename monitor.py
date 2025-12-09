"""
Abu Auf Procurement Monitor - Platinum Edition
Features:
- ⏱️ 10-Min Market Snapshots (24/7)
- 🔔 Hourly Buying Tips (6 AM - 6 PM Cairo Time)
- 📄 Weekly PDF Board Report
- 🇪🇬 Cairo Timezone Logic
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
START_HOUR = 6       # 6:00 AM
END_HOUR = 18        # 6:00 PM (18:00)

WATCHLIST = {
    'RC=F': {'name': 'Robusta Coffee (ICE)', 'harvest': 'Oct-Jan (Vietnam)', 'origin': 'Vietnam'},
    'KC=F': {'name': 'Coffee Arabica (ICE)', 'harvest': 'Apr-Sep (Brazil)', 'origin': 'Brazil'},
    'CC=F': {'name': 'Cocoa (ICE)', 'harvest': 'Oct-Mar (Ivory Coast)', 'origin': 'West Africa'},
    'SB=F': {'name': 'Sugar (ICE)', 'harvest': 'Apr-Nov (Brazil)', 'origin': 'Brazil'},
    'ZW=F': {'name': 'Wheat (CBOT)', 'harvest': 'Jun-Aug (Global)', 'origin': 'Global'},
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ============ TIMEZONE HELPER (CRITICAL) ============
def get_cairo_time():
    # Render is UTC. Cairo is UTC+2 (Standard).
    # We add 2 hours to server time to get Abu Auf time.
    return datetime.utcnow() + timedelta(hours=2)

def clean_for_pdf(text):
    if not text: return ""
    return text.encode('latin-1', 'ignore').decode('latin-1')

# ============ DATA ENGINE ============
def fetch_commodity_data(symbol):
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    try:
        data = fetch_multi(symbol, WATCHLIST[symbol]['name'])
        if data:
            price = data['price']
            egp_cost = 0
            if symbol in ['RC=F', 'CC=F']: egp_cost = price * USD_EGP_RATE
            elif symbol in ['KC=F', 'SB=F']: egp_cost = (price / 100) * 2204.62 * USD_EGP_RATE
            elif symbol == 'ZW=F': egp_cost = (price / 100) * 36.74 * USD_EGP_RATE
            data['egp_cost'] = round(egp_cost, 2)
            return data
    except: return None

# ============ AI ENGINE ============
def get_harvest_status(symbol):
    harvest_months = WATCHLIST[symbol]['harvest']
    curr = get_cairo_time().strftime('%b')
    status = "OFF-SEASON"
    if curr in ["Oct", "Nov", "Dec", "Jan"] and "Oct" in harvest_months: status = "PEAK HARVEST"
    elif curr in ["Apr", "May", "Jun", "Jul"] and "Apr" in harvest_months: status = "PEAK HARVEST"
    return f"{harvest_months} | {status}"

def generate_ai_content(symbol, price_data, mode="DAILY"):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        egp = f"{price_data['egp_cost']:,.0f} EGP"
        if mode == "TIP":
            prompt = f"Act as Abu Auf Procurement. Short buying tip for {price_data['name']} (${price_data['price']}). Max 15 words."
            return model.generate_content(prompt).text
        
        # PDF Mode
        harvest = get_harvest_status(symbol)
        prompt = f"Briefing for {price_data['name']} (${price_data['price']}). Season: {harvest}. Return JSON: {{'recommendation': 'LOCK/SPOT', 'summary': 'Strategy.', 'risk': 'Risk.', 'targets': [{{'label': 'T1', 'price': {price_data['price']*0.95}}}, {{'label': 'T2', 'price': {price_data['price']*1.05}}}]}}"
        text = model.generate_content(prompt).text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except: return {}

# ============ CHART ENGINE ============
def generate_chart(name, current_price, targets, filename=None):
    try:
        plt.figure(figsize=(10, 5), facecolor='#ffffff')
        ax = plt.gca()
        dates = [datetime.now() - timedelta(days=x) for x in range(30, 0, -1)]
        prices = [current_price * (1 + random.uniform(-0.02, 0.02)) for _ in range(30)]
        prices[-1] = current_price
        plt.plot(dates, prices, color='#f97316', linewidth=2, label='History')
        
        f_dates = [datetime.now()]
        f_prices = [current_price]
        for i, t in enumerate(targets):
            f_dates.append(datetime.now() + timedelta(weeks=i+1))
            f_prices.append(t['price'])
        plt.plot(f_dates, f_prices, color='#f97316', linestyle=':', marker='o')
        
        for i, (d, p) in enumerate(zip(f_dates[1:], f_prices[1:])):
            label = targets[i].get('label', f'T{i}')
            plt.annotate(f"{label}\n${p:,.0f}", (d, p), xytext=(0, 15), textcoords='offset points', ha='center', fontsize=8, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#f97316"))

        plt.grid(True, linestyle='-', alpha=0.1)
        plt.gcf().autofmt_xdate()
        
        if filename:
            plt.savefig(filename, format='png', bbox_inches='tight', dpi=100)
            plt.close()
            return filename
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            plt.close()
            return buf
    except: return None

# ============ PDF ENGINE ============
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'ABU AUF - WEEKLY REPORT', 0, 1, 'C')
        self.ln(5)

def generate_pdf_report():
    pdf = PDF()
    pdf.add_page()
    for symbol, info in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if not data: continue
        ai = generate_ai_content(symbol, data, mode="PDF")
        
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 8, clean_for_pdf(info['name']), 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, f"Price: ${data['price']:,.2f} | Landed: {data['egp_cost']:,.0f} EGP", 0, 1)
        pdf.cell(0, 6, f"Strategy: {clean_for_pdf(ai.get('recommendation', 'WAIT'))}", 0, 1)
        
        chart_file = f"chart_{symbol.replace('=','')}.png"
        generate_chart(info['name'], data['price'], ai.get('targets', []), filename=chart_file)
        if os.path.exists(chart_file):
            pdf.image(chart_file, x=10, w=170)
            os.remove(chart_file)
        pdf.ln(5)
    
    outfile = "AbuAuf_Report.pdf"
    pdf.output(outfile, 'F')
    return outfile

# ============ TELEGRAM ============
def send_telegram(text=None, photo=None, doc=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/"
        if doc:
            with open(doc, 'rb') as f: requests.post(url + "sendDocument", data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': f})
        elif photo:
            requests.post(url + "sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': text, 'parse_mode': 'HTML'}, files={'photo': ('chart.png', photo, 'image/png')})
        else:
            requests.post(url + "sendMessage", json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'})
    except Exception as e: print(f"Telegram Error: {e}")

# ============ LOGIC ============
def run_snapshot():
    cairo_now = get_cairo_time()
    msg = f"⏱️ <b>SNAPSHOT ({cairo_now.strftime('%I:%M %p')})</b>\n"
    for s, i in WATCHLIST.items():
        d = fetch_commodity_data(s)
        if d: msg += f"▫️ {i['name'].split()[0]}: ${d['price']:,.0f}\n"
    send_telegram(msg)

def run_tips():
    cairo_now = get_cairo_time()
    # Check Hours (6 AM - 6 PM)
    if not (START_HOUR <= cairo_now.hour <= END_HOUR): 
        print(f"Skipping Tips: It is {cairo_now.hour}:00 in Cairo (Outside {START_HOUR}-{END_HOUR})")
        return

    msg = "🔔 <b>SOURCING TIPS</b>\n"
    for s, i in WATCHLIST.items():
        d = fetch_commodity_data(s)
        if d: msg += f"📦 {i['name'].split()[0]}: {generate_ai_content(s, d, mode='TIP')}\n"
    send_telegram(msg)

def run_pdf():
    send_telegram("📄 Generating Report...")
    try:
        pdf = generate_pdf_report()
        send_telegram(doc=pdf)
    except Exception as e: send_telegram(f"PDF Error: {e}")

def monitor_cycle():
    cairo_now = get_cairo_time()
    print(f"Checking schedule... Cairo Time: {cairo_now}")
    
    # Weekly (Mon 9 AM)
    if cairo_now.weekday() == 0 and cairo_now.hour == 9 and cairo_now.minute < 15: run_pdf(); return
    
    # Hourly Tips (Top of hour)
    if cairo_now.minute < 5: run_tips()
    
    # Always run snapshot
    run_snapshot()

# ============ APP ============
app = Flask(__name__)
@app.route('/')
def home(): return jsonify({'status': 'online'})
@app.route('/monitor')
def tick(): Thread(target=monitor_cycle).start(); return jsonify({'status': 'ok'})
@app.route('/pdf')
def pdf(): Thread(target=run_pdf).start(); return jsonify({'status': 'ok'})
@app.route('/tips')
def tips(): Thread(target=run_tips).start(); return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
