"""
Multi-Layer Barchart Scraper with Cloudflare Bypass
Version: DIAMOND+ (Robusta + Arabica Support)
Supports: Robusta (RMF26), Arabica (Last 2 Contracts)
ENHANCED: Better opening price extraction
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

# Import UserAgent but DO NOT initialize it yet (Lazy Loading to prevent crash)
try:
    from fake_useragent import UserAgent
    HAS_FAKE_UA = True
except:
    HAS_FAKE_UA = False

# ============ HELPER: ROBUST PARSER ============
def extract_price_from_html(html):
    """Try 4 different ways to find the price in Barchart HTML"""
    price = None
    
    # Strategy 1: JSON "lastPrice" (Common in script tags)
    if not price:
        matches = re.findall(r'"lastPrice":"?([\d,.]+)"?', html)
        if matches: return float(matches[0].replace(',', ''))

    # Strategy 2: Data Attribute (Common in table rows)
    if not price:
        matches = re.findall(r'data-last-price="([\d,.]+)"', html)
        if matches: return float(matches[0].replace(',', ''))

    # Strategy 3: Specific Script Variable (var bcQuoteApp)
    if not price and 'var bcQuoteApp' in html:
        try:
            start = html.find('var bcQuoteApp')
            end = html.find('};', start) + 1
            snippet = html[start:end]
            matches = re.findall(r'"lastPrice":\s*([\d,.]+)', snippet)
            if matches: return float(matches[0].replace(',', ''))
        except: pass

    # Strategy 4: Span Class (Visual price)
    if not price:
        matches = re.findall(r'<span[^>]*class="[^"]*last-change[^"]*"[^>]*>([\d,.]+)</span>', html)
        if matches: return float(matches[0].replace(',', ''))
        
    return None


def extract_open_from_html(html):
    """Extract opening price from Barchart HTML - ENHANCED VERSION"""
    try:
        # Method 1: Look for "open" in JSON data (most reliable)
        match = re.search(r'"open":"?([\d,.]+)"?', html)
        if match:
            open_val = float(match.group(1).replace(',', ''))
            print(f"    [Open Parser] Method 1 (JSON): ${open_val:.2f}")
            return open_val
        
        # Method 2: Look in table data attributes
        match = re.search(r'data-open="([\d,.]+)"', html)
        if match:
            open_val = float(match.group(1).replace(',', ''))
            print(f"    [Open Parser] Method 2 (Data Attr): ${open_val:.2f}")
            return open_val
        
        # Method 3: Find in bcQuoteApp variable
        if 'var bcQuoteApp' in html:
            start = html.find('var bcQuoteApp')
            end = html.find('};', start) + 1
            snippet = html[start:end]
            match = re.search(r'"open":\s*([\d,.]+)', snippet)
            if match:
                open_val = float(match.group(1).replace(',', ''))
                print(f"    [Open Parser] Method 3 (bcQuoteApp): ${open_val:.2f}")
                return open_val
        
        # Method 4: Look for "Open" label in the quote summary section
        match = re.search(r'<dt[^>]*>Open[^<]*</dt>\s*<dd[^>]*>([\d,.]+)</dd>', html, re.IGNORECASE)
        if match:
            open_val = float(match.group(1).replace(',', ''))
            print(f"    [Open Parser] Method 4 (Label): ${open_val:.2f}")
            return open_val
        
        # Method 5: Look in the price summary table
        match = re.search(r'<tr[^>]*>\s*<td[^>]*>Open[^<]*</td>\s*<td[^>]*>([\d,.]+)</td>', html, re.IGNORECASE)
        if match:
            open_val = float(match.group(1).replace(',', ''))
            print(f"    [Open Parser] Method 5 (Table): ${open_val:.2f}")
            return open_val
            
        print("    [Open Parser] All methods failed - no opening price found")
    except Exception as e:
        print(f"    [Open Parser] Error: {e}")
    return None

# ============ METHOD 1: Official Hidden API ============
def method_1_api(symbol="RMF26"):
    print(f"  [Method 1] Trying Official API for {symbol}...")
    url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"
    params = {'fields': 'lastPrice,priceChange,high,low,open', 'list': symbol}
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
                
                # Return None for open if it's 0 or same as price
                if open_price == 0 or open_price == price:
                    open_price = None
                    
                return {
                    'price': price,
                    'change': float(str(quote.get('priceChange', 0)).replace(',', '')),
                    'high': float(str(quote.get('high', 0)).replace(',', '')),
                    'low': float(str(quote.get('low', 0)).replace(',', '')),
                    'open': open_price,
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
                # Try to extract opening price from HTML
                open_price = extract_open_from_html(response.text)
                
                # Return None for open if it's same as current price
                if open_price and abs(open_price - price) < 0.01:
                    open_price = None
                    
                return {
                    'price': price, 
                    'change': 0,
                    'high': price,
                    'low': price,
                    'open': open_price,
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
                # Try to extract opening price from HTML
                open_price = extract_open_from_html(response.text)
                
                # Return None for open if it's same as current price
                if open_price and abs(open_price - price) < 0.01:
                    open_price = None
                    
                return {
                    'price': price,
                    'change': 0,
                    'high': price,
                    'low': price,
                    'open': open_price,
                    'source': 'Barchart (Headers)'
                }
    except: pass
    return None

# ============ MASTER FUNCTION FOR SINGLE CONTRACT ============
def get_barchart_contract(symbol):
    """Get data for a single Barchart contract (Robusta or Arabica)"""
    print(f"\n🌊 Fetching {symbol} from Barchart...")
    
    # Try methods in order
    res = method_1_api(symbol)
    if res: return res
    
    res = method_2_curl_cffi(symbol)
    if res: return res
    
    res = method_3_antibot(symbol)
    if res: return res

    print(f"❌ All methods failed for {symbol}")
    return None

# ============ ROBUSTA COFFEE (Current Contract) ============
def get_barchart_robusta_jan26():
    """Get Robusta Coffee current contract (Jan '26)"""
    return get_barchart_contract("RMF26")

# ============ ARABICA COFFEE (Last 2 Contracts) ============
def get_barchart_arabica_last2():
    """
    Get Arabica Coffee 4/5 last 2 active contracts from Barchart
    Uses XF symbols (Arabica Coffee 4/5) not KC (standard Arabica)
    Fetches: Dec '25 (XFZ25) and Mar '26 (XFH26)
    Returns: List of 2 contract dictionaries with price, change, high, low
    """
    print("\n🌊 Fetching Arabica Coffee 4/5 Last 2 Contracts from Barchart...")
    
    # Define the exact contracts we want (XF = Arabica Coffee 4/5)
    contracts_to_fetch = [
        {'symbol': 'XFZ25', 'contract': 'Z25', 'name': 'Dec \'25'},
        {'symbol': 'XFH26', 'contract': 'H26', 'name': 'Mar \'26'}
    ]
    
    results = []
    
    for contract_info in contracts_to_fetch:
        symbol = contract_info['symbol']
        print(f"  📊 Fetching {contract_info['name']} ({symbol})...")
        
        # Fetch the contract data
        data = get_barchart_contract(symbol)
        if data:
            data['symbol'] = symbol
            data['contract'] = contract_info['contract']
            results.append(data)
            print(f"    ✅ Got {contract_info['name']}: ${data['price']:.2f}")
        else:
            print(f"    ❌ Failed to fetch {contract_info['name']}")
    
    return results if len(results) == 2 else None

# ============ TESTING ============
if __name__ == "__main__":
    print("🧪 Testing Barchart Scraper\n")
    
    # Test Robusta
    robusta = get_barchart_robusta_jan26()
    if robusta:
        print(f"✅ Robusta: ${robusta['price']:.2f} | Open: ${robusta.get('open', 'N/A')}")
    
    # Test Arabica
    arabica_contracts = get_barchart_arabica_last2()
    if arabica_contracts:
        print(f"\n✅ Arabica Contract 1 ({arabica_contracts[0]['symbol']}): ${arabica_contracts[0]['price']:.2f} | Open: ${arabica_contracts[0].get('open', 'N/A')}")
        print(f"✅ Arabica Contract 2 ({arabica_contracts[1]['symbol']}): ${arabica_contracts[1]['price']:.2f} | Open: ${arabica_contracts[1].get('open', 'N/A')}")
    else:
        print("\n❌ Could not fetch Arabica contracts")