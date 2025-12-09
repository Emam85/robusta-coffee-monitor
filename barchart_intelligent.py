"""
Multi-Layer Barchart Scraper with Cloudflare Bypass
Tries 3 methods in waterfall sequence until success
"""
import json
import time
import random
import re
import requests as standard_requests

# Try to import smart libraries
try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    print("⚠️ curl_cffi not available")

try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    HAS_FAKE_UA = True
except:
    HAS_FAKE_UA = False
    print("⚠️ fake-useragent not available")

# ============ METHOD 1: Official Hidden API (Cleanest) ============
def method_1_api(symbol="RMF26"):
    """
    Barchart's internal API endpoint
    This is what their website calls via AJAX
    """
    print(f"  [Method 1] Trying Official API...")
    
    url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"
    params = {
        'fields': 'symbol,lastPrice,priceChange,percentChange,highPrice,lowPrice,tradeTime,volume',
        'list': symbol
    }
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': f'https://www.barchart.com/futures/quotes/{symbol}',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://www.barchart.com'
    }
    
    try:
        response = standard_requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                quote = data['data'][0]
                price_raw = quote.get('lastPrice', 0)
                
                # Handle both string and number formats
                if isinstance(price_raw, str):
                    price = float(price_raw.replace(',', ''))
                else:
                    price = float(price_raw)
                
                if price > 0:
                    print(f"  ✅ Method 1 SUCCESS: ${price}")
                    return {
                        'price': price,
                        'change': float(quote.get('priceChange', 0)),
                        'percent': float(quote.get('percentChange', 0)),
                        'high': float(quote.get('highPrice', price)),
                        'low': float(quote.get('lowPrice', price)),
                        'volume': int(quote.get('volume', 0)),
                        'source': 'Barchart API'
                    }
        
        print(f"  ❌ Method 1 failed: Status {response.status_code}")
    except Exception as e:
        print(f"  ❌ Method 1 error: {str(e)[:100]}")
    
    return None

# ============ METHOD 2: TLS Impersonation (curl_cffi) ============
def method_2_curl_cffi(symbol="RMF26"):
    """
    Uses curl_cffi to impersonate Chrome 120
    Bypasses Cloudflare TLS fingerprinting
    """
    if not HAS_CURL_CFFI:
        print(f"  [Method 2] Skipped (curl_cffi not installed)")
        return None
    
    print(f"  [Method 2] Trying TLS Impersonation (Chrome 120)...")
    
    url = f"https://www.barchart.com/futures/quotes/{symbol}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none'
    }
    
    try:
        # Impersonate Chrome 120
        response = cf_requests.get(
            url, 
            headers=headers,
            impersonate="chrome120",
            timeout=15
        )
        
        if response.status_code == 200:
            html = response.text
            price = None
            
            # Parsing Strategy 1: Find in JSON data
            if '"lastPrice":' in html:
                matches = re.findall(r'"lastPrice":"?([\d,.]+)"?', html)
                if matches:
                    try:
                        price = float(matches[0].replace(',', ''))
                    except:
                        pass
            
            # Parsing Strategy 2: Find in data attributes
            if not price and 'data-last-price=' in html:
                matches = re.findall(r'data-last-price="([\d,.]+)"', html)
                if matches:
                    try:
                        price = float(matches[0].replace(',', ''))
                    except:
                        pass
            
            # Parsing Strategy 3: Find in script tag
            if not price and 'var bcQuoteApp' in html:
                start = html.find('var bcQuoteApp')
                end = html.find('};', start) + 1
                try:
                    snippet = html[start:end]
                    matches = re.findall(r'"lastPrice":\s*([\d,.]+)', snippet)
                    if matches:
                        price = float(matches[0].replace(',', ''))
                except:
                    pass
            
            if price and price > 0:
                print(f"  ✅ Method 2 SUCCESS: ${price}")
                return {
                    'price': price,
                    'change': 0,
                    'percent': 0,
                    'high': price,
                    'low': price,
                    'volume': 0,
                    'source': 'Barchart (TLS Impersonation)'
                }
        
        print(f"  ❌ Method 2 failed: Status {response.status_code}")
    except Exception as e:
        print(f"  ❌ Method 2 error: {str(e)[:100]}")
    
    return None

