#!/usr/bin/env python3
"""
Test script to verify all configurations before deployment
Run this in GitHub Codespaces to check everything works
"""

import os
import sys

def check_environment_variables():
    """Check if all required environment variables are set"""
    print("\n" + "="*60)
    print("🔍 CHECKING ENVIRONMENT VARIABLES")
    print("="*60)
    
    required_vars = {
        'TELEGRAM_BOT_TOKEN': 'Telegram bot token from @BotFather',
        'TELEGRAM_CHAT_ID': 'Your Telegram chat ID from @userinfobot',
        'GEMINI_API_KEY': 'Google Gemini API key',
        'EMAIL_FROM': 'Your Gmail address',
        'EMAIL_PASSWORD': 'Gmail app-specific password',
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Show first/last few characters for security
            if len(value) > 20:
                masked = f"{value[:8]}...{value[-8:]}"
            else:
                masked = value[:3] + "..." + value[-3:]
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: NOT SET ({description})")
            all_set = False
    
    print()
    return all_set

def test_telegram():
    """Test Telegram bot connection"""
    print("="*60)
    print("📱 TESTING TELEGRAM BOT")
    print("="*60)
    
    try:
        import requests
        
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if not token or not chat_id:
            print("❌ Missing Telegram credentials")
            return False
        
        # Test bot API
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            bot_info = response.json()
            print(f"✅ Bot connected: @{bot_info['result']['username']}")
            
            # Send test message
            send_url = f"https://api.telegram.org/bot{token}/sendMessage"
            test_message = "🧪 Test message from Robusta Monitor setup!\n\nIf you see this, Telegram notifications are working! ✅"
            
            payload = {
                'chat_id': chat_id,
                'text': test_message
            }
            
            send_response = requests.post(send_url, json=payload, timeout=10)
            
            if send_response.status_code == 200:
                print("✅ Test message sent! Check your Telegram app.")
                return True
            else:
                print(f"❌ Failed to send message: {send_response.text}")
                return False
        else:
            print(f"❌ Bot connection failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_gemini():
    """Test Gemini API connection"""
    print("\n" + "="*60)
    print("🤖 TESTING GEMINI API")
    print("="*60)
    
    try:
        import google.generativeai as genai
        
        api_key = os.environ.get('GEMINI_API_KEY')
        
        if not api_key:
            print("❌ Missing Gemini API key")
            return False
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        response = model.generate_content("Say 'Gemini API is working!' in one sentence")
        
        if response.text:
            print(f"✅ Gemini API connected")
            print(f"   Response: {response.text[:100]}...")
            return True
        else:
            print("❌ No response from Gemini")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_email():
    """Test email configuration"""
    print("\n" + "="*60)
    print("📧 TESTING EMAIL CONFIGURATION")
    print("="*60)
    
    try:
        import smtplib
        from email.mime.text import MIMEText
        
        email_from = os.environ.get('EMAIL_FROM')
        email_password = os.environ.get('EMAIL_PASSWORD')
        
        if not email_from or not email_password:
            print("❌ Missing email credentials")
            return False
        
        # Test SMTP connection
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(email_from, email_password)
            print("✅ Gmail SMTP connection successful")
            
            # Send test email
            msg = MIMEText("This is a test email from Robusta Monitor setup.\n\nIf you receive this, email notifications are working! ✅")
            msg['Subject'] = '🧪 Test Email - Robusta Monitor'
            msg['From'] = email_from
            msg['To'] = email_from
            
            server.send_message(msg)
            print(f"✅ Test email sent to {email_from}")
            print("   Check your inbox!")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Tips:")
        print("   - Use Gmail app-specific password (not account password)")
        print("   - Get it from: https://myaccount.google.com/apppasswords")
        print("   - Password should be 16 characters")
        return False

def test_yahoo_finance():
    """Test Yahoo Finance data fetching"""
    print("\n" + "="*60)
    print("📊 TESTING YAHOO FINANCE DATA")
    print("="*60)
    
    try:
        import yfinance as yf
        
        # Test fetching Robusta Coffee data
        ticker = yf.Ticker('RC=F')
        hist = ticker.history(period='1d')
        
        if not hist.empty:
            latest = hist.iloc[-1]
            price = float(latest['Close'])
            print(f"✅ Yahoo Finance working")
            print(f"   Robusta Coffee (RC=F): ${price:.2f}")
            return True
        else:
            print("❌ No data returned")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_full_monitor():
    """Run a full monitoring cycle"""
    print("\n" + "="*60)
    print("🚀 RUNNING FULL MONITOR TEST")
    print("="*60)
    
    try:
        # Set LOCAL_TEST flag
        os.environ['LOCAL_TEST'] = 'true'
        
        # Import and run monitor
        from monitor import monitor_all_commodities
        
        print("Starting monitor cycle...\n")
        result = monitor_all_commodities()
        
        if result['status'] == 'success':
            print(f"\n✅ Monitor completed successfully!")
            print(f"   Commodities updated: {result['commodities_updated']}")
            print(f"   Timestamp: {result['timestamp']}")
            return True
        else:
            print(f"\n⚠️ Monitor status: {result['status']}")
            if 'reason' in result:
                print(f"   Reason: {result['reason']}")
            return False
            
    except Exception as e:
        print(f"❌ Error running monitor: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 ROBUSTA MONITOR - CONFIGURATION TEST")
    print("="*70)
    print("\nThis script will verify your setup before deployment.")
    print("Make sure you have set all environment variables!\n")
    
    # Check Python version
    print("Python version:", sys.version)
    
    # Run tests
    results = {
        'Environment Variables': check_environment_variables(),
        'Telegram Bot': test_telegram(),
        'Gemini API': test_gemini(),
        'Email': test_email(),
        'Yahoo Finance': test_yahoo_finance(),
        'Full Monitor': test_full_monitor(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("📋 TEST SUMMARY")
    print("="*70)
    
    for test, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test:.<50} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED! You're ready to deploy!")
        print("\nNext steps:")
        print("1. Commit and push your code: git add . && git commit -m 'Add monitor' && git push")
        print("2. Deploy to Render.com")
        print("3. Set environment variables in Render dashboard")
        print("4. Wait for deployment and check logs")
    else:
        print("⚠️ SOME TESTS FAILED")
        print("\nPlease fix the issues above before deploying.")
        print("\nCommon fixes:")
        print("- Set missing environment variables")
        print("- Check API keys are valid")
        print("- Verify Telegram bot is started (send /start)")
        print("- Use Gmail app-specific password")
    print("="*70 + "\n")

if __name__ == '__main__':
    main()