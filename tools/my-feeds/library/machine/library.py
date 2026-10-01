#!/usr/bin/env python3
"""The My Feeds library — one front door to everything that has been swiped,
written where the team already looks.

    python3 library.py                # writes the Drive index + every feed's FEED.md, and the public page
    python3 library.py --dry-run      # counts only, writes nothing

What exists, and where it goes:

  ORGANIC FORMATS   the structures pulled out of posts that worked      → public pack (tools/my-feeds/organic) — brand-free
  SWIPE VIDEOS      every post torn down, filed under its format        → Drive, one folder per post, video inside
  MY FEEDS          one feed per sub-avatar: what that person watches   → Drive, one FEED.md per feed + the records
  PAID SWEEPS       every competitor's live ads, blocked by angle       → Drive (media) + public pack (tools/my-feeds/paid) — brand-free
  SAVES             what the owner saved by hand                         → Drive, inside the feeds as its own feed

The index is `SWIPE LIBRARY.md` at the root of the shared drive. The words in
it are read by Higgsfield Supercomputer (the team's front) and by people.
Nothing private leaves Drive: the public page carries formats, angle shapes
and counts only — no brand, no creator, no competitor.

Brand-agnostic: brands, sub-avatars and competitors are read from the
folders, never named here. `AI_WORKSPACE` and `DRIVE_ACCOUNT` pick the two
planes; unset, `~/Projects/ai-workspace` and the first Drive mount are used.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
WS = Path(os.environ.get("AI_WORKSPACE", Path.home() / "Projects/ai-workspace"))
ORG = WS / "lab/damon/swipe-organic"
PAID = WS / "lab/damon/swipe-paid"


def drive_root() -> Path:
    cs = Path.home() / "Library/CloudStorage"
    acct = os.environ.get("DRIVE_ACCOUNT")
    if acct:
        return cs / f"GoogleDrive-{acct}"
    return next(iter(sorted(cs.glob("GoogleDrive-*"))), cs / "GoogleDrive")


SA = drive_root() / "Shared drives/Shared Assets"
FEEDS_DRIVE = SA / "lab/damon/swipe-organic/records/avatar-feeds"
VIDEOS_DRIVE = SA / "lab/damon/swipe-organic/records/swipe-videos"
PAID_DRIVE = SA / "lab/damon/swipe-paid"
INDEX = SA / "SWIPE LIBRARY.md"


def jload(p: Path, default):
    try:
        return json.loads(p.read_text())
    except Exception:
        return default


# ── organic formats and the torn-down videos ───────────────────────────────
def formats() -> dict[str, dict]:
    lib = jload(ORG / "formats.json", {}).get("formats", [])
    return {f["id"]: f for f in lib}


def videos() -> list[dict]:
    out = []
    root = ORG / "records/swipe-videos"
    if not root.is_dir():
        return out
    # formats get merged as the library matures; a post keeps the id it was
    # filed under, and the merge map says what that id is called today
    merges = (jload(ORG / "records/format-merges.json", {}) or {}).get("merged", {})
    known = formats()
    def today(fid: str) -> str:
        fid = merges.get(fid) or merges.get("new:" + fid) or fid
        if fid in known:
            return known[fid].get("name") or fid
        return "one-off · " + fid.replace("new:", "")   # appears once; no library card yet
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        fj = jload(d / "format.json", None)
        meta = jload(d / "meta.json", {}) or {}
        out.append({"code": d.name, "format": today((fj or {}).get("format_id") or (fj or {}).get("format") or ""),
                    "torn": bool(fj) and (d / "handoff.md").is_file(),
                    "author": meta.get("author") or meta.get("username") or "",
                    "views": meta.get("views") or meta.get("play_count") or 0,
                    "url": meta.get("url") or ""})
    return out


# ── the feeds ──────────────────────────────────────────────────────────────
def feeds() -> list[dict]:
    out = []
    root = ORG / "records/avatar-feeds"
    if not root.is_dir():
        return out
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / "items.json").is_file():
            continue
        items = (jload(d / "items.json", {}) or {}).get("items", {})
        if not isinstance(items, dict):
            continue
        plan = jload(d / "plan.json", {}) or {}
        brand, _, sub = d.name.partition("--")
        rows = list(items.values())
        sifted = any(r.get("sift") for r in rows)
        kept = [r for r in rows if (r.get("sift") or {}).get("keep")] if sifted else rows   # saves are kept by definition
        lanes = {}
        for r in kept:
            lane = (r.get("sift") or {}).get("lane") or "unsorted"
            lanes[lane] = lanes.get(lane, 0) + 1
        out.append({"feed": d.name, "brand": brand, "sub": sub, "dir": d, "ask": plan.get("ask") or plan.get("question") or "",
                    "total": len(rows), "kept": len(kept), "lanes": lanes, "rows": kept,
                    "updated": max((r.get("first_seen") or "" for r in rows), default="")[:10]})
    return out


def feed_md(f: dict) -> str:
    L = [f"# Feed — {f['brand']} · {f['sub']}", "",
         f"{f['kept']} posts kept of {f['total']} seen · " + " · ".join(f"{k} {v}" for k, v in sorted(f['lanes'].items())) +
         f" · newest {f['updated']}", ""]
    if f["ask"]:
        L += ["**Whose scroll this is:** " + str(f["ask"]).strip().replace("\n", " ")[:600], ""]
    L += ["What this person watches for free — the posts, not our product. Entertainment first; educational as its own lane. "
          "Open a post, watch it, and if it is worth rebuilding, run it through the video teardown.", "",
          "| Lane | Platform | Author | What it is | Followers | Link |", "|---|---|---|---|---|---|"]
    def key(r):
        return (0 if (r.get("sift") or {}).get("lane") == "entertainment" else 1, -(r.get("followers") or 0))
    for r in sorted(f["rows"], key=key):
        s = r.get("sift") or {}
        what = s.get("what") or ""
        if not what or what == "unread":
            what = r.get("caption") or ""
        what = what.replace("|", "/").replace("\n", " ")[:110]
        L.append(f"| {s.get('lane', '')} | {r.get('platform', '')} | {r.get('author', '')} | {what} | "
                 f"{r.get('followers') or ''} | {r.get('url', '')} |")
    return "\n".join(L) + "\n"


# ── paid sweeps ────────────────────────────────────────────────────────────
def sweeps() -> list[dict]:
    out = []
    for b in sorted(PAID.glob("*/blocks.json")):
        d = jload(b, {}) or {}
        blocks = d.get("blocks", [])
        live = sum(x.get("count", 0) for x in blocks)
        top3 = sum(x.get("count", 0) for x in sorted(blocks, key=lambda x: -x.get("count", 0))[:3])
        out.append({"brand": b.parent.name, "angles": len(blocks), "ads": live,
                    "video": d.get("video", 0), "image": d.get("image", 0),
                    "concentration": round(top3 / live * 100) if live else 0,
                    "on_drive": (PAID_DRIVE / b.parent.name).is_dir()})
    return out


# ── the index ──────────────────────────────────────────────────────────────
def index_md(F, V, FE, SW) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    torn = [v for v in V if v["torn"]]
    by_fmt = {}
    for v in torn:
        by_fmt.setdefault(v["format"], []).append(v)
    L = [f"# MY FEEDS — THE LIBRARY", "",
         f"Everything swiped, in one place. Built {now}; rebuilt whenever the library changes. "
         "Read this in Higgsfield Supercomputer (\"open the library for <brand>\") or by hand.", "",
         "| What | How much | Where |",
         "|---|---|---|",
         f"| **Organic formats** — the structures under posts that worked | {len([k for k in by_fmt if not k.startswith('one-off')])} library formats in use of {len(F)} · {len([k for k in by_fmt if k.startswith('one-off')])} one-offs | "
         "public pack: github.com/daemnapps/prizm-labs → tools/my-feeds/organic |",
         f"| **Swipe videos** — every post torn down, filed under its format | {len(torn)} torn down · {len(V) - len(torn)} waiting | "
         "`lab/damon/swipe-organic/records/swipe-videos/<code>/` — `video.mp4`, `handoff.md` (the rebuild sheet), `sheet.jpg` (the beats) |",
         f"| **My Feeds** — one feed per sub-avatar: what that person actually watches | {len(FE)} feeds · {sum(f['kept'] for f in FE):,} posts kept of {sum(f['total'] for f in FE):,} seen | "
         "`lab/damon/swipe-organic/records/avatar-feeds/<feed>/FEED.md` |",
         f"| **Paid sweeps** — every competitor's live ads, blocked by angle | {len(SW)} brands · {sum(s['ads'] for s in SW):,} ads · {sum(s['angles'] for s in SW)} angles | "
         "`lab/damon/swipe-paid/<brand>/angles/NN_<angle>/` — video, photos, page captures · public pack: tools/my-feeds/paid |",
         "", "## My Feeds", "",
         "A feed is one person's scroll — entertainment first, the educational lane beside it, nothing that sells. "
         "The feed name is `<brand>--<sub-avatar>`. Open the FEED.md; every row links to the post.", "",
         "| Feed | Brand | Kept | Entertainment | Educational | Newest |", "|---|---|---|---|---|---|"]
    for f in FE:
        L.append(f"| `{f['feed']}` | {f['brand']} | {f['kept']} | {f['lanes'].get('entertainment', 0)} | "
                 f"{f['lanes'].get('educational', 0)} | {f['updated']} |")
    L += ["", "## Swipe videos, by format", "",
          "Each code is a folder on this drive with the video, the rebuild sheet and the beat strip. "
          "The format names match the public pack's `formats/` folders.", "",
          "| Format | Torn down | Codes |", "|---|---|---|"]
    for fmt, vs in sorted(by_fmt.items(), key=lambda kv: -len(kv[1])):
        codes = ", ".join(f"`{v['code']}`" for v in vs[:12]) + (f" … +{len(vs) - 12}" if len(vs) > 12 else "")
        L.append(f"| {fmt or '(unfiled)'} | {len(vs)} | {codes} |")
    L += ["", "## Paid sweeps", "",
          "Live ads at the moment of the sweep. `angles/01_…` carries the most creatives — that is the angle the money is on.", "",
          "| Brand swept | Angles | Live ads | Video / image | Top-3 share | Media on this drive |", "|---|---|---|---|---|---|"]
    for s in SW:
        L.append(f"| {s['brand']} | {s['angles']} | {s['ads']:,} | {s['video']} / {s['image']} | {s['concentration']}% | "
                 f"{'yes' if s['on_drive'] else 'not yet'} |")
    L += ["", "## How to use any of it", "",
          "1. Pick a post, a feed row, or an angle folder.",
          "2. Run it through the teardown (tools/video-teardown, or the **Tear down** button on My Feeds) — the structure comes out, your brand goes in.",
          "3. The brief lands in the brand's `briefs/` folder and shows on the queue.", "",
          "Who keeps this current: the library tool in the public repo (`tools/my-feeds/library`), run by the owner. "
          "My Feeds itself (the live board with Pull now / Tear down) runs on the owner's machine; these files are its export.", ""]
    return "\n".join(L)


# ── the public page (formats + angle shapes, brand-free) ───────────────────
def public_page(F, V, SW, FE) -> str:
    torn = [v for v in V if v["torn"]]
    by_fmt = {}
    for v in torn:
        by_fmt.setdefault(v["format"], 0)
        by_fmt[v["format"]] += 1
    pack03 = REPO / "tools/my-feeds/organic/formats"
    pack04 = REPO / "tools/my-feeds/paid/angle-shapes"
    fmts = []
    oneoffs = len([x for x in (pack03 / "one-offs").iterdir() if x.is_dir()]) if (pack03 / "one-offs").is_dir() else 0
    for d in sorted(pack03.iterdir()) if pack03.is_dir() else []:
        if not d.is_dir() or d.name == "one-offs":
            continue
        card = d / "00-THE-FORMAT.md"
        first = ""
        if card.is_file():
            for ln in card.read_text().splitlines():
                if ln.strip() and not ln.startswith("#"):
                    first = ln.strip(); break
        fmts.append((d.name, first, len([p for p in d.iterdir() if p.suffix == ".md" and p.name != "00-THE-FORMAT.md"])))
    shapes = []
    for p in sorted(pack04.glob("*.md")) if pack04.is_dir() else []:
        first = ""
        for ln in p.read_text().splitlines():
            if ln.strip() and not ln.startswith("#"):
                first = ln.strip(); break
        shapes.append((p.stem, first))
    E = html.escape
    fmt_html = "".join(f'<div class="card"><div class="num">{n} REFERENCE{"S" if n != 1 else ""}</div><h3>{E(name.replace("-", " "))}</h3>'
                       f'<p>{E(first[:180])}</p><div class="foot"><a class="mono" href="https://github.com/daemnapps/prizm-labs/tree/main/tools/my-feeds/organic/formats/{E(name)}" target="_blank" rel="noopener">open →</a></div></div>'
                       for name, first, n in fmts)
    shape_html = "".join(f'<div class="card"><h3>{E(name.replace("-", " "))}</h3><p>{E(first[:200])}</p>'
                         f'<div class="foot"><a class="mono" href="https://github.com/daemnapps/prizm-labs/blob/main/tools/my-feeds/paid/angle-shapes/{E(name)}.md" target="_blank" rel="noopener">open →</a></div></div>'
                         for name, first in shapes)
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#EDE0DC">
<meta name="description" content="Every structure we have pulled out of posts and ads that worked — the organic formats and the paid angle shapes — in one place.">
<title>The Library — My Feeds — PRIZM LABS</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jost:wght@200;300;400&family=Archivo:wght@400;500&family=IBM+Plex+Mono:wght@400&display=swap">
<link rel="stylesheet" href="studio.css">
<style>
.hero{{padding-top:120px;display:grid;grid-template-columns:1.1fr .9fr;gap:50px;align-items:end}}
@media(max-width:900px){{.hero{{grid-template-columns:1fr;padding-top:110px}}}}
.hstats{{display:grid;grid-template-columns:1fr 1fr;gap:22px}}
.stat .k{{font-family:var(--display);font-weight:200;font-size:clamp(30px,4vw,44px);line-height:1}}
.stat .v{{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink3);margin-top:6px}}
.card h3{{font-size:16px;text-transform:none;letter-spacing:0;font-weight:400}}
.where{{border:1px solid var(--line);border-radius:14px;padding:26px 28px;background:color-mix(in srgb,var(--halo) 66%,transparent);margin-top:26px}}
.where table{{border-collapse:collapse;width:100%;font-size:13.5px}}
.where td{{padding:10px 14px 10px 0;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink2)}}
.where td:first-child{{font-family:var(--mono);font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink);white-space:nowrap}}
</style>

<nav>
  <a class="mark" href="/">PRIZM LABS</a>
  <span class="sp"></span>
  <a class="link" href="/how-it-works.html">The tools</a>
  <a class="link" href="/swipes/" aria-current="page">Feeds</a>
  <a class="link" href="/onboarding.html">Onboarding</a>
  <a class="link" href="https://github.com/daemnapps/prizm-labs" target="_blank" rel="noopener">Repo</a>
</nav>

<div class="wrap">
  <div class="hero">
    <div>
      <p class="eyebrow">My Feeds · the library</p>
      <h1>What<br>worked.</h1>
      <p class="lede">Every structure we have pulled out of posts and ads that already earned their audience — the organic <b>formats</b> and the paid <b>angle shapes</b>. Pick one, put your brand in, make it.</p>
      <div class="btns">
        <a class="btn" href="https://github.com/daemnapps/prizm-labs/tree/main/tools/my-feeds/organic" target="_blank" rel="noopener">Organic formats — in the repo</a>
        <a class="btn ghost" href="https://github.com/daemnapps/prizm-labs/tree/main/tools/my-feeds/paid" target="_blank" rel="noopener">Paid angle shapes — in the repo</a>
      </div>
      <div class="note">Structures only. No brand, no creator, no competitor is named anywhere in these.</div>
    </div>
    <div class="hstats">
      <div class="stat"><div class="k">{len(fmts)}</div><div class="v">organic formats · +{oneoffs} one-offs</div></div>
      <div class="stat"><div class="k">{len(torn)}</div><div class="v">posts taken apart</div></div>
      <div class="stat"><div class="k">{len(shapes)}</div><div class="v">paid angle shapes</div></div>
      <div class="stat"><div class="k">{sum(s['ads'] for s in SW):,}</div><div class="v">live ads, {len(SW)} markets</div></div>
    </div>
  </div>

  <section id="formats">
    <p class="eyebrow">01 — organic formats</p>
    <h2>The shape under the post</h2>
    <p class="lede">Each format is one proven structure, with every real post it came from taken apart beat by beat — image prompt and motion note included. Copy the structure, not the content.</p>
    <div class="cards">{fmt_html}</div>
  </section>

  <section id="shapes">
    <p class="eyebrow">02 — paid angle shapes</p>
    <h2>The pitch the money is on</h2>
    <p class="lede">An ad still running has survived a test you never had to pay for. These are the pitch structures that recur across {len(SW)} swept markets, as fill-in-the-blank templates.</p>
    <div class="cards">{shape_html}</div>
  </section>

  <section id="where">
    <p class="eyebrow">03 — where the rest lives</p>
    <h2>The library behind the packs</h2>
    <p class="lede">The two packs in the repo are the public half. The full library — the videos themselves, one feed per customer type, every competitor's live ads with media — is a Google Drive the team reads through Higgsfield Supercomputer. If you run these tools for your own brand, yours is built the same way.</p>
    <div class="where"><table>
      <tr><td>Swipe videos</td><td>One folder per post: the video, the rebuild sheet, the beat strip. Filed under its format.</td></tr>
      <tr><td>My Feeds</td><td>One feed per customer type — what that person watches for free. Entertainment first, educational beside it, nothing that sells. {len(FE)} feeds today.</td></tr>
      <tr><td>Paid sweeps</td><td>Every live ad a competitor is running, blocked by angle, ranked by how many creatives sit on it — with the video, the photos and the landing page captured.</td></tr>
      <tr><td>The index</td><td><code>SWIPE LIBRARY.md</code> at the root of the drive — counts, feeds and codes, rebuilt by <code>tools/my-feeds/library</code>.</td></tr>
    </table></div>
  </section>

  <footer>
    <span>PRIZM LABS</span>
    <span><a href="/how-it-works.html">The tools</a> · <a href="/onboarding.html">Onboarding</a> · <a href="https://github.com/daemnapps/prizm-labs" target="_blank" rel="noopener">Repo</a></span>
  </footer>
</div>
</html>
"""


def main():
    dry = "--dry-run" in sys.argv
    F, V, FE, SW = formats(), videos(), feeds(), sweeps()
    print(f"formats {len(F)} · videos {len(V)} ({sum(v['torn'] for v in V)} torn) · feeds {len(FE)} "
          f"({sum(f['kept'] for f in FE):,} kept) · sweeps {len(SW)} ({sum(s['ads'] for s in SW):,} ads)")
    if dry:
        return
    if not SA.is_dir():
        sys.exit(f"Drive not mounted at {SA}")
    # feeds → Drive: the records and a readable FEED.md each
    for f in FE:
        dest = FEEDS_DRIVE / f["feed"]
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "FEED.md").write_text(feed_md(f))
        for name in ("items.json", "plan.json"):
            src = f["dir"] / name
            if src.is_file():
                shutil.copy2(src, dest / name)
    INDEX.write_text(index_md(F, V, FE, SW))
    print(f"wrote Shared Assets/{INDEX.name} and {len(FE)} FEED.md files")
    # The public half is the Swipes page (docs/swipes/, daemn.co/swipes/) —
    # ruled 2026-09-24: one swipe page on the site, not a second one.


if __name__ == "__main__":
    main()
