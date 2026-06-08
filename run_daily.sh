#!/usr/bin/env bash
set -uo pipefail
umask 077

cd /home/kzamd22/job
LOG="output/scrape_$(date +%F).log"

echo "=== $(date) ===" >> "$LOG"
/home/kzamd22/job/venv/bin/python main.py run >> "$LOG" 2>&1
EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
    /home/kzamd22/job/venv/bin/python - <<'PYEOF'
import os, smtplib, datetime
from email.message import EmailMessage
from dotenv import load_dotenv
load_dotenv()
email = os.environ.get('NOTIFY_EMAIL', '')
pw    = os.environ.get('GMAIL_APP_PASSWORD', '')
if not email or not pw:
    raise SystemExit(0)
log_path = 'output/scrape_' + datetime.date.today().isoformat() + '.log'
MAX_BYTES = 50_000
raw = open(log_path, 'rb').read() if os.path.exists(log_path) else b'Log file not found.'
body = raw[-MAX_BYTES:].decode('utf-8', errors='replace')
msg = EmailMessage()
msg['Subject'] = 'Job scraper FAILED'
msg['From']    = email
msg['To']      = email
msg.set_content(body)
with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(email, pw)
    smtp.send_message(msg)
PYEOF
fi

echo "=== done (exit $EXIT_CODE) ===" >> "$LOG"
exit "$EXIT_CODE"
