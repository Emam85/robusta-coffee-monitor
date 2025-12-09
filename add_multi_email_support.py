"""
Add multi-recipient email support for weekly PDF reports
Sends to 3 email addresses + keeps Telegram delivery
"""

with open('monitor.py', 'r') as f:
    content = f.read()

# Step 1: Update the EMAIL_TO variable parsing to support multiple recipients
old_email_config = "EMAIL_TO = os.environ.get('EMAIL_TO', EMAIL_FROM)"

new_email_config = """EMAIL_TO = os.environ.get('EMAIL_TO', EMAIL_FROM)
# Parse multiple email recipients (comma-separated)
EMAIL_RECIPIENTS = [email.strip() for email in EMAIL_TO.split(',')]"""

if old_email_config in content:
    content = content.replace(old_email_config, new_email_config)
    print("✅ Step 1: Email recipients parsing added")

# Step 2: Find and update the send_weekly_report function
old_weekly_function = '''def send_weekly_report():
    """Send weekly PDF report (Friday only)"""
    if datetime.now().weekday() != 4:  # 4 = Friday
        return
    
    print("\\nðŸ"„ Generating weekly PDF report...")
    
    pdf_path = generate_weekly_pdf_report()
    
    if pdf_path and TELEGRAM_BOT_TOKEN:
        caption = f"ðŸ"Š Abu Auf Commodities - Weekly Report\\n{datetime.now().strftime('%Y-%m-%d')}"
        send_telegram_document(pdf_path, caption)
        print("âœ… Weekly report sent!")
    else:
        print("âš ï¸ Weekly report generation failed")'''

new_weekly_function = '''def send_weekly_report():
    """Send weekly PDF report (Friday only) via Telegram AND Email"""
    if datetime.now().weekday() != 4:  # 4 = Friday
        return
    
    print("\\nðŸ"„ Generating weekly PDF report...")
    
    pdf_path = generate_weekly_pdf_report()
    
    if not pdf_path:
        print("âš ï¸ Weekly report generation failed")
        return
    
    # Send via Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        caption = f"ðŸ"Š Abu Auf Commodities - Weekly Report\\n{datetime.now().strftime('%Y-%m-%d')}"
        if send_telegram_document(pdf_path, caption):
            print("âœ… Weekly report sent to Telegram!")
        else:
            print("âš ï¸ Failed to send to Telegram")
    
    # Send via Email to all recipients
    if EMAIL_FROM and EMAIL_PASSWORD and EMAIL_RECIPIENTS:
        print(f"\\nðŸ"§ Sending PDF to {len(EMAIL_RECIPIENTS)} email recipients...")
        
        subject = f"ðŸ"Š Abu Auf Commodities - Weekly Report - {datetime.now().strftime('%B %d, %Y')}"
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #003366; border-bottom: 3px solid #003366; padding-bottom: 10px;">
                        ðŸ"Š Abu Auf Commodities Intelligence Report
                    </h2>
                    
                    <p>Dear Team,</p>
                    
                    <p>Please find attached the <strong>Weekly Commodities Report</strong> for the week ending <strong>{datetime.now().strftime('%B %d, %Y')}</strong>.</p>
                    
                    <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <h3 style="margin-top: 0; color: #003366;">ðŸ"‹ Report Contents:</h3>
                        <ul style="margin-bottom: 0;">
                            <li>Executive Summary with Market Overview</li>
                            <li>Weekly Price Performance (All 7 Commodities)</li>
                            <li>Supply & Demand Analysis by Category</li>
                            <li>Key Risk Factors & Market Outlook</li>
                            <li>Strategic Procurement Recommendations</li>
                        </ul>
                    </div>
                    
                    <div style="background-color: #e8f4f8; padding: 15px; border-radius: 5px; border-left: 4px solid #0066cc;">
                        <h4 style="margin-top: 0; color: #0066cc;">ðŸ"Š Commodities Tracked:</h4>
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
                    print(f"   âœ… Sent to {recipient}")
                    success_count += 1
                else:
                    print(f"   âŒ Failed to send to {recipient}")
            except Exception as e:
                print(f"   âŒ Error sending to {recipient}: {e}")
        
        print(f"\\nðŸ"§ Email delivery: {success_count}/{len(EMAIL_RECIPIENTS)} successful")
    
    print("\\nâœ… Weekly report distribution completed!")'''

# Replace the function
if "def send_weekly_report():" in content:
    # Find the function and replace it
    import re
    pattern = r'def send_weekly_report\(\):.*?(?=\ndef |\nif __name__)'
    content = re.sub(pattern, new_weekly_function + '\n\n', content, flags=re.DOTALL)
    print("✅ Step 2: send_weekly_report() function updated")

# Step 3: Add the email sending function with attachment support
email_function = '''
def send_email_with_attachment(to_email, subject, html_body, attachment_path, attachment_name):
    """Send email with PDF attachment"""
    try:
        # Create message
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        
        # Attach HTML body
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Attach PDF
        with open(attachment_path, 'rb') as f:
            pdf_part = MIMEBase('application', 'pdf')
            pdf_part.set_payload(f.read())
        
        encoders.encode_base64(pdf_part)
        pdf_part.add_header(
            'Content-Disposition',
            f'attachment; filename={attachment_name}'
        )
        msg.attach(pdf_part)
        
        # Send via Gmail SMTP
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
        
        return True
        
    except Exception as e:
        print(f"      Error: {e}")
        return False
'''

# Add the function before send_weekly_report
if "def send_email_with_attachment(" not in content:
    # Find where to insert (before send_weekly_report)
    insert_point = content.find("def send_weekly_report():")
    if insert_point > 0:
        content = content[:insert_point] + email_function + content[insert_point:]
        print("✅ Step 3: send_email_with_attachment() function added")

# Save the updated file
with open('monitor.py', 'w') as f:
    f.write(content)

print("\n" + "="*70)
print("🎉 MULTI-EMAIL SUPPORT ADDED SUCCESSFULLY!")
print("="*70)

print("\n📧 Email Configuration:")
print("   • Primary: f.mohemam85@gmail.com")
print("   • Secondary: sherine.aboelkheir@abu-auf.com")
print("   • Tertiary: adeldodo8800@gmail.com")

print("\n📋 What Changed:")
print("   1. ✅ Added support for comma-separated email recipients")
print("   2. ✅ Updated send_weekly_report() to send via BOTH Telegram AND Email")
print("   3. ✅ Added professional HTML email template")
print("   4. ✅ Added send_email_with_attachment() function")
print("   5. ✅ PDF will be sent to all 3 email addresses every Friday")

print("\n🎯 Update Render Environment Variable:")
print("   In Render dashboard, update EMAIL_TO to:")
print("   EMAIL_TO = f.mohemam85@gmail.com,sherine.aboelkheir@abu-auf.com,adeldodo8800@gmail.com")

print("\n📅 When It Runs:")
print("   • Every Friday at 5:00 PM Cairo time")
print("   • Generates PDF report")
print("   • Sends to Telegram (instant notification)")
print("   • Sends to 3 email addresses (professional delivery)")

print("\n✅ Ready to deploy!")
print("="*70)