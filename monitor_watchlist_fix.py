import re

with open('monitor.py', 'r') as f:
    content = f.read()

# Replace WATCHLIST section
old_watchlist = r"WATCHLIST = \{[^}]+\}"
new_watchlist = """WATCHLIST = {
    'KC=F': 'Coffee Arabica (ICE)',
    'CC=F': 'Cocoa (ICE)',
    'SB=F': 'Sugar (ICE)',
    'CT=F': 'Cotton (ICE)',
    'ZW=F': 'Wheat (CBOT)',
    'GC=F': 'Gold (COMEX)',
}"""

content = re.sub(old_watchlist, new_watchlist, content)

with open('monitor.py', 'w') as f:
    f.write(content)

print("✅ Watchlist updated!")
