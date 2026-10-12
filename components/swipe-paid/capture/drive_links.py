#!/usr/bin/env python3
"""Turn synced Drive paths into Drive links.

    python3 drive_links.py <brand>

Google Drive for desktop stamps every synced file and folder with its Drive id
in the xattr `com.google.drivefs.item-id#S`. Read it and a link falls out — no
API call, no auth. A file that has not finished uploading has no id yet, which
is also how you tell the sync is still running.

Every run ends in links, never paths.
"""
import os, subprocess, sys
from pathlib import Path

# The DRIVE mirror is the paid swipe home, found through swipe_home — one
# definition for both pools (SI-47 (swipe switch)). Links already handed out
# keep the path they were written with.
for _r in Path(__file__).resolve().parents:
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402

DRIVE = str(swipe_home.root("paid"))

def link(path):
    if not os.path.exists(path):
        return None
    out = subprocess.run(["xattr", "-p", "com.google.drivefs.item-id#S", path],
                         capture_output=True, text=True).stdout.strip()
    if not out:
        return None
    kind = "drive/folders" if os.path.isdir(path) else "file/d"
    return (f"https://drive.google.com/drive/folders/{out}" if os.path.isdir(path)
            else f"https://drive.google.com/file/d/{out}/view")

def report(brand):
    root = os.path.join(DRIVE, brand)
    rows = [("The whole swipe library (every brand)", DRIVE),
            (f"{brand} — everything", root),
            ("  angles (creatives by copy block)", os.path.join(root, "angles")),
            ("  _pages (their whole funnel)", os.path.join(root, "_pages")),
            ("  teardown.html", os.path.join(root, "teardown.html")),
            ("  teardown.md", os.path.join(root, "teardown.md"))]
    angles = os.path.join(root, "angles")
    for a in sorted(os.listdir(angles)) if os.path.isdir(angles) else []:
        if os.path.isdir(os.path.join(angles, a)):
            rows.append(("    " + a, os.path.join(angles, a)))
    pending = 0
    for label, p in rows:
        u = link(p)
        pending += u is None
        print(f"{label:56}  {u or 'still uploading'}")
    if pending:
        print(f"\n{pending} not synced yet — re-run when Drive has caught up.")
    return rows

if __name__ == "__main__":
    if len(sys.argv) < 2: sys.exit(__doc__)
    report(sys.argv[1])
