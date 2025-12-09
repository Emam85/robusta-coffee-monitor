"""
Multi-Layer Barchart Scraper with Cloudflare Bypass
Version: DIAMOND+ (Robusta + Arabica Support)
Supports: Robusta (RMF26), Arabica (Last 2 Contracts)
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

def extract_multiple_contracts_from_html(html):
    """Extract data for multiple contracts from Barchart quotes page"""
    contracts = []
    
    # Look for table rows with contract data
    # Pattern: <tr data-symbol="KCF26" ...> ... </tr>
    row_pattern = r'<tr[^>]*data-symbol="([^"]+)"[^>]*>(.*?)</tr>'
    rows = re.findall(row_pattern, html, re.DOTALL)
    
    for symbol, row_content in rows:
        try:
            # Extract contract month/year from symbol (e.g., KCF26 -> Mar '26)
            contract_code = symbol[-3:]  # Last 3 chars (e.g., F26)
            
            # Extract price
            price_match = re.search(r'data-last-price="([\d,.]+)"', row_content)
            if not price_match:
                price_match = re.search(r'<td[^>]*>\s*([\d,.]+)\s*</td>', row_content)
            
            if price_match:
                price = float(price_match.group(1).replace(',', ''))
                
                # Extract change
                change_match = re.search(r'data-change="([+-]?[\d,.]+)"', row_content)
                change = float(change_match.group(1).replace(',', '')) if change_match else 0
                
                # Extract high/low if available
                high_match = re.search(r'data-high="([\d,.]+)"', row_content)
                low_match = re.search(r'data-low="([\d,.]+)"', row_content)
                high = float(high_match.group(1).replace(',', '')) if high_match else price
                low = float(low_match.group(1).replace(',', '')) if low_match else price
                
                contracts.append({
                    'symbol': symbol,
                    'contract': contract_code,
                    'price': price,
                    'change': change,
                    'high': high,
                    'low': low
                })
        except Exception as e:
            continue
    
    return contracts

# ============ METHOD 1: Official Hidden API ============
def method_1_api(symbol="RMF26"):
    print(f"  [Method 1] Trying Official API for {symbol}...")
    url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"
    params = {'fields': 'lastPrice,priceChange,high,low', 'list': symbol}
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
                return {
                    'price': float(str(quote.get('lastPrice', 0)).replace(',', '')),
                    'change': float(str(quote.get('priceChange', 0)).replace(',', '')),
                    'high': float(str(quote.get('high', 0)).replace(',', '')),
                    'low': float(str(quote.get('low', 0)).replace(',', '')),
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
                return {
                    'price': price, 
                    'change': 0,  # Not available from HTML scraping
                    'high': price,
                    'low': price,
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
                return {
                    'price': price,
                    'change': 0,
                    'high': price,
                    'low': price,
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
    Get Arabica Coffee last 2 active contracts from Barchart
    Returns: List of 2 contract dictionaries with price, change, high, low
    """
    print("\n🌊 Fetching Arabica Last 2 Contracts from Barchart...")
    
    # Get the quotes overview page which lists all contracts
    url = "https://www.barchart.com/futures/quotes/KC*0/futures-prices"
    
    # Try curl_cffi first for best results
    if HAS_CURL_CFFI:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            response = cf_requests.get(url, headers=headers, impersonate="chrome120", timeout=10)
            
            if response.status_code == 200:
                contracts = extract_multiple_contracts_from_html(response.text)
                if len(contracts) >= 2:
                    # Return first 2 contracts (most recent)
                    return [
                        {
                            'symbol': contracts[0]['symbol'],
                            'contract': contracts[0]['contract'],
                            'price': contracts[0]['price'],
                            'change': contracts[0]['change'],
                            'high': contracts[0]['high'],
                            'low': contracts[0]['low'],
                            'source': 'Barchart (TLS)'
                        },
                        {
                            'symbol': contracts[1]['symbol'],
                            'contract': contracts[1]['contract'],
                            'price': contracts[1]['price'],
                            'change': contracts[1]['change'],
                            'high': contracts[1]['high'],
                            'low': contracts[1]['low'],
                            'source': 'Barchart (TLS)'
                        }
                    ]
        except Exception as e:
            print(f"  ⚠️ TLS method failed: {e}")
    
    # Fallback: Get known front month contracts manually
    # Coffee months: H (Mar), K (May), N (Jul), U (Sep), Z (Dec)
    current_month = datetime.now().month
    current_year = datetime.now().year % 100  # Last 2 digits
    
    # Determine likely front 2 contracts
    month_codes = ['H', 'K', 'N', 'U', 'Z']  # Mar, May, Jul, Sep, Dec
    month_nums = [3, 5, 7, 9, 12]
    
    contracts_to_try = []
    for i, month_num in enumerate(month_nums):
        year_offset = 0 if month_num >= current_month else 1
        symbol = f"KC{month_codes[i]}{current_year + year_offset}"
        contracts_to_try.append(symbol)
    
    # Try to get the first 2 available contracts
    results = []
    for symbol in contracts_to_try[:3]:  # Try first 3 to ensure we get 2
        data = get_barchart_contract(symbol)
        if data:
            data['symbol'] = symbol
            data['contract'] = symbol[-3:]
            results.append(data)
            if len(results) == 2:
                break
    
    return results if len(results) == 2 else None

# ============ TESTING ============
if __name__ == "__main__":
    print("🧪 Testing Barchart Scraper\n")
    
    # Test Robusta
    robusta = get_barchart_robusta_jan26()
    if robusta:
        print(f"✅ Robusta: ${robusta['price']:.2f}")
    
    # Test Arabica
    arabica_contracts = get_barchart_arabica_last2()
    if arabica_contracts:
        print(f"✅ Arabica Contract 1 ({arabica_contracts[0]['contract']}): ${arabica_contracts[0]['price']:.2f}")
        print(f"✅ Arabica Contract 2 ({arabica_contracts[1]['contract']}): ${arabica_contracts[1]['price']:.2f}")