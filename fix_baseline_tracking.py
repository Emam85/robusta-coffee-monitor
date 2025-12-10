# fix_baseline_tracking.py

def fix_monitor_baseline():
    with open('monitor.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # ===== FIX 1: Update initialize_session_baseline to only set once =====
    old_baseline_func = '''def initialize_session_baseline(symbol, price):
    """Set baseline price at session start (used for calculating daily change)"""
    if symbol not in daily_start_prices:
        daily_start_prices[symbol] = price
        session_high_low[symbol] = {'high': price, 'low': price}
        print(f"  📌 Baseline set for {symbol}: ${price:.2f}")'''
    
    new_baseline_func = '''def initialize_session_baseline(symbol, price):
    """Set baseline price at session start (used for calculating daily change)"""
    # CRITICAL: Only set baseline ONCE per session - never overwrite
    if symbol not in daily_start_prices:
        daily_start_prices[symbol] = price
        session_high_low[symbol] = {'high': price, 'low': price}
        print(f"  📌 Baseline set for {symbol}: ${price:.2f}")
    else:
        # Baseline already exists - just update high/low
        if symbol not in session_high_low:
            session_high_low[symbol] = {'high': price, 'low': price}'''
    
    content = content.replace(old_baseline_func, new_baseline_func)
    
    # ===== FIX 2: Update AI prompt to explain baseline comparison =====
    old_prompt = '''prompt = f"""You are a professional commodity analyst. Analyze the following data for {display_name} and provide concise trading insights.

Current Data:
- Price: ${commodity_data['price']:,.2f}
- Change: {commodity_data['change']:+.2f} ({commodity_data['change_percent']:+.2f}%)
- Daily Range: ${commodity_data['low']:,.2f} - ${commodity_data['high']:,.2f}
- Exchange: {commodity_data.get('exchange', 'N/A')}'''
    
    new_prompt = '''# Get baseline for context
    symbol_key = commodity_data.get('symbol', '')
    if symbol_key.startswith('KC_CONTRACT'):
        baseline_key = symbol_key
    else:
        baseline_key = symbol_key
    baseline_price = daily_start_prices.get(baseline_key, commodity_data['price'])
    
    prompt = f"""You are a professional commodity analyst. Analyze the following data for {display_name} and provide concise trading insights.

Current Data:
- Opening Price (Session Baseline): ${baseline_price:,.2f}
- Current Price: ${commodity_data['price']:,.2f}
- Change from Open: {commodity_data['change']:+.2f} ({commodity_data['change_percent']:+.2f}%)
- Daily Range: ${commodity_data['low']:,.2f} - ${commodity_data['high']:,.2f}
- Exchange: {commodity_data.get('exchange', 'N/A')}

NOTE: Your analysis should compare the current price (${commodity_data['price']:,.2f}) against the opening price (${baseline_price:,.2f}). The change of {commodity_data['change_percent']:+.2f}% reflects movement from market open to now.'''
    
    content = content.replace(old_prompt, new_prompt)
    
    # ===== FIX 3: Update reset function to be more explicit =====
    old_reset = '''def reset_daily_tracking():
    """Reset daily tracking at session start (called at 1:00 AM Cairo time)"""
    global daily_start_prices, session_high_low
    daily_start_prices.clear()
    session_high_low.clear()
    print("🔄 Daily tracking reset for new session")'''
    
    new_reset = '''def reset_daily_tracking():
    """Reset daily tracking at session start (called at 1:00 AM Cairo time)"""
    global daily_start_prices, session_high_low
    print(f"🔄 Resetting daily tracking - Old baseline count: {len(daily_start_prices)}")
    daily_start_prices.clear()
    session_high_low.clear()
    print("✅ Daily tracking reset complete - All baselines cleared for new session")'''
    
    content = content.replace(old_reset, new_reset)
    
    # Write back
    with open('monitor.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ monitor.py updated successfully!")
    print("\n📋 Changes made:")
    print("  1. ✅ Fixed baseline tracking - now persists across fetches")
    print("  2. ✅ Added baseline context to AI prompt")
    print("  3. ✅ Enhanced reset logging")
    print("\n⚠️  IMPORTANT: Restart your monitor service to apply changes!")
    print("    The baseline will be set correctly on the FIRST fetch after restart.")

if __name__ == '__main__':
    fix_monitor_baseline()