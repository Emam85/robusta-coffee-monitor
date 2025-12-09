import re

with open('monitor.py', 'r') as f:
    content = f.read()

# Fix 1: Add tempfile import
if 'import tempfile' not in content:
    content = content.replace(
        'from io import BytesIO',
        'from io import BytesIO\nimport tempfile'
    )

# Fix 2: Change PDF path
content = content.replace(
    "pdf_path = f'/tmp/abu_auf_weekly_{datetime.now().strftime(\"%Y%m%d\")}.pdf'",
    "pdf_path = tempfile.mktemp(suffix='.pdf', prefix='abu_auf_weekly_')"
)

with open('monitor.py', 'w') as f:
    f.write(content)

print("✅ PDF path fixed!")
