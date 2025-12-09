import smtplib
import os
from email.mime.text import MIMEText

# Get variables
user = os.environ.get('EMAIL_FROM')
password = os.environ.get('EMAIL_PASSWORD')
to_email = os.environ.get('EMAIL_TO')

print(f"📧 Testing connection for: {user}")
print("   Using Port: 587 (TLS)")

try:
    # Connect to GMAIL on Port 587 (The specific fix)
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.set_debuglevel(1) # Show us exactly what happens
    server.starttls()        # Encrypt the connection
    print("   ✅ Connection Established!")
    
    server.login(user, password)
    print("   ✅ Login Successful!")
    
    msg = MIMEText("If you see this, the Render Email Fix is working! 🚀")
    msg['Subject'] = "Test Email from Port 587"
    msg['From'] = user
    msg['To'] = to_email
    
    server.send_message(msg)
    server.quit()
    print("\n🎉 SUCCESS! Email sent via Port 587.")
    
except Exception as e:
    print(f"\n❌ FAILED: {e}")
