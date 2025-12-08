import re

with open('monitor.py', 'r') as f:
    content = f.read()

# Remove threading import if exists
content = content.replace('from threading import Thread\n', '')

# Create simple synchronous /check endpoint
new_check = '''@app.route('/check')
def manual_check():
    """Manual trigger - synchronous monitoring"""
    try:
        print("🔄 Manual /check endpoint called")
        result = monitor_all_commodities()
        return jsonify({
            "status": "success",
            "message": "Monitoring completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500'''

# Replace existing /check endpoint
pattern = r'@app\.route\(\'/check\'\).*?(?=\n@app\.route|\nif __name__)'
content = re.sub(pattern, new_check, content, flags=re.DOTALL)

with open('monitor.py', 'w') as f:
    f.write(content)

print("✅ /check endpoint fixed!")
