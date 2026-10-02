# -*- coding: utf-8 -*-
"""Guard: every shipped .ps1 must be 100% ASCII.

PowerShell 5.1 decodes a BOM-less UTF-8 .ps1 as GBK/ANSI, so a single non-ASCII
character -- even inside a COMMENT -- corrupts the parse and can swallow the next
line. (Real incident: a Chinese comment in scan_workshop.ps1 made `$WS = ...`
disappear, so the script ran with a null path.)

Usage:  python verify_ps1_ascii.py [dir]     (default: this script's own folder)
Exit 0 = all clean. Exit 1 = offenders listed.
"""
import io, os, sys
sys.stdout.reconfigure(encoding="utf-8")

d = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
bad = []
for name in sorted(os.listdir(d)):
    if not name.lower().endswith(".ps1"):
        continue
    p = os.path.join(d, name)
    raw = io.open(p, "rb").read()
    off = [(i, b) for i, b in enumerate(raw) if b > 127]
    if off:
        bad.append((name, len(off), off[0][0]))

if not bad:
    n = len([f for f in os.listdir(d) if f.lower().endswith(".ps1")])
    print('{"ok": true, "checked": %d, "note": "all .ps1 are pure ASCII"}' % n)
    sys.exit(0)
print('{"ok": false, "offenders": %s}' % str([{"file": b[0], "nonAsciiBytes": b[1], "firstAt": b[2]} for b in bad]))
sys.exit(1)
