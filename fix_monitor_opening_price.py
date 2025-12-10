# fix_monitor_opening_price.py

def fix_monitor_baseline():
    with open('monitor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("🔧 Fixing monitor.py to use real opening prices...\n")
    
    # ===== FIX 1: Barchart Section (Robusta) =====
    old_barchart = """                # Initialize baseline if needed
                initialize_session_baseline(symbol, price)
                update_session_high_low(symbol, price)
                
                # Calculate accurate daily change
                baseline = daily_start_prices.get(symbol, price)
                daily_change = price - baseline
                daily_change_pct = (daily_change / baseline * 100) if baseline else 0
                
                # Use session high/low
                high = session_high_low[symbol]['high']
                low = session_high_low[symbol]['low']
                
                print(f"✅ Using Barchart data: ${price:.2f} (Change: {daily_change_pct:+.2f}%)")
                print("=" * 60 + "\\n")
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'change': daily_change,
                    'change_percent': daily_change_pct,
                    'high': high,
                    'low': low,"""
    
    new_barchart = """                # Get opening price from Barchart
                opening_price = barchart_data.get('open', price)
                
                # Initialize baseline ONCE with opening price
                if symbol not in daily_start_prices:
                    daily_start_prices[symbol] = opening_price
                    session_high_low[symbol] = {'high': price, 'low': price}
                    print(f"  📌 Session Open: ${opening_price:.2f} | Current: ${price:.2f}")
                
                # Calculate change from REAL opening price
                baseline = daily_start_prices[symbol]
                daily_change = price - baseline
                daily_change_pct = (daily_change / baseline * 100) if baseline else 0
                
                # Update session high/low
                update_session_high_low(symbol, price)
                high = session_high_low[symbol]['high']
                low = session_high_low[symbol]['low']
                
                print(f"✅ Using Barchart data: ${price:.2f} (Change: {daily_change_pct:+.2f}%)")
                print("=" * 60 + "\\n")
                
                return {
                    'symbol': symbol,
                    'price': price,
                    'change': daily_change,
                    'change_percent': daily_change_pct,
                    'high': high,
                    'low': low,
                    'open': opening_price,"""
    
    content = content.replace(old_barchart, new_barchart)
    print("1️⃣ ✅ Fixed Barchart section (Robusta)")
    
    # ===== FIX 2: Investing.com Section =====
    old_investing = """            price = data.get('price', 0)
            
            # Initialize baseline if needed
            initialize_session_baseline(symbol, price)
            update_session_high_low(symbol, price)
            
            # Calculate accurate daily change
            baseline = daily_start_prices.get(symbol, price)
            daily_change = price - baseline
            daily_change_pct = (daily_change / baseline * 100) if baseline else 0
            
            # Use session high/low
            high = session_high_low[symbol]['high']
            low = session_high_low[symbol]['low']"""
    
    new_investing = """            price = data.get('price', 0)
            
            # Get opening price from data (or fallback to current)
            opening_price = data.get('open', price)
            
            # Initialize baseline ONCE with opening price
            if symbol not in daily_start_prices:
                daily_start_prices[symbol] = opening_price
                session_high_low[symbol] = {'high': price, 'low': price}
                print(f"  📌 Session Open: ${opening_price:.2f} | Current: ${price:.2f}")
            
            # Calculate change from REAL opening price
            baseline = daily_start_prices[symbol]
            daily_change = price - baseline
            daily_change_pct = (daily_change / baseline * 100) if baseline else 0
            
            # Update session high/low
            update_session_high_low(symbol, price)
            high = session_high_low[symbol]['high']
            low = session_high_low[symbol]['low']"""
    
    content = content.replace(old_investing, new_investing)
    print("2️⃣ ✅ Fixed Investing.com section")
    
    # ===== FIX 3: Add 'open' to Investing.com return dict =====
    old_investing_return = """            return {
                'symbol': symbol,
                'price': price,
                'change': daily_change,
                'change_percent': daily_change_pct,
                'high': high,
                'low': low,
                'volume': data.get('volume', 0),"""
    
    new_investing_return = """            return {
                'symbol': symbol,
                'price': price,
                'change': daily_change,
                'change_percent': daily_change_pct,
                'high': high,
                'low': low,
                'open': opening_price,
                'volume': data.get('volume', 0),"""
    
    content = content.replace(old_investing_return, new_investing_return)
    print("3️⃣ ✅ Added 'open' field to return data")
    
    # ===== FIX 4: Update Arabica contracts handling =====
    old_arabica = """            symbol_key = f'KC_CONTRACT_{i+1}'
            price = contract['price']
            
            # Initialize baseline
            initialize_session_baseline(symbol_key, price)
            update_session_high_low(symbol_key, price)
            
            # Calculate accurate daily change
            baseline = daily_start_prices.get(symbol_key, price)
            daily_change = price - baseline
            daily_change_pct = (daily_change / baseline * 100) if baseline else 0
            
            # Use session high/low
            high = session_high_low[symbol_key]['high']
            low = session_high_low[symbol_key]['low']"""
    
    new_arabica = """            symbol_key = f'KC_CONTRACT_{i+1}'
            price = contract['price']
            opening_price = contract.get('open', price)
            
            # Initialize baseline ONCE with opening price
            if symbol_key not in daily_start_prices:
                daily_start_prices[symbol_key] = opening_price
                session_high_low[symbol_key] = {'high': price, 'low': price}
                print(f"  📌 {contract['contract']} Open: ${opening_price:.2f} | Current: ${price:.2f}")
            
            # Calculate change from REAL opening price
            baseline = daily_start_prices[symbol_key]
            daily_change = price - baseline
            daily_change_pct = (daily_change / baseline * 100) if baseline else 0
            
            # Update session high/low
            update_session_high_low(symbol_key, price)
            high = session_high_low[symbol_key]['high']
            low = session_high_low[symbol_key]['low']"""
    
    content = content.replace(old_arabica, new_arabica)
    print("4️⃣ ✅ Fixed Arabica contracts handling")
    
    with open('monitor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n✅ monitor.py updated successfully!")
    print("\n📋 What Changed:")
    print("   • Baseline = Opening Price (from data source)")
    print("   • Daily Change = Current - Opening")
    print("   • Baseline set ONCE per session (never resets)")
    print("   • Added 'open' field to all return dictionaries")

if __name__ == '__main__':
    fix_monitor_baseline()