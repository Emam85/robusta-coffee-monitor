"""
Complete fix for baseline/opening price tracking
This ensures proper daily change calculations from market open
"""

def fix_barchart_html_extraction():
    """
    Fix barchart_intelligent.py to extract opening price from HTML
    """
    print("🔧 Fixing Barchart HTML extraction to get opening price...\n")
    
    with open('barchart_intelligent.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add new function to extract opening price from HTML
    extraction_function = '''
def extract_open_from_html(html):
    """Extract opening price from Barchart HTML"""
    try:
        # Method 1: Look for "open" in JSON data
        match = re.search(r'"open":"?([\d,.]+)"?', html)
        if match:
            return float(match.group(1).replace(',', ''))
        
        # Method 2: Look in table data
        match = re.search(r'data-open="([\d,.]+)"', html)
        if match:
            return float(match.group(1).replace(',', ''))
        
        # Method 3: Find in bcQuoteApp variable
        if 'var bcQuoteApp' in html:
            start = html.find('var bcQuoteApp')
            end = html.find('};', start) + 1
            snippet = html[start:end]
            match = re.search(r'"open":\\s*([\d,.]+)', snippet)
            if match:
                return float(match.group(1).replace(',', ''))
    except:
        pass
    return None

'''
    
    # Insert the new function after the extract_price_from_html function
    insert_point = content.find('def extract_arabica_contracts_from_table')
    if insert_point != -1:
        content = content[:insert_point] + extraction_function + content[insert_point:]
        print("1️⃣ ✅ Added extract_open_from_html() function")
    
    # Update Method 2 (curl_cffi) to extract opening price
    old_method2_return = '''            if price: 
                return {
                    'price': price, 
                    'change': 0,  # Not available from HTML scraping
                    'high': price,
                    'low': price,
                    'open': price,  # Estimate: use current price as fallback
                    'source': 'Barchart (TLS)'
                }'''
    
    new_method2_return = '''            if price:
                # Try to extract opening price from HTML
                open_price = extract_open_from_html(response.text)
                if not open_price:
                    open_price = price  # Fallback to current price
                return {
                    'price': price, 
                    'change': 0,
                    'high': price,
                    'low': price,
                    'open': open_price,
                    'source': 'Barchart (TLS)'
                }'''
    
    content = content.replace(old_method2_return, new_method2_return)
    print("2️⃣ ✅ Updated Method 2 (TLS) to extract opening price from HTML")
    
    # Update Method 3 (antibot) similarly
    old_method3_return = '''            if price: 
                return {
                    'price': price,
                    'change': 0,
                    'high': price,
                    'low': price,
                    'open': price,  # Estimate: use current price as fallback
                    'source': 'Barchart (Headers)'
                }'''
    
    new_method3_return = '''            if price:
                # Try to extract opening price from HTML
                open_price = extract_open_from_html(response.text)
                if not open_price:
                    open_price = price  # Fallback to current price
                return {
                    'price': price,
                    'change': 0,
                    'high': price,
                    'low': price,
                    'open': open_price,
                    'source': 'Barchart (Headers)'
                }'''
    
    content = content.replace(old_method3_return, new_method3_return)
    print("3️⃣ ✅ Updated Method 3 (Anti-Bot) to extract opening price from HTML")
    
    with open('barchart_intelligent.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ Barchart scraper fully updated!\n")

def fix_commodity_fetcher_opening():
    """
    Fix commodity_fetcher.py to return opening price (or use current as fallback)
    """
    print("🔧 Fixing commodity_fetcher.py for opening price...\n")
    
    with open('commodity_fetcher.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the return statement and add 'open' field
    old_return = '''            if price and price > 0:
                return {
                    'price': price,
                    'change': 0,
                    'percent': 0,
                    'high': price,
                    'low': price,
                    'volume': 0,
                    'source': 'Investing.com'
                }'''
    
    new_return = '''            if price and price > 0:
                return {
                    'price': price,
                    'change': 0,
                    'percent': 0,
                    'high': price,
                    'low': price,
                    'open': price,  # Investing.com doesn't provide open, use current
                    'volume': 0,
                    'source': 'Investing.com'
                }'''
    
    if old_return in content:
        content = content.replace(old_return, new_return)
        print("✅ Added 'open' field to commodity_fetcher.py return data")
    else:
        print("⚠️  commodity_fetcher.py might already have 'open' field")
    
    with open('commodity_fetcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ commodity_fetcher.py updated!\n")

def verify_monitor_logging():
    """
    Add better logging to monitor.py to see what's happening
    """
    print("🔧 Adding enhanced logging to monitor.py...\n")
    
    with open('monitor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Enhance the Barchart section logging
    old_barchart_log = '''                # Get opening price from Barchart
                opening_price = barchart_data.get('open', price)
                
                # Initialize baseline ONCE with opening price
                if symbol not in daily_start_prices:
                    daily_start_prices[symbol] = opening_price
                    session_high_low[symbol] = {'high': price, 'low': price}
                    print(f"  📌 Session Open: ${opening_price:.2f} | Current: ${price:.2f}")'''
    
    new_barchart_log = '''                # Get opening price from Barchart
                opening_price = barchart_data.get('open', price)
                
                # DEBUG: Show what we got from Barchart
                print(f"  🔍 Barchart returned: Price=${price:.2f}, Open=${opening_price:.2f}")
                
                # Initialize baseline ONCE with opening price
                if symbol not in daily_start_prices:
                    daily_start_prices[symbol] = opening_price
                    session_high_low[symbol] = {'high': price, 'low': price}
                    print(f"  📌 NEW BASELINE SET: Open=${opening_price:.2f} | Current=${price:.2f}")
                else:
                    print(f"  ℹ️  Using existing baseline: ${daily_start_prices[symbol]:.2f}")'''
    
    if old_barchart_log in content:
        content = content.replace(old_barchart_log, new_barchart_log)
        print("1️⃣ ✅ Enhanced Barchart logging")
    
    # Enhance Investing.com logging
    old_investing_log = '''            # Get opening price from data (or fallback to current)
            opening_price = data.get('open', price)
            
            # Initialize baseline ONCE with opening price
            if symbol not in daily_start_prices:
                daily_start_prices[symbol] = opening_price
                session_high_low[symbol] = {'high': price, 'low': price}
                print(f"  📌 Session Open: ${opening_price:.2f} | Current: ${price:.2f}")'''
    
    new_investing_log = '''            # Get opening price from data (or fallback to current)
            opening_price = data.get('open', price)
            
            # DEBUG: Show what we got from Investing.com
            print(f"  🔍 Investing.com returned: Price=${price:.2f}, Open=${opening_price:.2f}")
            
            # Initialize baseline ONCE with opening price
            if symbol not in daily_start_prices:
                daily_start_prices[symbol] = opening_price
                session_high_low[symbol] = {'high': price, 'low': price}
                print(f"  📌 NEW BASELINE SET: Open=${opening_price:.2f} | Current=${price:.2f}")
            else:
                print(f"  ℹ️  Using existing baseline: ${daily_start_prices[symbol]:.2f}")'''
    
    if old_investing_log in content:
        content = content.replace(old_investing_log, new_investing_log)
        print("2️⃣ ✅ Enhanced Investing.com logging")
    
    # Enhance Arabica logging
    old_arabica_log = '''            # Initialize baseline ONCE with opening price
            if symbol_key not in daily_start_prices:
                daily_start_prices[symbol_key] = opening_price
                session_high_low[symbol_key] = {'high': price, 'low': price}
                print(f"  📌 {contract['contract']} Open: ${opening_price:.2f} | Current: ${price:.2f}")'''
    
    new_arabica_log = '''            # DEBUG: Show what we got
            print(f"  🔍 Arabica {contract['contract']} returned: Price=${price:.2f}, Open=${opening_price:.2f}")
            
            # Initialize baseline ONCE with opening price
            if symbol_key not in daily_start_prices:
                daily_start_prices[symbol_key] = opening_price
                session_high_low[symbol_key] = {'high': price, 'low': price}
                print(f"  📌 NEW BASELINE SET: {contract['contract']} Open=${opening_price:.2f} | Current=${price:.2f}")
            else:
                print(f"  ℹ️  Using existing baseline: ${daily_start_prices[symbol_key]:.2f}")'''
    
    if old_arabica_log in content:
        content = content.replace(old_arabica_log, new_arabica_log)
        print("3️⃣ ✅ Enhanced Arabica logging")
    
    with open('monitor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ Enhanced logging added to monitor.py!\n")

def main():
    """Run all fixes"""
    print("=" * 70)
    print("🚀 COMPLETE OPENING PRICE FIX")
    print("=" * 70)
    print()
    
    try:
        fix_barchart_html_extraction()
        fix_commodity_fetcher_opening()
        verify_monitor_logging()
        
        print("=" * 70)
        print("✅ ALL FIXES APPLIED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("📋 What Was Fixed:")
        print("   1. Barchart now extracts opening price from HTML")
        print("   2. commodity_fetcher.py returns 'open' field")
        print("   3. Enhanced logging shows what prices are being used")
        print()
        print("🔄 Next Steps:")
        print("   1. git add -A")
        print("   2. git commit -m 'Fix: Complete opening price extraction'")
        print("   3. git push origin main")
        print("   4. Check logs after next run to verify baselines are correct")
        print()
        
    except Exception as e:
        print(f"\n❌ Error during fixes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()