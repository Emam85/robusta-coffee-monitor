"""
Add /check endpoint to monitor.py
"""

with open('monitor.py', 'r') as f:
    content = f.read()

# Check if /check endpoint already exists
if '@app.route(\'/check\')' in content or '@app.route("/check")' in content:
    print("✅ /check endpoint already exists!")
else:
    # Find the location to add the new endpoint (after the main route)
    # Add before "if __name__ == '__main__':"
    
    check_endpoint = '''
@app.route('/check')
def manual_check():
    """Manual trigger for monitoring cycle"""
    try:
        print("🔄 Manual check triggered via /check endpoint")
        result = run_monitor()
        return jsonify({
            "status": "success",
            "message": "Monitor cycle completed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"❌ Error in manual check: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

'''
    
    # Insert before "if __name__ == '__main__':"
    if "if __name__ == '__main__':" in content:
        content = content.replace(
            "if __name__ == '__main__':",
            check_endpoint + "if __name__ == '__main__':"
        )
    else:
        # If not found, append at the end
        content += "\n" + check_endpoint
    
    with open('monitor.py', 'w') as f:
        f.write(content)
    
    print("✅ /check endpoint added to monitor.py!")

