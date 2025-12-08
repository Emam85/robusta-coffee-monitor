with open('monitor.py', 'r') as f:
    content = f.read()

if 'from threading import Thread' not in content:
    content = content.replace(
        'from flask import Flask, jsonify',
        'from flask import Flask, jsonify\nfrom threading import Thread'
    )

old_check = '@app.route(\'/check\')\ndef manual_check():\n    """Manual trigger for monitoring cycle"""\n    try:\n        print("🔄 Manual check triggered via /check endpoint")\n        result = monitor_all_commodities()\n        return jsonify({\n            "status": "success",\n            "message": "Monitor cycle completed",\n            "result": result,\n            "timestamp": datetime.now().isoformat()\n        })\n    except Exception as e:\n        print(f"❌ Error in manual check: {e}")\n        return jsonify({\n            "status": "error",\n            "message": str(e),\n            "timestamp": datetime.now().isoformat()\n        }), 500'

new_check = '@app.route(\'/check\')\ndef manual_check():\n    """Manual trigger for monitoring cycle - runs in background"""\n    def run_in_background():\n        try:\n            print("🔄 Manual check triggered via /check endpoint (background)")\n            monitor_all_commodities()\n            print("✅ Background monitoring completed")\n        except Exception as e:\n            print(f"❌ Error in background monitor: {e}")\n    \n    thread = Thread(target=run_in_background, daemon=True)\n    thread.start()\n    \n    return jsonify({\n        "status": "started",\n        "message": "Monitoring cycle started in background",\n        "note": "Check Telegram/Email in 30-60 seconds",\n        "timestamp": datetime.now().isoformat()\n    })'

content = content.replace(old_check, new_check)

with open('monitor.py', 'w') as f:
    f.write(content)

print("✅ Fixed!")
