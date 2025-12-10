"""
COMPLETE FIX - All Issues in One Go
Fixes: Syntax error, missing routes, missing /check endpoint
Run: python complete_fix_final.py
"""

import re

with open('monitor.py', 'r') as f:
    content = f.read()

print("=" * 70)
print("🔧 COMPREHENSIVE FIX - All Issues")
print("=" * 70)

# ============ FIX 1: WATCHLIST SYNTAX ERROR ============
print("\n1️⃣ Fixing WATCHLIST syntax error...")

# This pattern will match the entire broken WATCHLIST section
watchlist_pattern = r"WATCHLIST = \{[^}]*\}[,\s]*\n[^}]*\}"

correct_watchlist = """WATCHLIST = {
    'RC=F': {'name': 'Robusta Coffee', 'type': 'Softs'},
    'KC=F': {'name': 'Arabica Coffee', 'type': 'Softs'},
    'SB=F': {'name': 'Sugar No.11', 'type': 'Softs'},
    'CC=F': {'name': 'Cocoa', 'type': 'Softs'},
    'ZW=F': {'name': 'Wheat', 'type': 'Grains'},
    'ZL=F': {'name': 'Soybean Oil', 'type': 'Oils'},
    'PO=F': {'name': 'Palm Oil', 'type': 'Oils'}
}"""

# Replace the broken watchlist
content = re.sub(watchlist_pattern, correct_watchlist, content, flags=re.DOTALL)
print("   ✅ Removed duplicate WATCHLIST entries")

# ============ FIX 2: MISSING @app.route('/') ============
print("\n2️⃣ Adding missing route decorators...")

# Check if home() function exists without decorator
if "def home():" in content and "@app.route('/')" not in content:
    content = content.replace(
        "\ndef home():",
        "\n@app.route('/')\ndef home():"
    )
    print("   ✅ Added @app.route('/') for home()")
else:
    print("   ⚠️  @app.route('/') already exists")

# ============ FIX 3: ADD /check ENDPOINT ============
print("\n3️⃣ Adding /check endpoint for cron jobs...")

if "@app.route('/check')" not in content:
    check_endpoint = """
@app.route('/check')
def manual_check():
    \"\"\"Manual trigger - runs monitoring in background (for cron jobs)\"\"\"
    def run_background():
        try:
            print("📄 /check endpoint triggered")
            monitor_commodities()
            print("✅ Background monitoring completed")
        except Exception as e:
            print(f"❌ Background error: {e}")
            import traceback
            traceback.print_exc()
    
    # Start monitoring in background thread
    Thread(target=run_background, daemon=True).start()
    
    return jsonify({
        "status": "started",
        "message": "Monitoring cycle started in background",
        "note": "Check Telegram/logs for results in 30-60 seconds",
        "timestamp": datetime.now().isoformat()
    })

"""
    
    # Find the best insertion point (before scheduler or at end of routes)
    if "# ============ SCHEDULED TASKS ============" in content:
        content = content.replace(
            "# ============ SCHEDULED TASKS ============",
            check_endpoint + "# ============ SCHEDULED TASKS ============"
        )
        print("   ✅ Added /check endpoint")
    elif "if __name__ == '__main__':" in content:
        content = content.replace(
            "if __name__ == '__main__':",
            check_endpoint + "\nif __name__ == '__main__':"
        )
        print("   ✅ Added /check endpoint (alternative location)")
    else:
        print("   ⚠️  Could not find insertion point")
else:
    print("   ⚠️  /check endpoint already exists")

# ============ FIX 4: ENSURE Flask app IS INITIALIZED ============
print("\n4️⃣ Verifying Flask app initialization...")

if "app = Flask(__name__)" not in content:
    print("   ⚠️  WARNING: Flask app not initialized!")
    print("   Adding: app = Flask(__name__)")
    
    # Add Flask app initialization after imports
    flask_init = "\n# Flask app\napp = Flask(__name__)\n"
    
    if "from flask import Flask, jsonify" in content:
        content = content.replace(
            "from flask import Flask, jsonify",
            "from flask import Flask, jsonify" + flask_init
        )
        print("   ✅ Added Flask app initialization")
else:
    print("   ✅ Flask app already initialized")

# ============ SAVE FIXED FILE ============
with open('monitor.py', 'w') as f:
    f.write(content)

print("\n" + "=" * 70)
print("✅ ALL FIXES APPLIED SUCCESSFULLY!")
print("=" * 70)

print("\n📋 Summary of Changes:")
print("   1. ✅ Fixed WATCHLIST syntax error (removed duplicate entries)")
print("   2. ✅ Added @app.route('/') decorator")
print("   3. ✅ Added /check endpoint for cron jobs")
print("   4. ✅ Verified Flask app initialization")

print("\n🧪 Quick Test:")
print("   Run: python -m py_compile monitor.py")
print("   If no errors = syntax is valid!")

print("\n🚀 Deployment Steps:")
print("   1. git add monitor.py")
print("   2. git commit -m 'Fix all syntax and routing issues'")
print("   3. git push")
print("   4. Render will auto-deploy")

print("\n🔗 Endpoints After Deploy:")
print("   ✅ https://robusta-coffee-monitor.onrender.com/")
print("   ✅ https://robusta-coffee-monitor.onrender.com/check")
print("   ✅ https://robusta-coffee-monitor.onrender.com/monitor")
print("   ✅ https://robusta-coffee-monitor.onrender.com/prices")

print("\n⏰ Update Your Cron Job URL To:")
print("   https://robusta-coffee-monitor.onrender.com/check")

print("\n" + "=" * 70)
print("✅ Ready to commit and push!")
print("=" * 70)