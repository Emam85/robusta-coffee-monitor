# fix_barchart_opening.py

def fix_barchart_scraper():
    with open('barchart_intelligent.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix Method 1 API to include 'open' field
    old_method1 = """            if 'data' in data and len(data['data']) > 0:
                quote = data['data'][0]
                return {
                    'price': float(str(quote.get('lastPrice', 0)).replace(',', '')),
                    'change': float(str(quote.get('priceChange', 0)).replace(',', '')),
                    'high': float(str(quote.get('high', 0)).replace(',', '')),
                    'low': float(str(quote.get('low', 0)).replace(',', '')),
                    'source': 'Barchart API'
                }"""
    
    new_method1 = """            if 'data' in data and len(data['data']) > 0:
                quote = data['data'][0]
                return {
                    'price': float(str(quote.get('lastPrice', 0)).replace(',', '')),
                    'change': float(str(quote.get('priceChange', 0)).replace(',', '')),
                    'high': float(str(quote.get('high', 0)).replace(',', '')),
                    'low': float(str(quote.get('low', 0)).replace(',', '')),
                    'open': float(str(quote.get('open', 0)).replace(',', '')),
                    'source': 'Barchart API'
                }"""
    
    content = content.replace(old_method1, new_method1)
    
    # Fix Method 1 API params to request 'open' field
    old_params = """    params = {'fields': 'lastPrice,priceChange,high,low', 'list': symbol}"""
    new_params = """    params = {'fields': 'lastPrice,priceChange,high,low,open', 'list': symbol}"""
    
    content = content.replace(old_params, new_params)
    
    # Fix Method 2 (curl_cffi) to estimate open from price-change
    old_method2_return = """            if price: 
                return {
                    'price': price, 
                    'change': 0,  # Not available from HTML scraping
                    'high': price,
                    'low': price,
                    'source': 'Barchart (TLS)'
                }"""
    
    new_method2_return = """            if price: 
                return {
                    'price': price, 
                    'change': 0,  # Not available from HTML scraping
                    'high': price,
                    'low': price,
                    'open': price,  # Estimate: use current price as fallback
                    'source': 'Barchart (TLS)'
                }"""
    
    content = content.replace(old_method2_return, new_method2_return)
    
    # Fix Method 3 (antibot) similarly
    old_method3_return = """            if price: 
                return {
                    'price': price,
                    'change': 0,
                    'high': price,
                    'low': price,
                    'source': 'Barchart (Headers)'
                }"""
    
    new_method3_return = """            if price: 
                return {
                    'price': price,
                    'change': 0,
                    'high': price,
                    'low': price,
                    'open': price,  # Estimate: use current price as fallback
                    'source': 'Barchart (Headers)'
                }"""
    
    content = content.replace(old_method3_return, new_method3_return)
    
    with open('barchart_intelligent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ barchart_intelligent.py updated!")
    print("   • Added 'open' field to API request")
    print("   • Returns opening price from Barchart data")

if __name__ == '__main__':
    fix_barchart_scraper()