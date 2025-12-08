"""Multi-source commodity data fetcher"""
import requests
import random
from datetime import datetime

def fetch_from_investing_com(commodity_name):
    """Scrape from Investing.com"""
    try:
        urls = {
            'Coffee Arabica': 'https://www.investing.com/commodities/us-coffee-c',
            'Robusta Coffee': 'https://www.investing.com/commodities/london-coffee',
            'Cocoa': 'https://www.investing.com/commodities/us-cocoa',
            'Sugar': 'https://www.investing.com/commodities/us-sugar-no11',
            'Cotton': 'https://www.investing.com/commodities/us-cotton-no.2',
            'Wheat': 'https://www.investing.com/commodities/us-wheat',
            'Gold': 'https://www.investing.com/commodities/gold'
        }
        
        url = urls.get(commodity_name)
        if not url:
            return None
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Simple extraction logic
        if 'data-test="instrument-price-last"' in response.text:
            start = response.text.find('data-test="instrument-price-last"')
            snippet = response.text[start:start+200]
            price_start = snippet.find('>') + 1
            price_end = snippet.find('<', price_start)
            price_str = snippet[price_start:price_end].replace(',', '').strip()
            
            try:
                price = float(price_str)
                return {
                    'price': price,
                    'change': 0,
                    'change_percent': 0,
                    'source': 'Investing.com'
                }
            except:
                pass
    except Exception as e:
        print(f"Investing.com error for {commodity_name}: {e}")
    return None

def fetch_commodity_data(symbol, name):
    """Fetch with fallback"""
    print(f"  Fetching {name} ({symbol})...")
    
    # Clean name for URL lookup
    search_name = name.replace(' (ICE)', '').replace(' (CBOT)', '').replace(' (COMEX)', '')
    
    data = fetch_from_investing_com(search_name)
    if data:
        print(f"  ✅ Got data from {data['source']}")
        return {**data, 'symbol': symbol, 'name': name}
    
    print(f"  ⚠️ Data fetch failed for {name}")
    return None
