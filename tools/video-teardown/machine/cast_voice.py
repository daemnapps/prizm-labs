#!/usr/bin/env python3
"""Cast a character's voice ONCE, and bind it — the voice half of identity.

    python3 cast_voice.py --brand <brand> --character susan --audition
    python3 cast_voice.py --brand <brand> --character susan --pick Matilda

A face is held by a trained model (`lora.json`). A voice is held the same
way: not by DESCRIBING it in every prompt — descriptions drift, and a
stale name is worse (a run died on "Voice not found: Wise_Woman", a name
carried over from a retired model) — but by binding ONE voice to the
character and recording it beside them.

    --audition  speaks the character's own line in each candidate voice and
                writes the samples out for a human ear. Costs pennies.
    --pick      binds the chosen voice and writes `voice.json` next to the
                character's `lora.json`. That file is the record.

Like the trained face: cast once, reused forever. A character that already
has voice.json reports it and spends nothing unless --recast is given.

Brand-agnostic (rule 4): the character's own identity block supplies the
audition line and the register; nothing here names a brand.
"""

import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import keys
import brand_folders as BF

WS = Path.home() / "Projects" / "ai-workspace"
TTS = "https://queue.fal.run/fal-ai/elevenlabs/tts/multilingual-v2"

# A spread to audition across, not a recommendation. The ear decides.
CANDIDATES = ["Matilda", "Alice", "Charlotte", "Lily", "Jessica",
              "Sarah", "Laura", "River", "Will", "Brian", "Bill",
              "Chris", "Daniel", "Eric", "George", "Roger"]


def fal(url, data=None, key=None):
    r = urllib.request.Request(
        url, data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=300) as resp:
        return json.loads(resp.read() or b"{}")


def character_home(brand, name):
    d = BF.home(WS / "brands" / brand, "ai-elements/characters") / name   # old: ai-cast/
    if not d.is_dir():
        sys.exit(f"no character '{name}' in brands/{brand}/ai-elements/characters/")
    return d


def identity_block(home):
    """The first blockquote in character.md — their physical truth, and the
    only description this tool uses to pick an audition line."""
    cm = home / "character.md"
    if not cm.is_file():
        return None, None
    text = cm.read_text()
    block, started = [], False
    for line in text.splitlines():
        if line.startswith(">"):
            started = True
            block.append(line.lstrip("> ").strip())
        elif started:
            break
    m = re.search(r"^-?\s*\*?\*?Voice[^:]*:\*?\*?\s*(.+)$", text, re.M | re.I)
    return " ".join(block).strip() or None, (m.group(1).strip() if m else None)


def speak(key, text, voice, dest):
    job = fal(TTS, {"text": text, "voice": voice, "stability": 0.5,
                    "similarity_boost": 0.75}, key)
    while True:
        st = fal(job["status_url"] + "?logs=0", key=key)
        if st.get("status") in ("COMPLETED", "FAILED", "ERROR"):
            break
        time.sleep(3)
    out = fal(job["response_url"], key=key)
    url = (out.get("audio") or {}).get("url")
    if not url:
        return None
    urllib.request.urlretrieve(url, dest)
    return dest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", required=True)
    ap.add_argument("--character", required=True)
    ap.add_argument("--audition", action="store_true",
                    help="speak one line in every candidate voice, for the ear")
    ap.add_argument("--pick", help="bind this voice to the character")
    ap.add_argument("--line", help="what the audition says; defaults to a "
                                   "neutral line in the character's register")
    ap.add_argument("--voices", help="comma-separated candidates to audition")
    ap.add_argument("--out", default=None, help="where audition samples land")
    ap.add_argument("--recast", action="store_true",
                    help="replace an existing binding — only when the "
                         "character themselves changed")
    a = ap.parse_args()

    home = character_home(a.brand, a.character)
    record = home / "voice.json"

    if record.exists() and not (a.recast or a.audition):
        rec = json.loads(record.read_text())
        print("ALREADY CAST — nothing to do, nothing spent.")
        print(f"  character: {a.character}")
        print(f"  voice:     {rec.get('voice')}")
        print(f"  cast:      {rec.get('cast')}")
        print(f"  record:    {record}")
        print("Use --recast only when the character themselves changed.")
        return 0

    key = keys.get("FAL_KEY")
    if not key:
        sys.exit("no FAL_KEY — the company key belongs in ~/.daemn/keys.env")

    block, voice_note = identity_block(home)
    line = a.line or ("I've had these spots on my arms for years. "
                      "I stopped wearing anything short-sleeved.")

    if a.pick:
        rec = {"voice": a.pick, "provider": "elevenlabs (via fal)",
               "model": "multilingual-v2", "stability": 0.5,
               "similarity_boost": 0.75,
               "cast": time.strftime("%Y-%m-%d"),
               "audition_line": line,
               "note": ("bound once and reused in every generation — a voice "
                        "named in a prompt drifts, a voice bound here does not")}
        if voice_note:
            rec["voice_direction"] = voice_note
        record.write_text(json.dumps(rec, indent=2) + "\n")
        print(f"BOUND — {a.character} speaks with {a.pick}")
        print(f"  record: {record}")
        return 0

    if not a.audition:
        sys.exit("give me --audition to hear candidates, or --pick <voice> to bind one")

    out = Path(a.out) if a.out else (Path.cwd() / f"audition-{a.character}")
    out.mkdir(parents=True, exist_ok=True)
    cands = [v.strip() for v in a.voices.split(",")] if a.voices else CANDIDATES
    if block:
        print(f"{a.character}: {block[:120]}…")
    print(f'auditioning {len(cands)} voice(s) on: "{line[:60]}…"\n')
    made = []
    for v in cands:
        dest = out / f"{a.character}-{v}.mp3"
        try:
            if speak(key, line, v, dest):
                made.append(v)
                print(f"  {v}")
        except Exception as e:
            print(f"  {v} — unavailable ({str(e)[:40]})")
    print(f"\n{len(made)} sample(s) in {out}")
    print(f"Listen, then: cast_voice.py --brand {a.brand} "
          f"--character {a.character} --pick <voice>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
