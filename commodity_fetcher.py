"""Multi-source commodity data fetcher"""
import requests
import random
from datetime import datetime

def fetch_from_investing_com(commodity_name):
    """Scrape from Investing.com"""
    try:
        urls = {
            'Robusta Coffee': 'https://www.investing.com/commodities/london-coffee',
            'Coffee Arabica': 'https://www.investing.com/commodities/us-coffee-c',
            'Cocoa': 'https://www.investing.com/commodities/us-cocoa',
            'Sugar': 'https://www.investing.com/commodities/us-sugar-no11',
            'Wheat': 'https://www.investing.com/commodities/us-wheat',
            'Soybean Oil': 'https://www.investing.com/commodities/us-soybean-oil',
            'Palm Oil': 'https://www.investing.com/commodities/palm-oil'
        }
        
        url = urls.get(commodity_name)
        if not url: return None
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if 'data-test="instrument-price-last"' in response.text:
            start = response.text.find('data-test="instrument-price-last"')
            snippet = response.text[start:start+200]
            price_str = snippet.split('>')[1].split('<')[0].replace(',', '').strip()
            return {'price': float(price_str), 'source': 'Investing.com'}
            
    except Exception as e:
        print(f"Fetch Error ({commodity_name}): {e}")
    return None

def fetch_commodity_data(symbol, name):
    search_name = name.split(' (')[0] # Remove (ICE) etc
    data = fetch_from_investing_com(search_name)
    if data: return {**data, 'symbol': symbol, 'name': name}
    return None