# ============ METHOD 3: Anti-Bot Headers (Safety Net) ============
def method_3_antibot(symbol="RMF26"):
    """
    Traditional anti-bot techniques
    Rotating user agents + realistic delays + retry logic
    """
    print(f"  [Method 3] Trying Anti-Bot Headers...")
    
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
    ]
    
    if HAS_FAKE_UA:
        try:
            user_agents.append(ua.random)
        except:
            pass
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://www.google.com/'
    }
    
    # Realistic human delay
    time.sleep(random.uniform(0.5, 1.5))
    
    url = f"https://www.barchart.com/futures/quotes/{symbol}"
    
    try:
        session = standard_requests.Session()
        
        # Retry logic (up to 2 attempts)
        for attempt in range(2):
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                html = response.text
                price = None
                
                # Multiple parsing strategies
                # Strategy 1: data-last-price attribute
                matches = re.findall(r'data-last-price="([\d,.]+)"', html)
                if matches:
                    try:
                        price = float(matches[0].replace(',', ''))
                    except:
                        pass
                
                # Strategy 2: JSON in script tag
                if not price and '"lastPrice":' in html:
                    matches = re.findall(r'"lastPrice":"?([\d,.]+)"?', html)
                    if matches:
                        try:
                            price = float(matches[0].replace(',', ''))
                        except:
                            pass
                
                # Strategy 3: Price in span/div elements
                if not price:
                    matches = re.findall(r'<span[^>]*class="[^"]*last-change[^"]*"[^>]*>([\d,.]+)</span>', html)
                    if matches:
                        try:
                            price = float(matches[0].replace(',', ''))
                        except:
                            pass
                
                if price and price > 0:
                    print(f"  ✅ Method 3 SUCCESS: ${price}")
                    return {
                        'price': price,
                        'change': 0,
                        'percent': 0,
                        'high': price,
                        'low': price,
                        'volume': 0,
                        'source': 'Barchart (Anti-Bot Headers)'
                    }
            
            if attempt < 1:
                print(f"  ⚠️ Attempt {attempt + 1} failed, retrying...")
                time.sleep(random.uniform(1, 2))
        
        print(f"  ❌ Method 3 failed after {attempt + 1} attempts")
    except Exception as e:
        print(f"  ❌ Method 3 error: {str(e)[:100]}")
    
    return None

# ============ MASTER FUNCTION: Waterfall Logic ============
def get_barchart_robusta_jan26():
    """
    Intelligent waterfall scraper
    Tries methods in order: API → TLS → Headers
    Returns first successful result
    """
    print("\n🌊 Starting Waterfall Scraper for Barchart (Jan '26 Robusta)")
    print("=" * 65)
    
    symbol = "RMF26"  # January 2026 Robusta Coffee
    
    # Try each method in priority order
    methods = [
        ("Official API", method_1_api),
        ("TLS Impersonation", method_2_curl_cffi),
        ("Anti-Bot Headers", method_3_antibot)
    ]
    
    for name, method_func in methods:
        try:
            result = method_func(symbol)
            if result and result.get('price', 0) > 0:
                print(f"\n✅ SUCCESS via {name}!")
                print(f"   💰 Price: ${result['price']:,.2f}")
                print(f"   📊 Source: {result['source']}")
                print("=" * 65 + "\n")
                return result
        except Exception as e:
            print(f"  ⚠️ {name} crashed: {str(e)[:100]}")
            continue
    
    print("\n❌ ALL METHODS FAILED - Will use Investing.com fallback")
    print("=" * 65 + "\n")
    return None

# ============ TEST FUNCTION ============
if __name__ == "__main__":
    print("🧪 Testing Barchart Intelligent Scraper...\n")
    data = get_barchart_robusta_jan26()
    
    if data:
        print(f"\n🎯 FINAL RESULT:")
        print(f"   Price: ${data['price']:,.2f}")
        print(f"   Source: {data['source']}")
        print(f"   Change: {data.get('change', 0):+.2f} ({data.get('percent', 0):+.2f}%)")
    else:
        print("\n❌ TEST FAILED - All methods blocked")