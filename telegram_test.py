#!/usr/bin/env python3
"""
Telegram Bot Notification Tester
This script tests if your Telegram bot configuration is working correctly.
"""

import os
import requests
import sys

def test_telegram_bot():
    """Test Telegram bot configuration and send a test message."""
    
    print("\n🔍 TELEGRAM BOT CONFIGURATION TEST")
    print("=" * 60)
    
    # Get environment variables
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    # Check if credentials exist
    print("\n1. Checking Environment Variables...")
    if not bot_token:
        print("   ❌ TELEGRAM_BOT_TOKEN is missing!")
        return False
    else:
        print(f"   ✅ TELEGRAM_BOT_TOKEN found: {bot_token[:20]}...")
    
    if not chat_id:
        print("   ❌ TELEGRAM_CHAT_ID is missing!")
        return False
    else:
        print(f"   ✅ TELEGRAM_CHAT_ID found: {chat_id}")
    
    # Test bot validity
    print("\n2. Testing Bot Token Validity...")
    try:
        response = requests.get(
            f'https://api.telegram.org/bot{bot_token}/getMe',
            timeout=10
        )
        if response.status_code == 200:
            bot_info = response.json()
            if bot_info.get('ok'):
                print(f"   ✅ Bot is valid: @{bot_info['result']['username']}")
            else:
                print(f"   ❌ Bot token invalid: {bot_info}")
                return False
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Error testing bot: {e}")
        return False
    
    # Send test message
    print("\n3. Sending Test Message...")
    test_message = """
🧪 **Test Message from Commodity Monitor**

This is a test to verify your Telegram notifications are working.

If you receive this message, your configuration is correct! ✅

---
*Robusta Coffee Monitor*
"""
    
    try:
        response = requests.post(
            f'https://api.telegram.org/bot{bot_token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': test_message,
                'parse_mode': 'Markdown'
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("   ✅ Test message sent successfully!")
                print(f"   📱 Message ID: {result['result']['message_id']}")
                return True
            else:
                print(f"   ❌ Telegram API error: {result}")
                return False
        else:
            print(f"   ❌ HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error sending message: {e}")
        return False

def check_chat_permissions():
    """Check if the bot can send messages to the chat."""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        return
    
    print("\n4. Checking Chat Permissions...")
    try:
        response = requests.get(
            f'https://api.telegram.org/bot{bot_token}/getChat',
            params={'chat_id': chat_id},
            timeout=10
        )
        
        if response.status_code == 200:
            chat_info = response.json()
            if chat_info.get('ok'):
                chat_data = chat_info['result']
                print(f"   ✅ Chat found: {chat_data.get('title', 'Private Chat')}")
                print(f"   📋 Chat type: {chat_data.get('type')}")
            else:
                print(f"   ❌ Cannot access chat: {chat_info}")
        else:
            print(f"   ⚠️  Cannot verify chat (may still work): HTTP {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Cannot verify chat (may still work): {e}")

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  TELEGRAM BOT NOTIFICATION TESTER")
    print("=" * 60)
    
    success = test_telegram_bot()
    check_chat_permissions()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED! Your Telegram bot is working correctly.")
    else:
        print("❌ TESTS FAILED! Please check the errors above.")
        print("\nCommon issues:")
        print("  1. Wrong TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        print("  2. Bot not added to the chat/group")
        print("  3. Bot doesn't have permission to send messages")
        print("  4. Chat ID format incorrect (should be number, e.g., -5035384619)")
    print("=" * 60 + "\n")
    
    sys.exit(0 if success else 1)