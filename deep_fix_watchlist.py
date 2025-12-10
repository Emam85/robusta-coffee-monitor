"""
Deep Fix - Manually rebuild the WATCHLIST section
This handles any malformed structure
"""

with open('monitor.py', 'r') as f:
    lines = f.readlines()

print("=" * 70)
print("🔍 DEEP FIX - Analyzing monitor.py line by line")
print("=" * 70)

# Find the WATCHLIST section
watchlist_start = None
watchlist_end = None

for i, line in enumerate(lines):
    if 'WATCHLIST = {' in line:
        watchlist_start = i
        print(f"\n📍 Found WATCHLIST start at line {i+1}")
    
    # Look for the end of WATCHLIST (a line with just } or },)
    if watchlist_start is not None and watchlist_end is None:
        if line.strip() in ['}', '},']:
            watchlist_end = i
            print(f"📍 Found WATCHLIST end at line {i+1}")
            break

if watchlist_start is None:
    print("❌ ERROR: Could not find WATCHLIST in monitor.py")
    exit(1)

# Show the problematic section
print(f"\n🔍 Current WATCHLIST section (lines {watchlist_start+1}-{watchlist_end+1}):")
print("─" * 70)
for i in range(watchlist_start, min(watchlist_end + 5, len(lines))):
    print(f"{i+1:3d}: {lines[i]}", end='')
print("─" * 70)

# Build the corrected WATCHLIST
correct_watchlist_lines = [
    "WATCHLIST = {\n",
    "    'RC=F': {'name': 'Robusta Coffee', 'type': 'Softs'},\n",
    "    'KC=F': {'name': 'Arabica Coffee', 'type': 'Softs'},\n",
    "    'SB=F': {'name': 'Sugar No.11', 'type': 'Softs'},\n",
    "    'CC=F': {'name': 'Cocoa', 'type': 'Softs'},\n",
    "    'ZW=F': {'name': 'Wheat', 'type': 'Grains'},\n",
    "    'ZL=F': {'name': 'Soybean Oil', 'type': 'Oils'},\n",
    "    'PO=F': {'name': 'Palm Oil', 'type': 'Oils'}\n",
    "}\n"
]

# Find where the next section starts (skip any duplicate entries)
next_section_start = watchlist_end + 1
for i in range(watchlist_end + 1, len(lines)):
    # Look for the next major section (starts with # or a variable assignment at column 0)
    if lines[i].startswith('#') or (lines[i][0].isalpha() and '=' in lines[i] and not lines[i].startswith(' ')):
        next_section_start = i
        print(f"📍 Next section starts at line {i+1}: {lines[i].strip()[:50]}")
        break

# Rebuild the file
new_lines = (
    lines[:watchlist_start] +           # Everything before WATCHLIST
    correct_watchlist_lines +            # Corrected WATCHLIST
    ["\n"] +                             # Blank line
    lines[next_section_start:]           # Everything after WATCHLIST
)

# Write the fixed file
with open('monitor.py', 'w') as f:
    f.writelines(new_lines)

print("\n" + "=" * 70)
print("✅ WATCHLIST SECTION REBUILT")
print("=" * 70)

print("\n📋 Applied changes:")
print(f"   • Removed lines {watchlist_start+1} to {next_section_start}")
print(f"   • Inserted clean WATCHLIST (9 lines)")
print(f"   • Total commodities: 7")

print("\n🧪 Testing syntax...")
import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'monitor.py'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("   ✅ Syntax is VALID! No errors found.")
else:
    print("   ❌ Syntax error still exists:")
    print(result.stderr)
    exit(1)

print("\n🎯 WATCHLIST now contains:")
print("   1. RC=F → Robusta Coffee (Softs)")
print("   2. KC=F → Arabica Coffee (Softs)")
print("   3. SB=F → Sugar No.11 (Softs)")
print("   4. CC=F → Cocoa (Softs)")
print("   5. ZW=F → Wheat (Grains)")
print("   6. ZL=F → Soybean Oil (Oils)")
print("   7. PO=F → Palm Oil (Oils)")

print("\n🚀 Ready to deploy!")
print("=" * 70)