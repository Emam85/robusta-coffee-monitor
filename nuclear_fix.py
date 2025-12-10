"""
Nuclear Fix - Find the broken send_weekly_report and completely remove it
Then insert a clean version
"""

with open('monitor.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=" * 70)
print("🔥 NUCLEAR FIX - Removing Broken Section")
print("=" * 70)

# Find where send_weekly_report starts
send_weekly_start = None
for i, line in enumerate(lines):
    if 'def send_weekly_report():' in line:
        send_weekly_start = i
        print(f"📍 Found send_weekly_report at line {i+1}")
        break

if send_weekly_start is None:
    print("❌ Could not find send_weekly_report function!")
    exit(1)

# Find where it ends (next function definition or @app.route)
send_weekly_end = None
for i in range(send_weekly_start + 1, len(lines)):
    line = lines[i]
    # Look for next function or route decorator
    if (line.startswith('def ') and not line.startswith('    ')) or line.startswith('@app.route'):
        send_weekly_end = i
        print(f"📍 Function ends at line {i}")
        break

if send_weekly_end is None:
    print("⚠️ Could not find end, assuming it goes to end of file")
    send_weekly_end = len(lines)

print(f"\n🗑️ Removing lines {send_weekly_start+1} to {send_weekly_end}")

# The clean function - properly formatted
clean_function = '''def send_weekly_report():
    """Send weekly PDF report (Friday only) via Telegram AND Email"""
    if datetime.now().weekday() != 4:  # 4 = Friday
        return
    
    print("\\n📄 Generating weekly PDF report...")
    
    pdf_path = generate_weekly_pdf_report()
    
    if not pdf_path:
        print("⚠️ Weekly report generation failed")
        return
    
    # Send via Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        caption = f"📊 Abu Auf Commodities - Weekly Report\\n{datetime.now().strftime('%Y-%m-%d')}"
        if send_telegram_document(pdf_path, caption):
            print("✅ Weekly report sent to Telegram!")
        else:
            print("⚠️ Failed to send to Telegram")
    
    # Send via Email to all recipients
    if EMAIL_FROM and EMAIL_PASSWORD and EMAIL_RECIPIENTS:
        print(f"\\n📧 Sending PDF to {len(EMAIL_RECIPIENTS)} email recipients...")
        
        subject = f"📊 Abu Auf Commodities - Weekly Report - {datetime.now().strftime('%B %d, %Y')}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #003366; border-bottom: 3px solid #003366; padding-bottom: 10px;">
                        📊 Abu Auf Commodities Intelligence Report
                    </h2>
                    
                    <p>Dear Team,</p>
                    
                    <p>Please find attached the <strong>Weekly Commodities Report</strong> for the week ending <strong>{datetime.now().strftime('%B %d, %Y')}</strong>.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #003366;">📋 Report Contents:</h3>
                        <ul style="margin-bottom: 0;">
                            <li>Executive Summary with Market Overview</li>
                            <li>Weekly Price Performance (All 7 Commodities)</li>
                            <li>Supply & Demand Analysis by Category</li>
                            <li>Key Risk Factors & Market Outlook</li>
                            <li>Strategic Procurement Recommendations</li>
                        </ul>
                    </div>
                    
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; border-left: 4px solid #0066cc;">
                        <h4 style="margin-top: 0; color: #0066cc;">📊 Commodities Tracked:</h4>
                        <p style="margin-bottom: 5px;"><strong>Softs:</strong> Robusta Coffee, Arabica Coffee, Sugar, Cocoa</p>
                        <p style="margin-bottom: 5px;"><strong>Grains:</strong> Wheat</p>
                        <p style="margin-bottom: 0;"><strong>Oils:</strong> Soybean Oil, Palm Oil</p>
                    </div>
                    
                    <p style="margin-top: 20px;">This report is generated automatically every Friday at 5:00 PM Cairo time using real-time market data and AI-powered analysis.</p>
                    
                    <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                    
                    <p style="font-size: 12px; color: #666;">
                        <strong>Abu Auf Commodities Monitor</strong><br>
                        Automated Intelligence System<br>
                        For internal use only
                    </p>
                </div>
            </body>
        </html>
        """
        
        success_count = 0
        for recipient in EMAIL_RECIPIENTS:
            try:
                if send_email_with_attachment(
                    to_email=recipient,
                    subject=subject,
                    html_body=html_body,
                    attachment_path=pdf_path,
                    attachment_name=f"Abu_Auf_Weekly_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
                ):
                    print(f"   ✅ Sent to {recipient}")
                    success_count += 1
                else:
                    print(f"   ❌ Failed to send to {recipient}")
            except Exception as e:
                print(f"   ❌ Error sending to {recipient}: {e}")
        
        print(f"\\n📧 Email delivery: {success_count}/{len(EMAIL_RECIPIENTS)} successful")
    
    print("\\n✅ Weekly report distribution completed!")


'''

# Rebuild the file
new_lines = (
    lines[:send_weekly_start] +     # Everything before
    [clean_function] +               # Clean function
    lines[send_weekly_end:]          # Everything after
)

# Write it
with open('monitor.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("✅ Function replaced")

# Test syntax
print("\n" + "=" * 70)
print("🧪 Testing syntax...")
print("=" * 70)

import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'monitor.py'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("   ✅ SUCCESS! No syntax errors!")
    print("\n🎉 monitor.py is now valid Python!")
    print("\n🚀 Ready to deploy:")
    print("   git add monitor.py")
    print("   git commit -m 'Fix all syntax errors'")
    print("   git push")
else:
    print("   ❌ Still has error:")
    print(result.stderr)
    
    # Show the problematic area
    if 'line' in result.stderr:
        import re
        match = re.search(r'line (\d+)', result.stderr)
        if match:
            line_num = int(match.group(1))
            print(f"\n🔍 Error at line {line_num}:")
            with open('monitor.py', 'r') as f:
                lines = f.readlines()
                start = max(0, line_num - 5)
                end = min(len(lines), line_num + 3)
                for i in range(start, end):
                    marker = ">>> " if i == line_num - 1 else "    "
                    print(f"{marker}{i+1:4d}: {lines[i]}", end='')

print("\n" + "=" * 70)