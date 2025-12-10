# fix_commodity_fetcher.py

def fix_investing_fetcher():
    """
    Fix commodity_fetcher.py to return opening price
    Note: You'll need to check if your commodity_fetcher.py actually fetches 'open'
    This is a template - adjust based on your actual file structure
    """
    
    try:
        with open('commodity_fetcher.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        print("⚠️  Please manually check commodity_fetcher.py")
        print("   Make sure it returns an 'open' field in the data dictionary")
        print("   Example: data['open'] = <opening_price_from_investing>")
        print("\n   If Investing.com doesn't provide opening price,")
        print("   use current price as fallback: data['open'] = data['price']")
        
        # Check if file already has 'open' handling
        if "'open'" in content or '"open"' in content:
            print("\n✅ commodity_fetcher.py seems to already handle 'open' field")
        else:
            print("\n⚠️  commodity_fetcher.py may need manual update")
            print("   Add this line where you build the return dictionary:")
            print("   'open': data.get('open', current_price),  # Fallback to current")
        
    except FileNotFoundError:
        print("⚠️  commodity_fetcher.py not found - skipping")

if __name__ == '__main__':
    fix_investing_fetcher()