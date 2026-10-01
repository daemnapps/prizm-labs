"""RETIRED 2026-09-12 — THIS FILE RAN ON FAL. DO NOT USE IT.

Damon, 2026-09-12: "Everything should have been done in Higgsfield. How are
you using fal? Stop using fal. We're just using Higgsfield, and we're just
using the models that we've already proven worked."

What this cost: an entire ad. The talking beats were generated on kling3_0
with `sound: "off"` and no audio attached, so eighteen shots came back with a
mouth moving to nothing. This file's own header said Kling was RETIRED and it
was used anyway, because nothing recorded which model made a clip.

The replacement is `prompt.py` and `THE-CINEMA-LINE.md` — Higgsfield only,
`cinematic_studio_3_0` with the line IN the prompt and `generate_audio` true,
then `voice_change` onto the cast member's voice element.

(Corrected 2026-09-14. This header used to name `higgs.py`, which has never
existed in this repo, and seedance with an audio reference, which the Cinema
line then ruled out. A dead pointer sends the next session looking for a file
that isn't there and inventing one.)

Kept, not deleted, because it is the record of how the wrong thing happened.
Nothing imports it. Nothing should.
"""

#!/usr/bin/env python3
"""Stage 4c — generate everything the piece hears that is not a spoken line.

    python3 sound.py --plan sound-plan.md --out sounds/
    python3 sound.py --plan sound-plan.md --out sounds/ --dry-run

Reads the sound plan (stage 4b) and produces:

  * the BED — one music track under the piece, or
  * the SONG — when the piece is sung, the script IS the lyrics and the
    song carries the vocal; a sung piece never also gets a bed
  * the EFFECTS — one file per row of the plan's table
  * ROOM TONE — one file per location

Everything runs on the company account through one door (Damon's ruling
2026-09-02: one place things get produced). Effects marked CHECK in the
plan are skipped by default — a clip generated with audio already carries
most on-camera sound, and generating over it doubles the sound.
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# the key vault the machines share (~/.daemn/keys.env)
sys.path.insert(0, str(Path.home() / "Projects/ai-workspace/components/video-teardown/machine"))
import keys

# One roof. Music/song and effects both answer on the same account.
SONG = "https://queue.fal.run/fal-ai/ace-step"
# EFFECTS ENGINE. ElevenLabs sound-effects on fal is BROKEN as of
# 2026-09-02 and cannot be used: the job completes, then the result 422s
# because fal sends a retired model_id upstream ('eleven_text_to_sound_v0')
# and ignores the model_id you pass. Proven twice. stable-audio answers the
# same brief and works, so it holds the slot until fal fixes theirs.
SFX = "https://queue.fal.run/fal-ai/stable-audio"
BED_MODEL = "lyria-3-clip-preview"      # instrumental beds, on the same key
GEM = "https://generativelanguage.googleapis.com"


def fal(url, data=None, key=None):
    r = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=600) as resp:
        return json.loads(resp.read() or b"{}")


def fal_wait(job, key):
    while True:
        st = fal(job["status_url"] + "?logs=0", key=key)
        if st.get("status") in ("COMPLETED", "FAILED", "ERROR"):
            return fal(job["response_url"], key=key), st.get("status")
        time.sleep(4)


def section(md, title):
    m = re.search(rf"##\s*{title}\s*\n(.+?)(?=\n##|\Z)", md, re.S | re.I)
    return m.group(1).strip() if m else ""


def parse_plan(md):
    """Everything the generator needs, straight out of the plan."""
    sung = bool(re.search(r"^\s*`?SUNG`?\s*$", section(md, "IS THIS PIECE SUNG\\?"),
                          re.M | re.I))
    bed = section(md, "THE BED")
    no_bed = bed.upper().startswith("NO BED")
    brief = ""
    m = re.search(r"\*\*The brief[^*]*\*\*\s*[—-]?\s*(.+)", bed)
    if m:
        brief = m.group(1).strip()
    # a sung piece: lyrics + tags
    lyrics = tags = ""
    if sung:
        s = section(md, "IS THIS PIECE SUNG\\?")
        lm = re.search(r"\[verse\].*", s, re.S | re.I)
        if lm:
            lyrics = lm.group(0).strip()
        tm = re.search(r"\*\*The style tags\*\*\s*[—-]?\s*(.+)", s)
        if tm:
            tags = tm.group(1).strip()
    # effects table
    fx = []
    for line in section(md, "THE EFFECTS").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0] and not set(cells[0]) <= set("-: ") \
                and not cells[0].lower().startswith("scene"):
            fx.append({"scene": cells[0], "at": cells[1],
                       "desc": cells[2], "length": cells[3]})
    tone = [l.strip("- ").strip() for l in section(md, "ROOM TONE").splitlines()
            if l.strip() and not l.strip().startswith("#")]
    return {"sung": sung, "no_bed": no_bed, "bed_brief": brief,
            "lyrics": lyrics, "tags": tags, "effects": fx, "room_tone": tone}


def make_bed(brief, dest, gkey):
    body = {"contents": [{"parts": [{"text": brief}]}]}
    req = urllib.request.Request(
        f"{GEM}/v1beta/models/{BED_MODEL}:generateContent?key={gkey}",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    import base64
    with urllib.request.urlopen(req, timeout=400) as r:
        d = json.load(r)
    for p in d["candidates"][0]["content"]["parts"]:
        blob = p.get("inlineData") or p.get("inline_data")
        if blob:
            dest.write_bytes(base64.b64decode(blob["data"]))
            return dest
        # Lyria also returns a timed lyric sheet when lyrics were given —
        # keep it, because it is what the edit syncs to.
        if p.get("text"):
            dest.with_suffix(".timing.txt").write_text(p["text"])
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--include-check", action="store_true",
                    help="also generate effects the plan marked CHECK "
                         "(default: skip — the clip probably carries them)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    plan = parse_plan(Path(a.plan).read_text())
    out = Path(a.out)
    todo = []
    if plan["sung"]:
        todo.append(("song", "the song — carries its own vocal, so no bed and "
                             "no separate voice for these lines"))
    elif plan["no_bed"]:
        print("  no bed — the plan says so on purpose")
    elif plan["bed_brief"]:
        todo.append(("bed", plan["bed_brief"][:70]))
    skipped = [f for f in plan["effects"]
               if "CHECK" in f["length"].upper() and not a.include_check]
    fx = [f for f in plan["effects"] if f not in skipped]
    for f in fx:
        todo.append((f"fx · {f['scene']}", f["desc"][:70]))
    for t in plan["room_tone"]:
        todo.append(("room tone", t[:70]))

    print(f"{'SUNG' if plan['sung'] else 'SPOKEN'} piece · "
          f"{len(fx)} effect(s) · {len(plan['room_tone'])} room tone(s)"
          + (f" · {len(skipped)} marked CHECK, held" if skipped else ""))
    for k, d in todo:
        print(f"  {k:<16} {d}")
    if a.dry_run:
        print("(dry run — nothing called, nothing written)")
        return 0

    fkey = keys.get("FAL_KEY")
    gkey = keys.get("GEMINI_API_KEY")
    if not fkey:
        sys.exit("no FAL_KEY — the company key belongs in ~/.daemn/keys.env")
    out.mkdir(parents=True, exist_ok=True)
    made = 0

    if plan["sung"] and plan["lyrics"]:
        job = fal(SONG, {"tags": plan["tags"] or "warm, bright, uplifting",
                         "lyrics": plan["lyrics"], "duration": 30}, fkey)
        res, st = fal_wait(job, fkey)
        url = (res.get("audio") or {}).get("url")
        if url:
            urllib.request.urlretrieve(url, out / "song.mp3")
            made += 1
            print("  song.mp3")
    elif plan["bed_brief"] and gkey:
        if make_bed(plan["bed_brief"], out / "bed.mp3", gkey):
            made += 1
            print("  bed.mp3")

    def effect(text, dest, seconds=6):
        """One sound. A failure here loses one effect, never the run —
        a piece missing one door click still assembles."""
        try:
            res, _ = fal_wait(fal(SFX, {"prompt": text,
                                        "seconds_total": seconds}, fkey), fkey)
            blob = res.get("audio_file") or res.get("audio") or {}
            url = blob.get("url") if isinstance(blob, dict) else None
            if not url:
                print(f"  {dest.name} — nothing came back"); return 0
            urllib.request.urlretrieve(url, dest)
            print(f"  {dest.name}")
            return 1
        except Exception as e:
            print(f"  {dest.name} — failed ({str(e)[:60]})")
            return 0

    for i, f in enumerate(fx, 1):
        name = re.sub(r"[^a-z0-9]+", "-", f["scene"].lower()).strip("-")
        secs = 6
        m = re.search(r"(\d+)\s*s", f["length"])
        if m:
            secs = max(2, min(int(m.group(1)), 30))
        made += effect(f["desc"], out / f"fx-{i:02d}-{name}.wav", secs)

    for i, t in enumerate(plan["room_tone"], 1):
        made += effect(t, out / f"tone-{i:02d}.wav", 20)

    print(f"\n{made} audio file(s) in {out}")
    if skipped:
        print(f"{len(skipped)} effect(s) held as CHECK — the clips likely carry "
              "them; --include-check generates them anyway")


if __name__ == "__main__":
    sys.exit(main() or 0)
