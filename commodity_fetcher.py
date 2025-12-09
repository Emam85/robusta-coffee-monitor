"""
Multi-source commodity data fetcher
Primary: Investing.com (stable, reliable)
Used as fallback when Barchart fails
"""
import requests
import re
from datetime import datetime

def fetch_from_investing_com(commodity_name):
    """
    Scrape commodity price from Investing.com
    This is the stable fallback source
    """
    try:
        # Map commodity names to Investing.com URLs
        urls = {
            'Robusta Coffee': 'https://www.investing.com/commodities/london-coffee',
            'Arabica Coffee': 'https://www.investing.com/commodities/us-coffee-c',
            'Sugar No.11': 'https://www.investing.com/commodities/us-sugar-no11',
            'Cocoa': 'https://www.investing.com/commodities/us-cocoa',
            'Wheat': 'https://www.investing.com/commodities/us-wheat',
            'Soybean Oil': 'https://www.investing.com/commodities/us-soybean-oil',
            'Palm Oil': 'https://www.investing.com/commodities/palm-oil',
            'Coffee Arabica': 'https://www.investing.com/commodities/us-coffee-c',
            'Sugar': 'https://www.investing.com/commodities/us-sugar-no11'
        }
        
        url = urls.get(commodity_name)
        if not url:
            print(f"  ❌ No URL mapping for {commodity_name}")
            return None
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            html = response.text
            price = None
            
            # Method 1: data-test attribute (primary)
            if 'data-test="instrument-price-last"' in html:
                start = html.find('data-test="instrument-price-last"')
                snippet = html[start:start+300]
                
                # Extract the price from the snippet
                match = re.search(r'>([0-9,]+\.?[0-9]*)<', snippet)
                if match:
                    price_str = match.group(1).replace(',', '').strip()
                    try:
                        price = float(price_str)
                    except:
                        pass
            
            # Method 2: Alternative parsing
            if not price:
                matches = re.findall(r'data-test="instrument-price-last"[^>]*>([0-9,]+\.?[0-9]*)', html)
                if matches:
                    try:
                        price = float(matches[0].replace(',', ''))
                    except:
                        pass
            
            if price and price > 0:
                return {
                    'price': price,
                    'change': 0,
                    'percent': 0,
                    'high': price,
                    'low': price,
                    'volume': 0,
                    'source': 'Investing.com'
                }
        
        print(f"  ❌ Failed to parse {commodity_name} from Investing.com")
    except Exception as e:
        print(f"  ❌ Investing.com error for {commodity_name}: {str(e)[:100]}")
    
    return None

def fetch_commodity_data(symbol, name):
    """
    Main fetcher function
    Called by monitor.py for all non-Robusta commodities
    """
    # Extract clean name (remove exchange suffix)
    search_name = name.split(' (')[0] if '(' in name else name
    
    print(f"  🔍 Fetching {search_name} from Investing.com...")
    data = fetch_from_investing_com(search_name)
    
    if data:
        # Add symbol and full name to result
        data['symbol'] = symbol
        data['name'] = name
        data['timestamp'] = datetime.now().isoformat()
        print(f"  ✅ Got {search_name}: ${data['price']}")
        return data
    
    print(f"  ❌ Failed to fetch {search_name}")
    return None

# ============ TEST FUNCTION ============
if __name__ == "__main__":
    print("🧪 Testing Investing.com Fetcher...\n")
    
    test_commodities = [
        ('KC=F', 'Coffee Arabica (ICE)'),
        ('CC=F', 'Cocoa (ICE)'),
        ('SB=F', 'Sugar (ICE)')
    ]
    
    for symbol, name in test_commodities:
        print(f"\nTesting {name}...")
        result = fetch_commodity_data(symbol, name)
        if result:
            print(f"✅ SUCCESS: ${result['price']}")
        else:
            print(f"❌ FAILED")