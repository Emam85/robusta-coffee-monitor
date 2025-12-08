"""
Multi-source commodity data fetcher
Uses free APIs when Yahoo Finance fails
"""

import requests
import json
from datetime import datetime
import random

def fetch_from_twelvedata(symbol):
    """Twelve Data API - 800 calls/day FREE"""
    try:
        # Map our symbols to Twelve Data format
        symbol_map = {
            'KC=F': 'KC',
            'CC=F': 'CC', 
            'SB=F': 'SB',
            'CT=F': 'CT',
            'ZW=F': 'ZW',
            'GC=F': 'GC'
        }
        
        td_symbol = symbol_map.get(symbol, symbol.replace('=F', ''))
        
        url = f"https://api.twelvedata.com/price"
        params = {
            'symbol': td_symbol,
            'apikey': 'demo'  # Free demo key
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if 'price' in data:
            price = float(data['price'])
            return {
                'price': price,
                'change': 0,  # Will calculate from history
                'change_percent': 0,
                'source': 'TwelveData'
            }
    except Exception as e:
        print(f"TwelveData error for {symbol}: {e}")
    return None

def fetch_from_investing_com(commodity_name):
    """Scrape from Investing.com"""
    try:
        urls = {
            'Coffee': 'https://www.investing.com/commodities/us-coffee-c',
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Simple extraction from page content
        if 'data-test="instrument-price-last"' in response.text:
            start = response.text.find('data-test="instrument-price-last"')
            snippet = response.text[start:start+200]
            
            # Extract price
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

def generate_realistic_data(symbol, base_prices):
    """Generate realistic simulated data for testing"""
    base = base_prices.get(symbol, 100)
    
    # Add realistic volatility
    volatility = base * 0.02  # 2% daily volatility
    change = random.uniform(-volatility, volatility)
    price = base + change
    change_percent = (change / base) * 100
    
    return {
        'price': round(price, 2),
        'change': round(change, 2),
        'change_percent': round(change_percent, 2),
        'high': round(price + random.uniform(0, volatility/2), 2),
        'low': round(price - random.uniform(0, volatility/2), 2),
        'volume': random.randint(10000, 50000),
        'source': 'Simulated (Demo Mode)'
    }

def fetch_commodity_data(symbol, name):
    """
    Fetch commodity data from multiple sources
    Falls back to simulation if all fail
    """
    
    # Base prices for simulation fallback
    base_prices = {
        'KC=F': 325,    # Coffee Arabica ~325 cents/lb
        'CC=F': 8500,   # Cocoa ~8500 USD/MT
        'SB=F': 19,     # Sugar ~19 cents/lb
        'CT=F': 72,     # Cotton ~72 cents/lb
        'ZW=F': 550,    # Wheat ~550 cents/bu
        'GC=F': 2650,   # Gold ~2650 USD/oz
    }
    
    commodity_names = {
        'KC=F': 'Coffee',
        'CC=F': 'Cocoa',
        'SB=F': 'Sugar',
        'CT=F': 'Cotton',
        'ZW=F': 'Wheat',
        'GC=F': 'Gold'
    }
    
    print(f"  Fetching {name} ({symbol})...")
    
    # Try TwelveData first
    data = fetch_from_twelvedata(symbol)
    if data:
        print(f"  ✅ Got data from {data['source']}")
        return {**data, 'symbol': symbol, 'name': name}
    
    # Try Investing.com
    commodity_name = commodity_names.get(symbol)
    if commodity_name:
        data = fetch_from_investing_com(commodity_name)
        if data:
            print(f"  ✅ Got data from {data['source']}")
            return {**data, 'symbol': symbol, 'name': name}
    
    # Fallback to realistic simulation
    print(f"  ⚠️ Using simulated data for testing")
    data = generate_realistic_data(symbol, base_prices)
    return {**data, 'symbol': symbol, 'name': name, 'timestamp': datetime.now().isoformat()}

# Test the fetcher
if __name__ == '__main__':
    print("Testing commodity data fetcher...\n")
    
    watchlist = {
        'KC=F': 'Coffee Arabica (ICE)',
        'CC=F': 'Cocoa (ICE)',
        'SB=F': 'Sugar (ICE)',
        'CT=F': 'Cotton (ICE)',
        'ZW=F': 'Wheat (CBOT)',
        'GC=F': 'Gold (COMEX)',
    }
    
    for symbol, name in watchlist.items():
        data = fetch_commodity_data(symbol, name)
        print(f"\n{name}: ${data['price']:.2f} ({data['change_percent']:+.2f}%)")
        print(f"Source: {data['source']}")
