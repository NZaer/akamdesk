#!/bin/bash
# Installs the AkamDesk device report on the RustDesk server.
# Usage (as root): curl -fsSL https://raw.githubusercontent.com/NZaer/akamdesk/master/akamdesk/report/install.sh | bash
set -e
BASE="https://raw.githubusercontent.com/NZaer/akamdesk/master/akamdesk"
DIR=/opt/akamdesk-report

mkdir -p "$DIR"
curl -fsSL "$BASE/report/report.py" -o "$DIR/report.py"
curl -fsSL "$BASE/assets/fonts/Vazirmatn-Regular.ttf" -o "$DIR/Vazirmatn-Regular.ttf" || echo "Font download skipped (page will use Tahoma)"

cat > /etc/systemd/system/akamdesk-report.service <<'UNIT'
[Unit]
Description=AkamDesk device report (localhost only)
After=network.target docker.service

[Service]
ExecStart=/usr/bin/python3 -I /opt/akamdesk-report/report.py
WorkingDirectory=/opt/akamdesk-report
Restart=always

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable akamdesk-report >/dev/null 2>&1
systemctl restart akamdesk-report
sleep 2
if curl -fs -o /dev/null http://127.0.0.1:8088/; then
  echo "OK: AkamDesk report is running on 127.0.0.1:8088"
else
  echo "ERROR: report did not start. Check: journalctl -u akamdesk-report -n 30"
  exit 1
fi
