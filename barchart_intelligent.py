"""
Multi-Layer Barchart Scraper with Cloudflare Bypass
Tries 4 methods in sequence until one succeeds
"""

import json
import time
import random
from datetime import datetime

# Method 1: Standard requests (for API endpoint)
import requests as standard_requests

# Method 2: curl_cffi (TLS impersonation)
try:
    from curl_cffi import requests as cf_requests
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    print("⚠️ curl_cffi not available, will use fallback methods")

# Method 3: Fake user agents
try:
    from fake_useragent import UserAgent
    ua = UserAgent()
    HAS_FAKE_UA = True
except:
    HAS_FAKE_UA = False


# ============ METHOD 1: Official API Endpoint ============
def method_1_api(symbol="RMF26"):
    """
    Barchart's internal API - cleanest method
    This is what their website calls via AJAX
    """
    print(f"  [Method 1] Trying Official API...")
    
    url = f"https://www.barchart.com/proxies/core-api/v1/quotes/get"
    params = {
        'fields': 'symbol,lastPrice,priceChange,percentChange,highPrice,lowPrice,tradeTime,volume',
        'list': symbol,
        'meta': 'field.shortName,field.type,field.description'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': f'https://www.barchart.com/futures/quotes/{symbol}',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        response = standard_requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Parse the response
            if 'data' in data and len(data['data']) > 0:
                quote = data['data'][0]
                price = float(str(quote.get('lastPrice', 0)).replace(',', ''))
                
                if price > 0:
                    print(f"  ✅ Method 1 SUCCESS: ${price}")
                    return {
                        'price': price,
                        'change': quote.get('priceChange', 0),
                        'percent': quote.get('percentChange', 0),
                        'high': quote.get('highPrice', price),
                        'low': quote.get('lowPrice', price),
                        'volume': quote.get('volume', 0),
                        'source': 'Barchart API'
                    }
        
        print(f"  ❌ Method 1 failed: Status {response.status_code}")
        
    except Exception as e:
        print(f"  ❌ Method 1 error: {e}")
    
    return None


# ============ METHOD 2: curl_cffi (TLS Impersonation) ============
def method_2_curl_cffi(symbol="RMF26"):
    """
    Uses curl_cffi to impersonate real Chrome browser
    Bypasses Cloudflare TLS fingerprinting
    """
    if not HAS_CURL_CFFI:
        return None
    
    print(f"  [Method 2] Trying TLS Impersonation...")
    
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
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    try:
        # Impersonate Chrome 120 (latest)
        response = cf_requests.get(
            url, 
            headers=headers, 
            impersonate="chrome120",
            timeout=15
        )
        
        if response.status_code == 200:
            html = response.text
            
            # Try multiple extraction methods
            price = None
            
            # Method 2a: Find price in script tag
            if '"lastPrice":' in html:
                start = html.find('"lastPrice":') + 12
                end = html.find(',', start)
                try:
                    price = float(html[start:end].strip().replace('"', ''))
                except:
                    pass
            
            # Method 2b: Find in meta tags
            if not price and 'data-last-price=' in html:
                start = html.find('data-last-price="') + 17
                end = html.find('"', start)
                try:
                    price = float(html[start:end].replace(',', ''))
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
        print(f"  ❌ Method 2 error: {e}")
    
    return None


# ============ METHOD 3: Rotating Headers + Delays ============
def method_3_anti_bot(symbol="RMF26"):
    """
    Traditional anti-bot techniques
    Rotating user agents + realistic delays
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
        user_agents.append(ua.random)
    
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
    
    # Add random delay to seem human
    time.sleep(random.uniform(1.0, 2.5))
    
    url = f"https://www.barchart.com/futures/quotes/{symbol}"
    
    try:
        session = standard_requests.Session()
        
        # Retry logic
        for attempt in range(3):
            response = session.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                html = response.text
                
                # Multiple parsing strategies
                price = None
                
                # Strategy 1: JSON in script
                if 'var bcQuoteApp' in html:
                    start = html.find('var bcQuoteApp') + 15
                    end = html.find('};', start) + 1
                    try:
                        data_str = html[start:end]
                        data = json.loads(data_str)
                        price = float(data.get('lastPrice', 0))
                    except:
                        pass
                
                # Strategy 2: Data attributes
                if not price and 'data-ng-bind="quote.lastPrice"' in html:
                    start = html.find('data-ng-bind="quote.lastPrice"')
                    snippet = html[start-200:start+200]
                    # Extract number
                    import re
                    matches = re.findall(r'\d+\.\d+', snippet)
                    if matches:
                        try:
                            price = float(matches[0])
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
                        'source': 'Barchart (Anti-Bot)'
                    }
            
            if attempt < 2:
                time.sleep(random.uniform(2, 4))
        
        print(f"  ❌ Method 3 failed after 3 attempts")
        
    except Exception as e:
        print(f"  ❌ Method 3 error: {e}")
    
    return None


# ============ MASTER FUNCTION: Waterfall Logic ============
def get_barchart_robusta_jan26():
    """
    Intelligent scraper that tries all methods in sequence
    Returns data from first successful method
    """
    print("\n🧠 Starting Intelligent Barchart Scraper (Jan '26 Robusta)")
    print("=" * 60)
    
    symbol = "RMF26"  # January 2026 Robusta Coffee
    
    # Try each method in order
    methods = [
        ("Official API", method_1_api),
        ("TLS Impersonation", method_2_curl_cffi),
        ("Anti-Bot Headers", method_3_anti_bot)
    ]
    
    for name, method in methods:
        try:
            result = method(symbol)
            if result:
                print(f"\n✅ SUCCESS via {name}!")
                print(f"   Price: ${result['price']}")
                print(f"   Source: {result['source']}")
                print("=" * 60)
                return result
        except Exception as e:
            print(f"  ⚠️ {name} crashed: {e}")
            continue
    
    print("\n❌ ALL METHODS FAILED")
    print("=" * 60)
    return None


# ============ TEST ============
if __name__ == "__main__":
    data = get_barchart_robusta_jan26()
    if data:
        print(f"\n🎯 Final Result: ${data['price']} from {data['source']}")
    else:
        print("\n❌ Could not fetch Barchart data")
