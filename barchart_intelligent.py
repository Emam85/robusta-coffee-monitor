"""
Multi-Layer Barchart Scraper with Cloudflare Bypass
Version: DIAMOND+ (Robusta + Arabica Support)
Supports: Robusta (RMF26), Arabica (Last 2 Contracts)
ENHANCED: Fetches Previous Close for accurate baselines
"""
import json
import time
import random
import re
import requests as standard_requests
from datetime import datetime

# Try to import smart libraries
try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    from fake_useragent import UserAgent
    HAS_FAKE_UA = True
except:
    HAS_FAKE_UA = False

# ============ HELPER: ROBUST PARSER ============
def extract_price_from_html(html):
    """Try 4 different ways to find the price in Barchart HTML"""
    price = None
    if not price:
        matches = re.findall(r'"lastPrice":"?([\d,.]+)"?', html)
        if matches: return float(matches[0].replace(',', ''))
    if not price:
        matches = re.findall(r'data-last-price="([\d,.]+)"', html)
        if matches: return float(matches[0].replace(',', ''))
    if not price and 'var bcQuoteApp' in html:
        try:
            start = html.find('var bcQuoteApp')
            end = html.find('};', start) + 1
            snippet = html[start:end]
            matches = re.findall(r'"lastPrice":\s*([\d,.]+)', snippet)
            if matches: return float(matches[0].replace(',', ''))
        except: pass
    if not price:
        matches = re.findall(r'<span[^>]*class="[^"]*last-change[^"]*"[^>]*>([\d,.]+)</span>', html)
        if matches: return float(matches[0].replace(',', ''))
    return None

def extract_details_from_html(html):
    """Extract Open and Previous Close from HTML"""
    open_val = None
    prev_close_val = None

    # --- EXTRACT OPEN ---
    match = re.search(r'"open":"?([\d,.]+)"?', html)
    if match: open_val = float(match.group(1).replace(',', ''))
    
    if not open_val:
        match = re.search(r'data-open="([\d,.]+)"', html)
        if match: open_val = float(match.group(1).replace(',', ''))

    if not open_val:
        match = re.search(r'(?:>|")Open(?:<|")[\s\S]*?(?:<span[^>]*>|<dd[^>]*>)([\d,.]+)', html)
        if match: open_val = float(match.group(1).replace(',', ''))

    # --- EXTRACT PREVIOUS CLOSE ---
    match = re.search(r'"previousClose":"?([\d,.]+)"?', html)
    if match: prev_close_val = float(match.group(1).replace(',', ''))

    if not prev_close_val:
        match = re.search(r'Previous Close[\s\S]*?<span[^>]*>([\d,.]+)', html)
        if match: prev_close_val = float(match.group(1).replace(',', ''))
        
    if not prev_close_val:
        match = re.search(r'Previous Close[\s\S]*?<td[^>]*>([\d,.]+)', html)
        if match: prev_close_val = float(match.group(1).replace(',', ''))

    return open_val, prev_close_val

# ============ METHOD 1: Official Hidden API ============
def method_1_api(symbol="RMF26"):
    print(f"  [Method 1] Trying Official API for {symbol}...")
    url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"
    # Added previousClose to fields
    params = {'fields': 'lastPrice,priceChange,high,low,open,previousClose', 'list': symbol}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': f'https://www.barchart.com/futures/quotes/{symbol}'
    }
    
    try:
        response = standard_requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                quote = data['data'][0]
                price = float(str(quote.get('lastPrice', 0)).replace(',', ''))
                open_price = float(str(quote.get('open', 0)).replace(',', ''))
                prev_close = float(str(quote.get('previousClose', 0)).replace(',', ''))
                
                if open_price == 0: open_price = None
                if prev_close == 0: prev_close = None

                return {
                    'price': price,
                    'change': float(str(quote.get('priceChange', 0)).replace(',', '')),
                    'high': float(str(quote.get('high', 0)).replace(',', '')),
                    'low': float(str(quote.get('low', 0)).replace(',', '')),
                    'open': open_price,
                    'previous_close': prev_close,
                    'source': 'Barchart API'
                }
    except: pass
    return None

# ============ METHOD 2: TLS Impersonation (curl_cffi) ============
def method_2_curl_cffi(symbol="RMF26"):
    if not HAS_CURL_CFFI: return None
    print(f"  [Method 2] Trying TLS Impersonation for {symbol}...")
    
    url = f"https://www.barchart.com/futures/quotes/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = cf_requests.get(url, headers=headers, impersonate="chrome120", timeout=10)
        if response.status_code == 200:
            price = extract_price_from_html(response.text)
            if price:
                open_price, prev_close = extract_details_from_html(response.text)
                if open_price and abs(open_price - price) < 0.01: open_price = None
                return {
                    'price': price, 'change': 0, 'high': price, 'low': price,
                    'open': open_price, 'previous_close': prev_close,
                    'source': 'Barchart (TLS)'
                }
    except Exception as e: 
        print(f"  ⚠️ Method 2 error: {e}")
    return None

# ============ METHOD 3: Anti-Bot Headers ============
def method_3_antibot(symbol="RMF26"):
    print(f"  [Method 3] Trying Anti-Bot Headers for {symbol}...")
    
    ua_string = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    if HAS_FAKE_UA:
        try:
            ua = UserAgent() 
            ua_string = ua.random
        except: pass

    url = f"https://www.barchart.com/futures/quotes/{symbol}"
    headers = {'User-Agent': ua_string}
    
    try:
        response = standard_requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            price = extract_price_from_html(response.text)
            if price:
                open_price, prev_close = extract_details_from_html(response.text)
                if open_price and abs(open_price - price) < 0.01: open_price = None
                return {
                    'price': price, 'change': 0, 'high': price, 'low': price,
                    'open': open_price, 'previous_close': prev_close,
                    'source': 'Barchart (Headers)'
                }
    except: pass
    return None

# ============ MASTER FUNCTION ============
def get_barchart_contract(symbol):
    print(f"\n🌊 Fetching {symbol} from Barchart...")
    res = method_1_api(symbol)
    if res: return res
    res = method_2_curl_cffi(symbol)
    if res: return res
    res = method_3_antibot(symbol)
    if res: return res
    print(f"❌ All methods failed for {symbol}")
    return None

def get_barchart_robusta_jan26():
    return get_barchart_contract("RMF26")

def get_barchart_arabica_last2():
    print("\n🌊 Fetching Arabica Coffee 4/5 Last 2 Contracts from Barchart...")
    contracts_to_fetch = [
        {'symbol': 'XFZ25', 'contract': 'Z25', 'name': 'Dec \'25'},
        {'symbol': 'XFH26', 'contract': 'H26', 'name': 'Mar \'26'}
    ]
    results = []
    for contract_info in contracts_to_fetch:
        symbol = contract_info['symbol']
        print(f"  📊 Fetching {contract_info['name']} ({symbol})...")
        data = get_barchart_contract(symbol)
        if data:
            data['symbol'] = symbol
            data['contract'] = contract_info['contract']
            results.append(data)
            print(f"    ✅ Got {contract_info['name']}: ${data['price']:.2f}")
        else:
            print(f"    ❌ Failed to fetch {contract_info['name']}")
    return results if len(results) == 2 else None
