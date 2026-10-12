#!/usr/bin/env python3
"""PICK THE FRAME — the brief chooses it, not taste (the owner, 2026-09-09:
"it's about what the actual image calls for based on the brief that we have.
From that point forward, we need to select the best frame possible to carry
out the idea that we have").

    python3 pick_frame.py --brand brand-b --month 2026-09
    python3 pick_frame.py --direction "close on his neck and jaw"

Every picture slot in a month's briefs carries a direction. This reads the
creator library's own records — `tools/video-teardown/records/creators/
<creator>/delivered/index.jsonl`, one row per clip with its recorded setting,
action and shot — and scores each clip against that direction. It never
invents a scene: it names the clip that already shows it, or says the library
has nothing for it, which is an honest gap for a human to fill.

Scoring, in order of weight:
  framing   the direction's own words for distance (extreme close-up, close,
            medium, insert on hands) against the clip's recorded shot
  action    what is happening — the device at the face, cleanser, a towel,
            the tap running, the charging case, talking to camera
  setting   where — the sink, the doorway, a plain wall, the mirror
  props     a named product in the direction against the clip's own
Then the frames of the winning clip are listed so the one that carries the
idea can be chosen by eye, at one frame per second with its timecode.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from paths import HERE, WORKSPACE

sys.path.insert(0, str(HERE / "machine"))
import brand_facts as BF             # brand words and a run's own brand, read at run time   # noqa: E402

RECORDS = WORKSPACE / "tools" / "video-teardown" / "records" / "creators"

FRAMING = [
    (r"\bextreme close|fills the frame|macro\b", "extreme close-up", 1),
    (r"\bclose on|close-up|close up|tight on|pressed into|texture visible\b", "close-up", 1),
    (r"\bhands?\b|\binsert\b|\bfingertips?\b|\bon the counter\b|\bsqueez", "insert", 1),
    (r"\bportrait|head and shoulders|talking to camera|to camera\b", "medium close-up", 1),
    (r"\bstanding|over his shoulder|room|shelf|whole\b", "medium", 1),
]
ACTION = {
    r"\bbrush|device|widget\b": ["device", "brush"],
    r"\bcleanser|wash|lather|foam\b": ["cleanser", "lather"],
    r"\btowel|dry|pat\b": ["towel", "dries"],
    r"\bsink|tap|faucet|water|basin\b": ["sink", "basin", "faucet", "water"],
    r"\bcharg|case\b": ["charging", "case"],
    r"\bshelf|cabinet|counter|vanity\b": ["cabinet", "vanity", "sink"],
    r"\bbeard|jaw|neck|bumps|shave|lineup\b": ["jaw", "cheek", "beard"],
    r"\bmirror\b": ["mirror"],
    r"\bhold(s|ing)? .* up|beside his face|shows the\b": ["holds", "beside his face", "up beside"],
    r"\bspeaks|says|talks|direct address|founder\b": ["talks to camera", "speaks to camera", "direct-address"],
}


def clips(creator):
    f = RECORDS / creator / "delivered" / "index.jsonl"
    if not f.is_file():
        sys.exit(f"no delivered library for {creator} at {f}")
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


# A NAMED PRODUCT ON ITS OWN, and BRAND FURNITURE, are the brand's words: the
# product names come from brands/<brand>/products/ (store.json + the product
# files) and the furniture words from brands/<brand>/email-sms/simple.json, at run
# time (machine/brand_facts.py). A product line typed here as a regex was one
# brand's catalogue baked into every brand's routing.
FURNITURE = re.compile(r"footer|nav row|three-tile|banner|trust strip|category nav|"
                       r"social|standing claim|badge|icon|trust mark", re.I)
# things the creator library simply does not contain
NOT_IN_LIBRARY = re.compile(r"screenshot|forum|phone|thread|courtroom|evidence|cookout|practice field|"
                            r"stadium|game|diagram|drawing|illustration|cross-section|chart|"
                            r"wall of|razor and|cartridge razor", re.I)
# a pair or a sequence is two frames, not one - the library can carry it when it
# holds both states (marked skin early, clean face later)
PAIR = re.compile(r"side by side|before and after|two states|three weeks|week one|"
                  r"sequence|progress|panels?\b", re.I)


def route(direction, brand=None):
    """What kind of picture this is, before any frame is considered."""
    d = direction.strip()
    own = BF.furniture(brand) if brand else []
    if FURNITURE.search(d) or any(w in d.lower() for w in own if len(w) > 6):
        return "furniture", "brand furniture - no photograph"
    if brand and BF.product_only(brand).match(d):
        return "storefront", "a named product on its own - use the storefront photograph"
    if NOT_IN_LIBRARY.search(d):
        return "gap", "nothing in the creator library shows this - it needs footage or a designer"
    if PAIR.search(d):
        return "pair", "two frames, not one - an early state and a later one"
    return "frame", "a scene with our man in it - pick a frame"


def score(direction, clip):
    d = direction.lower()
    text = " ".join([clip.get("setting", "")] + clip.get("action", []) + clip.get("shot", [])).lower()
    pts, why = 0, []
    for pat, shot, w in FRAMING:
        if re.search(pat, d):
            if shot in text:
                pts += w; why.append(f"framing {shot} (+{w})")
            elif shot == "insert" and "insert" in text:
                pts += w; why.append(f"framing insert (+{w})")
            break
    hits = 0
    for pat, words in ACTION.items():
        if re.search(pat, d):
            hit = [w for w in words if w in text]
            if hit:
                pts += 2; hits += 1; why.append(f"action “{hit[0]}” (+2)")
    if not hits:                      # nothing the direction asks for happens here
        pts -= 1; why.append("none of the direction's actions happen in this clip (-1)")
    for word in ("sink", "mirror", "doorway", "shelf", "counter", "plain wall", "hoodie"):
        if word in d and word in text:
            pts += 1; why.append(f"setting {word} (+1)")
    return pts, why


def rank(direction, creator, top=3):
    out = []
    for c in clips(creator):
        s, why = score(direction, c)
        out.append((s, c, why))
    out.sort(key=lambda x: -x[0])
    return out[:top]


def frames_of(clip, out_dir, fps=1):
    out_dir.mkdir(parents=True, exist_ok=True)
    src = clip["source"]
    if not Path(src).is_file():
        return []
    for f in out_dir.glob("t*.png"):
        f.unlink()
    subprocess.run(["ffmpeg", "-v", "error", "-i", src, "-vf", f"fps={fps}", "-q:v", "2",
                    str(out_dir / "t%02d.png"), "-y"], check=False)
    return sorted(out_dir.glob("t*.png"))


def directions(brand, month):
    """Every picture slot in the month's briefs, with its slot."""
    import figma_brief as FB
    # this brand's runs, by each run's own run.json — never by a name prefix
    runs = BF.runs_of(brand, HERE / "results", BF.month_abbr(month))
    out = []
    for r in runs:
        for i, b in enumerate(FB.wire_blocks(r, brand)):
            if b["k"] == "P":
                out.append((r.name, i, b["t"]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True, help="brand folder name under brands/ — there is no default brand")
    ap.add_argument("--creator", default="rashad")
    ap.add_argument("--month", default="2026-09")
    ap.add_argument("--direction", default=None)
    ap.add_argument("--extract", default=None, help="clip id: pull its frames at 1fps")
    a = ap.parse_args()

    if a.extract:
        c = next((x for x in clips(a.creator) if x["clip_id"] == a.extract), None)
        if not c:
            sys.exit("no such clip")
        fs = frames_of(c, HERE / "results" / "_frames" / a.extract)
        print(f"{len(fs)} frames -> {HERE / 'results' / '_frames' / a.extract}")
        return

    todo = [("-", 0, a.direction)] if a.direction else directions(a.brand, a.month)
    tally = {}
    for slot, i, d in todo:
        kind, note = route(d, a.brand)
        tally[kind] = tally.get(kind, 0) + 1
        print(f"{slot} #{i}  [{kind.upper()}]")
        print(f"  direction: {d[:110]}")
        if kind != "frame":
            print(f"  {note}\n")
            continue
        if kind == "pair":
            marked = rank("close on his jaw and neck, razor bumps", a.creator, 1)
            clean = rank("presents the clean face to camera", a.creator, 1)
            print(f"  -> before: {marked[0][1]['clip_id']}  {marked[0][1]['action'][0][:52]}")
            print(f"  -> after : {clean[0][1]['clip_id']}  {clean[0][1]['action'][0][:52]}\n")
            continue
        best = rank(d, a.creator)
        if not best or best[0][0] < 2:
            print("  no clip in the library carries this - gap\n")
            continue
        for s, c, why in best:
            print(f"  {'->' if c is best[0][1] else '  '} {s:4.1f}  {c['clip_id']}  {c['action'][0][:56]}")
            if c is best[0][1]:
                print(f"        because: {'; '.join(why[:4])}")
        print()
    print("routing:", ", ".join(f"{k} {v}" for k, v in sorted(tally.items())))


if __name__ == "__main__":
    main()
