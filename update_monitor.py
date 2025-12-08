# Update monitor.py to use the new commodity fetcher

with open('monitor.py', 'r') as f:
    content = f.read()

# Replace the fetch function
old_fetch = '''def fetch_commodity_data(symbol, period='5d'):
    """Fetch real-time commodity data from Yahoo Finance (FREE)"""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return None
        
        latest = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else latest
        
        current_price = float(latest['Close'])
        previous_price = float(previous['Close'])
        change = current_price - previous_price
        change_percent = (change / previous_price) * 100
        
        return {
            'symbol': symbol,
            'price': round(current_price, 2),
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'high': round(float(latest['High']), 2),
            'low': round(float(latest['Low']), 2),
            'volume': int(latest['Volume']),
            'open': round(float(latest['Open']), 2),
            'prev_close': round(previous_price, 2),
            'timestamp': datetime.now().isoformat(),
            'name': WATCHLIST.get(symbol, symbol),
            'history': hist['Close'].values.tolist()[-20:],  # Last 20 data points
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None'''

new_fetch = '''def fetch_commodity_data(symbol, period='5d'):
    """Fetch commodity data from multiple sources with fallback"""
    from commodity_fetcher import fetch_commodity_data as fetch_multi
    
    try:
        # Use multi-source fetcher
        data = fetch_multi(symbol, WATCHLIST.get(symbol, symbol))
        
        if data:
            # Ensure all required fields
            return {
                'symbol': data.get('symbol', symbol),
                'price': data.get('price', 0),
                'change': data.get('change', 0),
                'change_percent': data.get('change_percent', 0),
                'high': data.get('high', data.get('price', 0)),
                'low': data.get('low', data.get('price', 0)),
                'volume': data.get('volume', 0),
                'open': data.get('price', 0),
                'prev_close': data.get('price', 0) - data.get('change', 0),
                'timestamp': datetime.now().isoformat(),
                'name': WATCHLIST.get(symbol, symbol),
                'history': [data.get('price', 0)] * 20,
            }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    
    return None'''

content = content.replace(old_fetch, new_fetch)

# Remove yfinance import since we're not using it
content = content.replace('import yfinance as yf\n', '')

with open('monitor.py', 'w') as f:
    f.write(content)

print("✅ monitor.py updated to use multi-source data fetcher!")
