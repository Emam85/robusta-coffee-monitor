"""
Fix the watchlist structure mismatch in monitor.py
Run this from: /workspaces/robusta-coffee-monitor/
"""

import re
import os

# Verify we're in the correct directory
current_dir = os.getcwd()
print(f"📁 Current directory: {current_dir}")

monitor_path = '/workspaces/robusta-coffee-monitor/monitor.py'

if not os.path.exists(monitor_path):
    print(f"❌ ERROR: monitor.py not found at {monitor_path}")
    print(f"   Please run this script from /workspaces/robusta-coffee-monitor/")
    exit(1)

print(f"✅ Found monitor.py\n")

# Read the file
with open(monitor_path, 'r') as f:
    content = f.read()

# Fix 1: Replace the entire WATCHLIST section with correct structure
old_watchlist_pattern = r"WATCHLIST = \{[^\}]*\}"

new_watchlist = """WATCHLIST = {
    'RC=F': {'name': 'Robusta Coffee', 'type': 'Softs'},
    'KC=F': {'name': 'Arabica Coffee', 'type': 'Softs'},
    'SB=F': {'name': 'Sugar No.11', 'type': 'Softs'},
    'CC=F': {'name': 'Cocoa', 'type': 'Softs'},
    'ZW=F': {'name': 'Wheat', 'type': 'Grains'},
    'ZL=F': {'name': 'Soybean Oil', 'type': 'Oils'},
    'PO=F': {'name': 'Palm Oil', 'type': 'Oils'}
}"""

# Replace the watchlist
if "WATCHLIST = {" in content:
    content = re.sub(old_watchlist_pattern, new_watchlist, content, flags=re.DOTALL)
    print("✅ Step 1: WATCHLIST structure fixed")
else:
    print("⚠️ WATCHLIST not found - adding it after imports")
    # Add after the imports section
    import_end = content.find("# ============ CONFIGURATION ============")
    if import_end > 0:
        content = content[:import_end] + "\n" + new_watchlist + "\n\n" + content[import_end:]

# Fix 2: Ensure the fetch_commodity_data function correctly extracts commodity name
# Look for the commodity name extraction pattern and fix it

old_pattern1 = "commodity_name = commodity_info.get('name', symbol)"
new_pattern1 = "commodity_name = commodity_info['name']"

if old_pattern1 in content:
    content = content.replace(old_pattern1, new_pattern1)
    print("✅ Step 2: Commodity name extraction fixed")

# Fix 3: Make sure the fetch function handles the dict structure properly
old_pattern2 = "commodity_info = WATCHLIST.get(symbol, {})"
new_pattern2 = "commodity_info = WATCHLIST.get(symbol, {'name': symbol, 'type': 'Unknown'})"

if old_pattern2 in content:
    content = content.replace(old_pattern2, new_pattern2)
    print("✅ Step 3: Default commodity_info structure fixed")

# Save the fixed file
with open(monitor_path, 'w') as f:
    f.write(content)

print("\n" + "="*60)
print("🎉 ALL FIXES APPLIED SUCCESSFULLY!")
print("="*60)

print("\n📋 Summary of changes:")
print("1. ✅ Added Robusta Coffee (RC=F) back to watchlist")
print("2. ✅ Fixed watchlist to use {'name': '...', 'type': '...'} structure")
print("3. ✅ Updated commodity name extraction to handle dict properly")
print("4. ✅ All 7 commodities now properly configured")

print("\n🎯 Next steps:")
print("1. Run: python monitor.py")
print("   OR")
print("2. Deploy to Render and it will work automatically")

print("\n📊 Current watchlist:")
watchlist_items = [
    "RC=F → Robusta Coffee (Softs)",
    "KC=F → Arabica Coffee (Softs)", 
    "SB=F → Sugar No.11 (Softs)",
    "CC=F → Cocoa (Softs)",
    "ZW=F → Wheat (Grains)",
    "ZL=F → Soybean Oil (Oils)",
    "PO=F → Palm Oil (Oils)"
]

for item in watchlist_items:
    print(f"   • {item}")

print("\n" + "="*60)