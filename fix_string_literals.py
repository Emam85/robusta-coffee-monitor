"""
Fix unterminated string literals in monitor.py
The issue is likely in the send_weekly_report function with print statements
"""

with open('monitor.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("=" * 70)
print("🔧 Fixing String Literal Issues")
print("=" * 70)

# Fix 1: Find and replace problematic print statements in send_weekly_report
# These often have broken unicode characters from copy-paste

problematic_patterns = [
    (r'print\("\\nÃ°Å¸"â€ž', 'print("\\n📄'),
    (r'print\("Ã¢Å¡ Ã¯Â¸', 'print("⚠️'),
    (r'print\("Ã¢Å"â€¦', 'print("✅'),
    (r'print\(f"\\nÃ°Å¸"Â§', 'print(f"\\n📧'),
    (r'print\(f"\\nÃ°Å¸"Â§', 'print(f"\\n📧'),
    (r'caption = f"Ã°Å¸"Å ', 'caption = f"📊'),
    (r'subject = f"Ã°Å¸"Å ', 'subject = f"📊'),
]

fixed_count = 0
for pattern, replacement in problematic_patterns:
    import re
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        fixed_count += 1

if fixed_count > 0:
    print(f"   ✅ Fixed {fixed_count} problematic string patterns")

# Fix 2: Ensure the send_weekly_report function is properly formatted
# Replace the entire function with a clean version

if 'def send_weekly_report():' in content:
    print("\n🔄 Rebuilding send_weekly_report() with clean strings...")
    
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
    
    print("\\n✅ Weekly report distribution completed!")'''
    
    # Find and replace the function
    import re
    pattern = r'def send_weekly_report\(\):.*?(?=\n\ndef [a-z_]|\n@app\.route)'
    content = re.sub(pattern, clean_function + '\n', content, flags=re.DOTALL)
    print("   ✅ Rebuilt send_weekly_report() with clean ASCII")

# Save the file
with open('monitor.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n" + "=" * 70)
print("🧪 Testing syntax...")
print("=" * 70)

import subprocess
result = subprocess.run(['python', '-m', 'py_compile', 'monitor.py'], 
                       capture_output=True, text=True)

if result.returncode == 0:
    print("   ✅ SUCCESS! Syntax is VALID!")
    print("\n🚀 Ready to commit and deploy!")
    print("\n📝 Next steps:")
    print("   git add monitor.py")
    print("   git commit -m 'Fix all syntax errors and clean strings'")
    print("   git push")
else:
    print("   ❌ Syntax error still exists:")
    print(result.stderr)
    
    # Try to identify the line
    if 'line' in result.stderr:
        import re
        match = re.search(r'line (\d+)', result.stderr)
        if match:
            line_num = int(match.group(1))
            print(f"\n🔍 Problem is around line {line_num}")
            print("   Showing context:")
            with open('monitor.py', 'r') as f:
                lines = f.readlines()
                start = max(0, line_num - 3)
                end = min(len(lines), line_num + 2)
                for i in range(start, end):
                    marker = ">>>" if i == line_num - 1 else "   "
                    print(f"{marker} {i+1:4d}: {lines[i]}", end='')

print("\n" + "=" * 70)