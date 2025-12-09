"""
Integrate Barchart scraper into existing system
"""

with open('monitor.py', 'r') as f:
    content = f.read()

# Add import at top
if 'from barchart_intelligent import' not in content:
    content = content.replace(
        'from flask import Flask, jsonify',
        'from flask import Flask, jsonify\nfrom barchart_intelligent import get_barchart_robusta_jan26'
    )

# Update fetch_commodity_data function
old_fetch = 'def fetch_commodity_data(symbol):'
new_fetch = '''def fetch_commodity_data(symbol):
    """Fetch commodity data with Barchart priority for Robusta"""
    
    # SPECIAL HANDLING: Robusta Coffee - Use Barchart Jan '26 contract
    if symbol == 'RC=F':
        print(f"🎯 Fetching Robusta from Barchart (Jan '26 contract)...")
        barchart_data = get_barchart_robusta_jan26()
        
        if barchart_data:
            # Convert to standard format
            return {
                'symbol': symbol,
                'price': barchart_data['price'],
                'change': barchart_data.get('change', 0),
                'change_percent': barchart_data.get('percent', 0),
                'high': barchart_data.get('high', barchart_data['price']),
                'low': barchart_data.get('low', barchart_data['price']),
                'volume': barchart_data.get('volume', 0),
                'open': barchart_data['price'],
                'prev_close': barchart_data['price'] - barchart_data.get('change', 0),
                'timestamp': datetime.now().isoformat(),
                'name': 'Robusta Coffee Jan 26 (Barchart)',
                'history': [barchart_data['price']] * 20,
                'source': barchart_data['source']
            }
        else:
            print("⚠️ Barchart failed, falling back to Investing.com")
    
    # FALLBACK: Use existing commodity_fetcher for all others'''

content = content.replace(old_fetch, new_fetch)

with open('monitor.py', 'w') as f:
    f.write(content)

print("✅ Barchart integration complete!")
