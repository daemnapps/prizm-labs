#!/usr/bin/env python3
"""One folder per email: the text, and the actual images.

    python3 calendar/build_email_folders.py --brand brand-b [--out <dir>]

The indexed sends carry image URLs. A URL is not a picture — you cannot look at
an email through a link list, and the images ARE the design. This downloads
them and lays each send out as something a person can open:

    2026-06-29--re-giannis-traded-to-the-heat/
        email.md          the copy, with every block in order
        meta.json         subject, preview, from, date, audience, campaign id
        images/01-....jpeg   numbered in the order they appear in the email

Images are downloaded once and reused, so 3,617 references cost 832 downloads.

Media never enters git (workspace rule 3) — this writes to the Drive mirror by
default, which is where lab content lives.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paths import WORKSPACE  # noqa: E402
import drive_reach as DR  # noqa: E402
BRAND_ROOT = WORKSPACE / "brands"

HERE = Path(__file__).resolve().parent


# The default --out is a folder on the Drive mount: this writes thousands of
# files, a mirror for people, so it never goes through the API (SI-38 (email
# Drive reach)). No mount -> no default; --out names one.
_SA = DR.mount()
DRIVE = (_SA / "lab/email-production/emails-sent") if _SA is not None else None

IMG = re.compile(r"\[IMAGE(.*?)\]\s+(https?://\S+)")


def fetch(url, dest, tries=3):
    for a in range(tries):
        r = subprocess.run(["curl", "-sSL", "--max-time", "45",
                            "-A", "Mozilla/5.0", url, "-o", str(dest)],
                           capture_output=True, text=True)
        if r.returncode == 0 and dest.is_file() and dest.stat().st_size > 100:
            return True
        time.sleep(1 + a)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    src = BRAND_ROOT / args.brand / "email-sms" / "sends"
    out = Path(args.out) if args.out else DRIVE
    if out is None:
        sys.exit("no Shared Assets Drive mount on this machine — pass --out <folder>")
    if not out.parent.exists():
        sys.exit(f"Drive not mounted — {out.parent} is not there")
    out.mkdir(parents=True, exist_ok=True)
    pool = HERE / f".{args.brand}-image-pool"
    pool.mkdir(exist_ok=True)

    files = sorted(f for f in glob.glob(str(src / "*.md")) if "README" not in f)
    if args.limit:
        files = files[:args.limit]
    index = {x["file"]: x for x in json.loads((src / "index.json").read_text())}

    # one pass to collect every distinct URL, so a picture used in 269 emails
    # is fetched once
    all_urls = []
    for f in files:
        all_urls += [u for _, u in IMG.findall(Path(f).read_text())]
    uniq = list(dict.fromkeys(all_urls))
    print(f"{len(files)} emails · {len(all_urls):,} image references · {len(uniq)} distinct")

    cache, failed = {}, []
    for i, u in enumerate(uniq, 1):
        ext = re.sub(r"[?#].*$", "", u).rsplit(".", 1)[-1].lower()
        ext = ext if ext in ("jpg", "jpeg", "png", "gif", "webp") else "jpg"
        key = hashlib.sha1(u.encode()).hexdigest()[:16]
        dest = pool / f"{key}.{ext}"
        if dest.is_file() or fetch(u, dest):
            cache[u] = dest
        else:
            failed.append(u)
        if i % 100 == 0:
            print(f"  fetched {i}/{len(uniq)} · {len(failed)} failed")

    made = 0
    for f in files:
        p = Path(f)
        text = p.read_text()
        folder = out / p.stem
        (folder / "images").mkdir(parents=True, exist_ok=True)
        seen, n = {}, 0
        def place(m):
            nonlocal n
            alt, url = m.group(1).strip(), m.group(2)
            if url not in cache:
                return f"[IMAGE MISSING] {alt} {url}".replace("  ", " ")
            if url not in seen:
                n += 1
                name = f"{n:02d}-{cache[url].name}"
                shutil.copyfile(cache[url], folder / "images" / name)
                seen[url] = name
            return f"[IMAGE {seen[url]}]" + (f" {alt}" if alt else "")
        body = IMG.sub(place, text)
        (folder / "email.md").write_text(body)
        meta = dict(index.get(p.name, {}))
        meta["images"] = len(seen)
        meta["source_file"] = p.name
        (folder / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
        made += 1
        if made % 50 == 0:
            print(f"  built {made}/{len(files)} folders")

    print(f"\n{made} folders -> {out}")
    if failed:
        print(f"{len(failed)} images could not be fetched")
        (pool / "failed.txt").write_text("\n".join(failed))
    print(f"pool: {sum(f.stat().st_size for f in pool.iterdir() if f.is_file())/1e6:.0f} MB")


if __name__ == "__main__":
    main()
