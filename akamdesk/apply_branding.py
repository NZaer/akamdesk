#!/usr/bin/env python3
"""Apply AkamDesk branding on top of a fresh RustDesk checkout.

Run from the repository root after `git submodule update --init`:
    python3 akamdesk/apply_branding.py

Upstream source files are only modified at build time, so the fork's master
branch stays identical to RustDesk and "Sync fork" never conflicts.
Every replacement must match exactly once; if upstream changes a line,
the build stops here instead of silently shipping a half-branded client.
"""
import shutil
import sys
from pathlib import Path

APP_NAME = "AkamDesk"
COMPANY = "Akam Data"
ID_SERVER = "desk.akamdata.com"
PUBLIC_KEY = "yxgsv8GIJsj6Ln8AQcLqpq0y7OE07zK8AM9LIzIp3Ek="
DEFAULT_LANG = "fa"

TEAL = "0xFF009799"
TEAL_50 = "0x77009799"
TEAL_80 = "0xAA009799"

ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent / "assets"


def replace(rel_path, old, new):
    path = ROOT / rel_path
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        sys.exit(f"[branding] expected 1 match in {rel_path}, found {count}: {old!r}")
    path.write_text(text.replace(old, new), encoding="utf-8")
    print(f"[branding] {rel_path}")


def copy(asset, *targets):
    for target in targets:
        shutil.copyfile(ASSETS / asset, ROOT / target)
        print(f"[branding] {target} <- {asset}")


# Name, server and key (hbb_common submodule)
cfg = "libs/hbb_common/src/config.rs"
replace(cfg, 'APP_NAME: RwLock<String> = RwLock::new("RustDesk".to_owned());',
        f'APP_NAME: RwLock<String> = RwLock::new("{APP_NAME}".to_owned());')
replace(cfg, 'pub const RENDEZVOUS_SERVERS: &[&str] = &["rs-ny.rustdesk.com"];',
        f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{ID_SERVER}"];')
replace(cfg, 'pub const RS_PUB_KEY: &str = "OeVuKk5nlHiXp+APNn0Y3pC1Iwpwn44JGqrQCsWqmBw=";',
        f'pub const RS_PUB_KEY: &str = "{PUBLIC_KEY}";')
# Persian UI by default; users can still switch to English in Settings > General > Language
replace(cfg, "pub static ref DEFAULT_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = Default::default();",
        f'pub static ref DEFAULT_LOCAL_SETTINGS: RwLock<HashMap<String, String>> = '
        f'RwLock::new(HashMap::from([("lang".to_owned(), "{DEFAULT_LANG}".to_owned())]));')

# Colors
common = "flutter/lib/common.dart"
replace(common, "static const Color accent = Color(0xFF0071FF);",
        f"static const Color accent = Color({TEAL});")
replace(common, "static const Color accent50 = Color(0x770071FF);",
        f"static const Color accent50 = Color({TEAL_50});")
replace(common, "static const Color accent80 = Color(0xAA0071FF);",
        f"static const Color accent80 = Color({TEAL_80});")
replace(common, "static const Color idColor = Color(0xFF00B6F0);",
        f"static const Color idColor = Color({TEAL});")
replace(common, "static const Color button = Color(0xFF2C8CFF);",
        f"static const Color button = Color({TEAL});")
replace(common, "  return Color(0xFF2C8CFF);\n}",
        f"  return Color({TEAL});\n}}")
replace("flutter/lib/desktop/pages/desktop_home_page.dart",
        "Color.fromARGB(255, 226, 66, 188),\n                  Color.fromARGB(255, 244, 114, 124),",
        "Color.fromARGB(255, 0, 151, 153),\n                  Color.fromARGB(255, 2, 33, 44),")

# Hide the "Powered by RustDesk" line under the logo
replace(common, 'if (bind.mainGetBuildinOption(key: "hide-powered-by-me") == \'Y\') {',
        "if (true) {")

# Window title bar text
replace("flutter/lib/desktop/widgets/tabbar_widget.dart",
        '"RustDesk",\n                              style: TextStyle(fontSize: 13),',
        f'"{APP_NAME}",\n                              style: TextStyle(fontSize: 13),')

# Windows file properties (Properties > Details)
rc = "flutter/windows/runner/Runner.rc"
replace(rc, 'VALUE "CompanyName", "Purslane Tech Pte. Ltd." "\\0"',
        f'VALUE "CompanyName", "{COMPANY}" "\\0"')
replace(rc, 'VALUE "FileDescription", "RustDesk Remote Desktop" "\\0"',
        f'VALUE "FileDescription", "{APP_NAME} Remote Support" "\\0"')
replace(rc, 'VALUE "ProductName", "RustDesk" "\\0"',
        f'VALUE "ProductName", "{APP_NAME}" "\\0"')
replace(rc, 'VALUE "LegalCopyright", "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved." "\\0"',
        f'VALUE "LegalCopyright", "{COMPANY}. Based on RustDesk (AGPL-3.0)." "\\0"')

# Icons and logos
copy("icon.ico", "res/icon.ico", "flutter/windows/runner/resources/app_icon.ico", "flutter/assets/icon.ico")
copy("tray-icon.ico", "res/tray-icon.ico")
copy("icon.svg", "flutter/assets/icon.svg")
copy("icon.png", "res/icon.png")
copy("32x32.png", "res/32x32.png")
copy("64x64.png", "res/64x64.png")
copy("128x128.png", "res/128x128.png")
copy("128x128@2x.png", "res/128x128@2x.png")
copy("logo_light.png", "flutter/assets/logo_light.png")
copy("logo_dark.png", "flutter/assets/logo_dark.png")

print(f"[branding] done: {APP_NAME} -> {ID_SERVER}")
