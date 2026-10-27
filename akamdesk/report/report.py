#!/usr/bin/env python3
"""AkamDesk device report: a small read-only dashboard over the hbbs database.

Standard library only. Listens on 127.0.0.1 so it is reachable only through an
SSH tunnel; customer names typed in the page are kept in a separate notes.db,
never in the RustDesk server database.
"""
import csv
import html
import io
import json
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

HBBS_DB = os.environ.get("HBBS_DB", "/opt/akamdesk/data/db_v2.sqlite3")
NOTES_DB = os.environ.get("NOTES_DB", "/opt/akamdesk-report/notes.db")
FONT = os.environ.get("REPORT_FONT", "/opt/akamdesk-report/Vazirmatn-Regular.ttf")
HOST = os.environ.get("REPORT_HOST", "127.0.0.1")
PORT = int(os.environ.get("REPORT_PORT", "8088"))
TEHRAN = timezone(timedelta(hours=3, minutes=30))
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def g2j(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = (355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100
            + (gy2 + 399) // 400 + gd + g_d_m[gm - 1])
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm, jd = 1 + days // 31, 1 + days % 31
    else:
        jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
    return jy, jm, jd


def to_local(created_at):
    try:
        dt = datetime.strptime(created_at[:19], "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None
    return dt.replace(tzinfo=timezone.utc).astimezone(TEHRAN)


def jalali(dt, with_time=True):
    if dt is None:
        return "-"
    y, m, d = g2j(dt.year, dt.month, dt.day)
    text = f"{y}/{m:02d}/{d:02d}"
    if with_time:
        text += f" {dt.hour:02d}:{dt.minute:02d}"
    return text.translate(FA_DIGITS)


def fa(n):
    return f"{n:,}".translate(FA_DIGITS).replace(",", "٬")


def notes_conn():
    conn = sqlite3.connect(NOTES_DB)
    conn.execute("create table if not exists note (id text primary key, name text not null)")
    return conn


def load_devices():
    conn = sqlite3.connect(f"file:{HBBS_DB}?mode=ro", uri=True)
    try:
        rows = conn.execute("select id, created_at, info from peer").fetchall()
    finally:
        conn.close()
    with notes_conn() as nc:
        names = dict(nc.execute("select id, name from note").fetchall())
    devices = []
    for pid, created_at, info in rows:
        try:
            ip = json.loads(info or "{}").get("ip", "")
        except ValueError:
            ip = ""
        devices.append({
            "id": pid,
            "created": to_local(created_at),
            "ip": ip,
            "name": names.get(pid, ""),
        })
    devices.sort(key=lambda d: d["created"] or datetime.min.replace(tzinfo=TEHRAN), reverse=True)
    return devices


def render(devices):
    now = datetime.now(TEHRAN)
    today = now.date()

    def since(days):
        return sum(1 for d in devices if d["created"] and (today - d["created"].date()).days < days)

    per_day = []
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        per_day.append((day, sum(1 for d in devices if d["created"] and d["created"].date() == day)))
    top = max([c for _, c in per_day] + [1])
    bars = "".join(
        f'<div class="bar" title="{jalali(datetime(day.year, day.month, day.day), False)}: {fa(c)}">'
        f'<span style="height:{max(c / top * 100, 2 if c else 0):.1f}%"></span></div>'
        for day, c in per_day
    )
    rows = "".join(
        f"""<tr>
<td class="ltr">{html.escape(d['id'])}</td>
<td><form method="post" action="/note" class="note">
<input type="hidden" name="id" value="{html.escape(d['id'])}">
<input name="name" value="{html.escape(d['name'])}" placeholder="نام مشتری…">
<button>ذخیره</button></form></td>
<td class="ltr">{html.escape(d['ip']) or '-'}</td>
<td>{jalali(d['created'])}</td>
</tr>"""
        for d in devices
    )
    named = sum(1 for d in devices if d["name"])
    return f"""<!doctype html>
<html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>گزارش AkamDesk</title>
<style>
@font-face {{ font-family: Vazirmatn; src: url(/font.ttf); }}
:root {{ --teal:#009799; --navy:#02212C; --bg:#F4F8F8; --card:#fff; --line:#DDEDED; --muted:#5B6B70; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family: Vazirmatn, Tahoma, sans-serif; background:var(--bg); color:var(--navy); }}
header {{ background:var(--navy); color:#fff; padding:18px 24px; display:flex; justify-content:space-between; align-items:center; }}
header h1 {{ margin:0; font-size:20px; }} header h1 b {{ color:#4FD1C5; }}
header small {{ color:#9FB8BD; }}
main {{ max-width:1100px; margin:0 auto; padding:20px 16px 40px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; }}
.card .n {{ font-size:28px; font-weight:700; color:var(--teal); }}
.card .l {{ color:var(--muted); font-size:13px; }}
.panel {{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px; margin-top:16px; }}
.panel h2 {{ margin:0 0 12px; font-size:16px; }}
.chart {{ display:flex; align-items:flex-end; gap:4px; height:120px; direction:ltr; }}
.bar {{ flex:1; height:100%; display:flex; align-items:flex-end; }}
.bar span {{ display:block; width:100%; background:var(--teal); border-radius:4px 4px 0 0; }}
.tools {{ display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }}
.tools input {{ flex:1; min-width:200px; }}
input {{ font:inherit; padding:8px 10px; border:1px solid var(--line); border-radius:10px; background:#fff; }}
button, .btn {{ font:inherit; padding:8px 14px; border:0; border-radius:10px; background:var(--teal); color:#fff; cursor:pointer; text-decoration:none; }}
table {{ width:100%; border-collapse:collapse; font-size:14px; }}
th, td {{ text-align:right; padding:8px; border-bottom:1px solid var(--line); }}
th {{ color:var(--muted); font-weight:500; }}
.ltr {{ direction:ltr; text-align:right; font-variant-numeric:tabular-nums; }}
.note {{ display:flex; gap:6px; }} .note input {{ flex:1; padding:5px 8px; }} .note button {{ padding:5px 10px; }}
.hint {{ color:var(--muted); font-size:12px; margin-top:10px; }}
</style></head><body>
<header><h1>گزارش <b>AkamDesk</b></h1><small>به‌روزرسانی: {jalali(now)}</small></header>
<main>
<div class="cards">
<div class="card"><div class="n">{fa(len(devices))}</div><div class="l">کل دستگاه‌های ثبت‌شده</div></div>
<div class="card"><div class="n">{fa(since(1))}</div><div class="l">دستگاه جدید امروز</div></div>
<div class="card"><div class="n">{fa(since(7))}</div><div class="l">دستگاه جدید ۷ روز اخیر</div></div>
<div class="card"><div class="n">{fa(since(30))}</div><div class="l">دستگاه جدید ۳۰ روز اخیر</div></div>
<div class="card"><div class="n">{fa(named)}</div><div class="l">دستگاه با نام مشتری</div></div>
</div>
<div class="panel"><h2>دستگاه‌های جدید در ۳۰ روز اخیر</h2><div class="chart">{bars}</div></div>
<div class="panel"><h2>لیست دستگاه‌ها</h2>
<div class="tools"><input id="q" placeholder="جستجو در شناسه، نام مشتری یا IP…" oninput="filter()">
<a class="btn" href="/export.csv">خروجی اکسل (CSV)</a></div>
<table><thead><tr><th>شناسه</th><th>نام مشتری</th><th>آخرین IP</th><th>اولین اتصال</th></tr></thead>
<tbody id="rows">{rows}</tbody></table>
<div class="hint">هر کامپیوتری که حتی یک بار AkamDesk را اجرا کرده باشد در این لیست است. وضعیت آنلاین بودن در نسخه‌ی رایگان سرور ثبت نمی‌شود.</div>
</div></main>
<script>
function filter() {{
  const q = document.getElementById('q').value.trim().toLowerCase();
  for (const tr of document.querySelectorAll('#rows tr')) {{
    const name = tr.querySelector('input[name=name]').value.toLowerCase();
    tr.style.display = !q || tr.textContent.toLowerCase().includes(q) || name.includes(q) ? '' : 'none';
  }}
}}
</script></body></html>"""


def export_csv(devices):
    buf = io.StringIO()
    buf.write("﻿")
    w = csv.writer(buf)
    w.writerow(["شناسه", "نام مشتری", "آخرین IP", "اولین اتصال (شمسی)", "اولین اتصال (میلادی)"])
    for d in devices:
        w.writerow([d["id"], d["name"], d["ip"], jalali(d["created"]),
                    d["created"].strftime("%Y-%m-%d %H:%M") if d["created"] else ""])
    return buf.getvalue().encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            if self.path == "/":
                self.send(200, render(load_devices()).encode("utf-8"), "text/html; charset=utf-8")
            elif self.path == "/export.csv":
                self.send(200, export_csv(load_devices()), "text/csv; charset=utf-8",
                          {"Content-Disposition": 'attachment; filename="akamdesk-devices.csv"'})
            elif self.path == "/font.ttf" and os.path.exists(FONT):
                with open(FONT, "rb") as f:
                    self.send(200, f.read(), "font/ttf", {"Cache-Control": "max-age=86400"})
            else:
                self.send(404, b"not found", "text/plain")
        except sqlite3.Error as e:
            self.send(500, f"database error: {e}".encode("utf-8"), "text/plain; charset=utf-8")

    def do_POST(self):
        if self.path != "/note":
            self.send(404, b"not found", "text/plain")
            return
        origin = self.headers.get("Origin")
        if origin and origin.split("://", 1)[-1] != self.headers.get("Host", ""):
            self.send(403, b"forbidden", "text/plain")
            return
        length = int(self.headers.get("Content-Length") or 0)
        form = parse_qs(self.rfile.read(min(length, 4096)).decode("utf-8"))
        pid = (form.get("id") or [""])[0].strip()[:100]
        name = (form.get("name") or [""])[0].strip()[:200]
        if pid:
            with notes_conn() as nc:
                if name:
                    nc.execute("insert into note(id, name) values(?, ?) "
                               "on conflict(id) do update set name=excluded.name", (pid, name))
                else:
                    nc.execute("delete from note where id=?", (pid,))
        self.send(303, b"", "text/plain", {"Location": "/"})

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    print(f"AkamDesk report on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
