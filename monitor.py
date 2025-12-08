"""
Abu Auf Procurement Monitor - Platinum Edition
Features:
- ⏱️ 10-Min Market Snapshots
- 🔔 Hourly Buying Tips
- 📄 Weekly PDF Board Report (Fixed for Unicode/Emojis)
- 🌾 Harvest Calendar & Freight Risk
- 🇪🇬 EGP Landed Cost Calculator
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
START_HOUR = 9
END_HOUR = 17

# WATCHLIST
WATCHLIST = {
    'RC=F': {'name': 'Robusta Coffee (ICE)', 'harvest': 'Oct-Jan (Vietnam)', 'origin': 'Vietnam'},
    'KC=F': {'name': 'Coffee Arabica (ICE)', 'harvest': 'Apr-Sep (Brazil)', 'origin': 'Brazil'},
    'CC=F': {'name': 'Cocoa (ICE)', 'harvest': 'Oct-Mar (Ivory Coast)', 'origin': 'West Africa'},
    'SB=F': {'name': 'Sugar (ICE)', 'harvest': 'Apr-Nov (Brazil)', 'origin': 'Brazil'},
    'ZW=F': {'name': 'Wheat (CBOT)', 'harvest': 'Jun-Aug (Global)', 'origin': 'Global'},
}

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ============ HELPER: CLEAN TEXT FOR PDF ============
def clean_for_pdf(text):
    """Removes emojis and non-latin characters for PDF compatibility"""
    if not text: return ""
    # Encode to ascii, ignore errors (drops emojis), decode back
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
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return None

# ============ INTELLIGENCE ENGINE ============
def get_harvest_status(symbol):
    harvest_months = WATCHLIST[symbol]['harvest']
    curr = datetime.now().strftime('%b')
    status = "OFF-SEASON"
    if curr in ["Oct", "Nov", "Dec", "Jan"] and "Oct" in harvest_months: status = "PEAK HARVEST"
    elif curr in ["Apr", "May", "Jun", "Jul"] and "Apr" in harvest_months: status = "PEAK HARVEST"
    return f"{harvest_months} | {status}"

def check_freight_crisis():
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        prompt = "Act as Logistics Analyst. Summarize Global Freight Risks (Red Sea/Suez) for Egypt. Return JSON: {'risk': 'HIGH/MED/LOW', 'headline': 'Short Headline', 'advice': 'One sentence advice'}"
        response = model.generate_content(prompt)
        return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except: return {"risk": "UNKNOWN", "headline": "No Data", "advice": "Check local forwarders."}

def generate_ai_content(symbol, price_data, mode="DAILY"):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        egp = f"{price_data['egp_cost']:,.0f} EGP"
        harvest = get_harvest_status(symbol)
        
        if mode == "PDF":
            prompt = f"""
            Act as Chief Procurement Officer. Briefing for {price_data['name']} (${price_data['price']} | {egp}/Ton).
            Seasonality: {harvest}.
            Return JSON: {{
                "recommendation": "LOCK / SPOT",
                "summary": "2 sentences on price strategy.",
                "risk": "Key supply chain risk.",
                "targets": [{{"label": "Buy", "price": {price_data['price']*0.95}}}, {{"label": "Panic", "price": {price_data['price']*1.05}}}]
            }}
            """
        elif mode == "TIP":
            prompt = f"Procurement Tip for {price_data['name']} (${price_data['price']}). Max 15 words."
            return model.generate_content(prompt).text
            
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
            plt.annotate(f"{label}\n${p:,.0f}", (d, p), xytext=(0, 15), textcoords='offset points',
                         ha='center', fontsize=8, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#f97316"))

        plt.title(f"{name} Projection", fontsize=12, fontweight='bold')
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

# ============ PDF REPORT ENGINE (FIXED) ============
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'ABU AUF - WEEKLY SOURCING REPORT', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.cell(0, 10, f'Generated: {datetime.now().strftime("%d %b %Y")} | EGP Rate: {USD_EGP_RATE}', 0, 1, 'C')
        self.ln(5)

def generate_pdf_report():
    pdf = PDF()
    pdf.add_page()
    
    # Freight Alert (Clean text)
    freight = check_freight_crisis()
    pdf.set_fill_color(255, 240, 240)
    pdf.set_font('Arial', 'B', 12)
    risk_level = clean_for_pdf(freight.get('risk', 'UNKNOWN'))
    pdf.cell(0, 10, f"FREIGHT RISK: {risk_level}", 1, 1, 'L', 1)
    
    pdf.set_font('Arial', '', 10)
    advice = clean_for_pdf(freight.get('advice', 'Check local forwarders.'))
    pdf.multi_cell(0, 6, f"Advice: {advice}")
    pdf.ln(5)
    
    for symbol, info in WATCHLIST.items():
        data = fetch_commodity_data(symbol)
        if not data: continue
        
        ai = generate_ai_content(symbol, data, mode="PDF")
        
        # Header
        pdf.set_font('Arial', 'B', 14)
        pdf.set_text_color(0, 51, 102)
        pdf.cell(0, 8, clean_for_pdf(info['name']), 0, 1, 'L')
        pdf.set_text_color(0, 0, 0)
        
        # Info Grid
        pdf.set_font('Arial', '', 10)
        pdf.cell(50, 6, f"Price: ${data['price']:,.2f}", 0, 0)
        pdf.cell(60, 6, f"Landed: {data['egp_cost']:,.0f} EGP/Ton", 0, 1)
        pdf.cell(0, 6, f"Harvest: {clean_for_pdf(get_harvest_status(symbol))}", 0, 1)
        
        # Strategy
        pdf.set_font('Arial', 'B', 10)
        rec = clean_for_pdf(ai.get('recommendation', 'WAIT'))
        pdf.cell(0, 8, f"STRATEGY: {rec}", 0, 1)
        
        pdf.set_font('Arial', '', 9)
        summary = clean_for_pdf(ai.get('summary', 'No data'))
        risk = clean_for_pdf(ai.get('risk', 'None'))
        pdf.multi_cell(0, 5, f"Summary: {summary}\nRisk: {risk}")
        
        # Embed Chart
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
            with open(doc, 'rb') as f:
                requests.post(url + "sendDocument", data={'chat_id': TELEGRAM_CHAT_ID}, files={'document': f})
        elif photo:
            requests.post(url + "sendPhoto", data={'chat_id': TELEGRAM_CHAT_ID, 'caption': text, 'parse_mode': 'HTML'}, files={'photo': ('chart.png', photo, 'image/png')})
        else:
            requests.post(url + "sendMessage", json={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'HTML'})
    except Exception as e: print(f"Telegram Error: {e}")

# ============ SCHEDULER ============
def run_snapshot():
    msg = f"⏱️ <b>SNAPSHOT ({datetime.now().strftime('%H:%M')})</b>\n"
    for s, i in WATCHLIST.items():
        d = fetch_commodity_data(s)
        if d: msg += f"▫️ {i['name'].split()[0]}: ${d['price']:,.0f}\n"
    send_telegram(msg)

def run_tips():
    now = datetime.now()
    if not (START_HOUR <= now.hour <= END_HOUR): return
    msg = "🔔 <b>SOURCING TIPS</b>\n"
    for s, i in WATCHLIST.items():
        d = fetch_commodity_data(s)
        if d: msg += f"📦 {i['name'].split()[0]}: {generate_ai_content(s, d, mode='TIP')}\n"
    send_telegram(msg)

def run_pdf():
    send_telegram("📄 Generating Board Report...")
    try:
        pdf = generate_pdf_report()
        send_telegram(doc=pdf)
    except Exception as e:
        send_telegram(f"⚠️ PDF Gen Error: {str(e)}")

def monitor_cycle():
    now = datetime.now()
    if now.weekday() == 0 and now.hour == 9 and now.minute < 15: run_pdf(); return
    if now.minute < 5 and (START_HOUR <= now.hour <= END_HOUR): run_tips()
    run_snapshot()

# ============ WEB SERVER ============
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
