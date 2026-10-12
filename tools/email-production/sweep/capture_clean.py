#!/usr/bin/env python3
"""Every clean rebuild as a picture — for the side-by-side contact sheets."""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent.parent
CH = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
import os as _os
root = Path(_os.environ["FORMAT_BANK_DIR"]).resolve() if _os.environ.get("FORMAT_BANK_DIR") else HERE / "results" / "format-bank"
URLBASE = f"/results/{root.name}"
boards = sys.argv[1:] or sorted(p.name for p in root.iterdir() if p.is_dir())
for b in boards:
    d = root / b
    rects = json.loads((d / "rects.json").read_text()) if (d / "rects.json").is_file() else []
    for f in sorted(d.glob("[0-9][0-9]-clean.html")):
        png = d / (f.stem + ".png")
        if png.is_file() and png.stat().st_mtime > f.stat().st_mtime:
            continue
        i = int(f.stem[:2])
        # width from the html itself
        html = f.read_text()
        import re
        m = re.search(r'<table role="presentation" width="(\d+)"', html)
        w = int(m.group(1)) if m else 600
        subprocess.run([CH, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=5000",
                        f"--window-size={w},6500", f"--screenshot={png}",
                        f"http://localhost:8785{URLBASE}/{b}/{f.name}"], capture_output=True)
    print(b, "done", flush=True)
