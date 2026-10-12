#!/usr/bin/env python3
"""Bring every brand's swipe folder to the one standard shape.

    python3 standardize.py

Only ever adds or corrects pointers; never deletes and never rewrites a
hand-written teardown. Idempotent.

  - `**Drive:**` lines in old records keep their lab path, with the retired
    `swipe/` prefix corrected and `angles/` renamed to `blocks/` (2026-09-21);
    a new `_BRAND.md` names the paid swipe home, found through swipe_home
  - pages.json exists (rebuilt from _pages/*.md where a brand never had one)
  - _BRAND.md exists, counts read off blocks.json
  - _raw/ holds the advertiser sweep (copied from the older research folder
    where it was never brought over)
"""
import collections, glob, json, os, re, shutil, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
for _r in Path(HERE).parents:          # the swipe home, one definition for both pools
    if (_r / "components" / "swipe-paid" / "swipe_home.py").is_file():
        sys.path.append(str(_r / "components" / "swipe-paid"))
        break
import swipe_home  # noqa: E402
OLD_RAW = os.path.join(HERE, "capture", "raw")   # the sweep cache, in-component since 2026-09-23
BRANDS = {  # domain, swept, credits — as pulled
    "competitor-a": ("competitor-a.example", "2026-08-19, refreshed 2026-09-21", "__"),
    "brand-c": ("brand-c.shop", "2026-08-31", ""),
    "competitor-b": ("competitor-b.example", "2026-08-20", ""),
    "competitor-c": ("competitor-c.example", "2026-08-20", "__"),
    "competitor-d": ("competitor-d.example", "2026-09-11", ""),
    "competitor-e": ("competitor-e.example", "", ""),
    "competitor-f": ("competitor-f.example", "2026-09-19", ""),
    "competitor-g": ("competitor-g.example", "2026-09-19", "__"),
    "competitor-h": ("competitor-h.example", "2026-09-20", "__"),
    "competitor-i": ("competitor-i.example", "2026-09-23 (US, live 14+ days)", "__"),
}


def fix_drive_lines(b):
    n = 0
    for p in glob.glob(f"{HERE}/{b}/**/*.md", recursive=True):
        s = open(p).read()
        t = s.replace("the shared drive/swipe/", "the shared drive/swipe-paid/")
        t = re.sub(r"(swipe-paid/%s/)angles/" % b, r"\1blocks/", t)
        if t != s:
            open(p, "w").write(t); n += 1
    return n


def pages_json(b):
    path = f"{HERE}/{b}/pages.json"
    if os.path.exists(path):
        return False
    out = {}
    for p in sorted(glob.glob(f"{HERE}/{b}/_pages/*.md")):
        s = open(p).read()
        g = lambda k: (re.search(rf"\*\*{k}:\*\*\s*(.+?)\s*$", s, re.M) or [None, ""])[1]
        h = re.sub(r"[^\d]", "", g("Page height").replace("px", ""))
        out[os.path.basename(p)[:-3]] = {
            "height": int(h) if h else None,
            "type": (g("Type") or "").replace("_pending capture_", "unknown") or "unknown",
            "url": g("URL")}
    json.dump(out, open(path, "w"), indent=1)
    return len(out)


def raw(b):
    have = f"{HERE}/{b}/_raw"
    dom = re.sub(r"[^a-z0-9]+", "-", BRANDS[b][0]) if b != "brand-c" else "brand-c-shop"
    if glob.glob(f"{have}/advertiser_*"):
        return 0
    os.makedirs(have, exist_ok=True)
    n = 0
    for f in glob.glob(f"{OLD_RAW}/advertiser_{dom}_*"):
        shutil.copy2(f, have); n += 1
    return n


def brand_md(b):
    path = f"{HERE}/{b}/_BRAND.md"
    if os.path.exists(path):
        return False
    d = json.load(open(f"{HERE}/{b}/blocks.json"))
    bl = d["blocks"]
    pj = json.load(open(f"{HERE}/{b}/pages.json")) if os.path.exists(f"{HERE}/{b}/pages.json") else {}
    types = collections.Counter(v.get("type") or "unknown" for v in pj.values())
    dom, swept, cred = BRANDS[b]
    open(path, "w").write(
        f"# {b}\n\n**Domain:** `{dom}`  \n**Swept:** {swept}  \n"
        f"**Source:** AdPlexity Social API `/search/ads` · `search_mode=advertiser.lp_url_redirect_outbound`, `meta_grouping_id=2`  \n"
        f"**Credits:** {cred or 'not recorded'}  \n"
        f"**Drive:** `{swipe_home.label('paid', b)}/`\n\n## Counts\n\n| | |\n|---|---|\n"
        f"| Creatives | **{d['creatives']}** |\n| Distinct copy blocks | **{len(bl)}** |\n"
        f"| Video / static | **{d['video']} / {d['image']}** |\n"
        f"| Landing pages | **{len(pj)}**" + (" — " + ", ".join(f"{n} {t}" for t, n in types.most_common()) if pj else "") + " |\n\n"
        f"The read on what they sell, their offer and their stack is in `teardown.md`.\n")
    return True


def check():
    need = ["_BRAND.md", "PROFILE.md", "teardown.md", "teardown.html", "teardown-content.json",
            "blocks.json", "pages.json", "_raw", "blocks", "_pages"]
    print("brand".ljust(14) + "".join(n.replace("teardown", "td")[:10].ljust(11) for n in need))
    bad = 0
    for b in BRANDS:
        row = ""
        for n in need:
            ok = os.path.exists(f"{HERE}/{b}/{n}")
            bad += not ok
            row += ("ok" if ok else "MISSING").ljust(11)
        print(b.ljust(14) + row)
    print("\nall present" if not bad else f"\n{bad} missing")


if __name__ == "__main__":
    if "check" in __import__("sys").argv:
        check(); raise SystemExit
    for b in BRANDS:
        print(f"{b:14} drive-lines fixed in {fix_drive_lines(b):>3} files · pages.json {pages_json(b) or 'ok'} · "
              f"_raw +{raw(b)} · _BRAND.md {'made' if brand_md(b) else 'ok'}")
