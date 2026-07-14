#!/usr/bin/env bash
# Local runner invoked by the job-scraper.timer systemd unit (daily, 7am).
# Writes output to output/scrape_YYYY-MM-DD.log and emails on failure.
# Does NOT deploy to GitHub Pages — that is handled by the GitHub Actions workflow.
set -uo pipefail
umask 077

cd /home/kzamd22/job
LOG="output/scrape_$(date +%F).log"

# Guard against overlapping invocations — a second run racing the first on the
# same-second output filename crashes main.py's atomic write. Skip instead of
# crashing if another run already holds the lock. Lock lives in the repo, not
# /tmp, so a stray root-owned file can't poison it.
LOCKFILE="output/.job-scraper.lock"
exec 200>"$LOCKFILE"
if ! flock -n 200; then
    echo "=== $(date) === another run is already in progress, skipping" >> "$LOG"
    exit 0
fi

echo "=== $(date) ===" >> "$LOG"
# 200>&- keeps the lock fd out of python's children so a leaked subprocess can't
# hold the lock after we exit; timeout bounds a hung run so the lock can't be
# held forever (124 exit → failure email below).
timeout 3600 /home/kzamd22/job/venv/bin/python main.py run >> "$LOG" 2>&1 200>&-
EXIT_CODE=$?

if [ "$EXIT_CODE" -ne 0 ]; then
    /home/kzamd22/job/venv/bin/python - <<'PYEOF'
import os, smtplib, datetime
from email.message import EmailMessage
from dotenv import load_dotenv
# Explicit path: load_dotenv()'s default find_dotenv() walks the caller's stack
# frames, which is None when this runs as a `python -` stdin heredoc and crashes.
# Relative to the repo root — the script cd's there before this runs.
load_dotenv('.env')
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
