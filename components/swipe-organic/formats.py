#!/usr/bin/env python3
"""Read every swiped video's frames and write its format handoff.

One pass per post: look at the contact sheet, name the FORMAT from
formats.json (or propose a new one), write the beats with the real
timestamps, read the on-screen text off the frames, and fill the
Higgsfield kit for that post's actual structure. Brand-neutral — the
brand enters later, per workspace rule 7.

    python3 formats.py [--lane swipe] [--limit 20] [--workers 4] [--redo]

Per post, in records/swipe-videos/<code>/:
    sheet.jpg      the six beats in one strip (what the model reads)
    format.json    format id, confidence, beats, on-screen text, kit
    handoff.md     the page a maker actually receives
"""
import argparse, json, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import desklib as D

HERE = Path(__file__).resolve().parent
SAVES = HERE / "records/damon-saves"
VID = HERE / "records/swipe-videos"
LIB = HERE / "formats.json"

def sheet(d):
    out = d / "sheet.jpg"
    if not out.exists():
        subprocess.run(["ffmpeg", "-y", "-v", "quiet", "-i", str(d / "strip/%02d.jpg"),
                        "-vf", "scale=300:-1,tile=6x1", str(out)], capture_output=True, timeout=120)
    return out if out.exists() else None

def one(row, redo=False):
    code = re.search(r"/(p|reel|reels)/([A-Za-z0-9_-]+)", row["url"]).group(2)
    d = VID / code
    if not (d / "meta.json").exists():
        return code, "novideo"
    if (d / "handoff.md").exists() and not redo:
        return code, "have"
    s = sheet(d)
    if not s:
        return code, "nosheet"
    meta = json.loads((d / "meta.json").read_text())
    lib = json.loads(LIB.read_text())
    names = ", ".join(f'{f["id"]} ({f["name"]})' for f in lib["formats"])
    # what other passes have already proposed — a shared vocabulary, so names
    # converge on structures instead of one bespoke name per video
    seen = {}
    for p in VID.glob("*/format.json"):
        try:
            j = json.loads(p.read_text())
        except Exception:
            continue
        fid = j.get("format_id", "")
        if fid.startswith("new:"):
            seen[fid] = seen.get(fid, 0) + 1
    proposed = ", ".join(f"{k} (x{v})" for k, v in sorted(seen.items(), key=lambda kv: -kv[1])[:40])
    prompt = f"""Read one swiped video's structure and write its production handoff. Work only from evidence — the frames and the caption. This is for a maker who will rebuild this STRUCTURE for a different brand, so the structure has to be right and honest.

The contact sheet (6 stills across the runtime — beats at {meta['beats']} seconds of a {meta['duration']}s video): {s}
Read that image first. Look at what is actually in each frame: the subject, the room, the light, the camera position, whether it moves, and the exact on-screen text.

The post: {row['url']} by {row.get('author')} — {row.get('views'):,} views, {row.get('likes') or 0:,} likes.
Its caption, verbatim: {json.dumps(row.get('caption') or '')}

The format library is at {LIB}. Read it. The formats are: {names}

Already proposed by earlier passes over other videos — REUSE one of these ids verbatim if this video has the same structure, rather than coining another name for the same thing: {proposed or "(nothing yet)"}

Naming rules, because a library only works if names repeat:
- A format is the STRUCTURE — camera behaviour, text behaviour, beat order, and what carries the persuasion. It is never the topic, the product, the room or the person.
- Prefer a library id. Take it if the structure matches even when the subject is completely different: a scalp treatment and a countertop demo can be the same format.
- Only coin `new:` when the structure genuinely differs from every library id AND every id listed above, and say in `why` which one it was closest to and what made it different.
- A coined name is 2-4 generic words about the mechanic (`new:locked-frame-escalating-caption`), never about content (`new:lemur-parable`, `new:herb-scrub-demo` — both wrong).

Write {d}/format.json — exactly this shape, no extra keys:
{{"code": "{code}", "format_id": "<one id from the library, or new:<kebab-name> if none fits>",
 "confidence": "high|medium|low", "why": "<one sentence: the structural evidence that decided it>",
 "onscreen_text": ["<the exact words in each frame that has text, in order; [] if none>"],
 "beats": [{{"t": <seconds>, "shot": "<what the camera sees>", "text": "<on-screen text at that moment or null>"}}],
 "carries_the_value": "<the one thing doing the persuading: the debris, the glow, the collection, the unfinished sentence…>",
 "replicable_without_talent": true|false,
 "higgsfield": {{"image": "<a full image prompt for the single most important beat — framing, subject, wardrobe, room, light, camera look; leave {{PRODUCT}} and {{SUBJECT}} as literal placeholders, nothing invented>",
   "motion": "<the camera behaviour for that beat, one sentence>",
   "text_overlay": "<the on-screen text pattern to reuse, with {{}} slots>"}}}}

Then write {d}/handoff.md — what a maker receives. Markdown, no preamble, in this order:
# {{Format name}} — rebuild sheet
one line on what this video is and its numbers · then **Why it works** (2 sentences, the mechanic) · **The beats** (a table: time, what happens, on-screen text) · **What carries the value** · **Shoot it** (camera, light, wardrobe rules — a person could shoot this with a phone) · **Or generate it** (the Higgsfield image prompt in a fenced block, the motion note, the text-overlay pattern) · **Reference:** the source url.
Say plainly wherever the frames do not show something — never fill a gap with an invention.

Do not modify any file outside {d}/."""
    r = subprocess.run(["claude", "-p", prompt, "--allowedTools", "Read", "Write"],
                       capture_output=True, text=True, timeout=900,
                       cwd=str(D.WS))
    ok = (d / "handoff.md").exists() and (d / "format.json").exists()
    if not ok:
        (d / "format.log").write_text((r.stdout or "")[-600:] + "\n--\n" + (r.stderr or "")[-600:])
    return code, "done" if ok else "failed"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lane", default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--redo", action="store_true")
    a = ap.parse_args()
    rows = json.loads((SAVES / "catalog.json").read_text())["rows"]
    if a.lane:
        rows = [r for r in rows if r.get("lane") == a.lane]
    rows = [r for r in rows if r.get("views")]
    rows.sort(key=lambda r: (r.get("views") or 0) + (r.get("likes") or 0) * 10, reverse=True)
    if a.limit:
        rows = rows[:a.limit]
    tally = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, (code, st) in enumerate(ex.map(lambda r: one(r, a.redo), rows), 1):
            tally[st] = tally.get(st, 0) + 1
            print(f"[{i}/{len(rows)}] {code} {st}", flush=True)
    print("done:", tally, flush=True)

if __name__ == "__main__":
    main()
