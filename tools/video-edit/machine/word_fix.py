#!/usr/bin/env python3
"""word_fix.py — a word or phrase said again in the speaker's own cloned voice, for the edit to lay in where a clip
cut it off or said it wrong (the owner, 4 Oct 2026: "We should never be cutting off words unless I'm discreetly
describing to cut it out").

    python3 word_fix.py <video-production-run> --who <SPEAKER> --say "<the words>" --name <scene>-<word>
            [--before "<the words said just before>"] [--after ""] [--takes 3] [--out <edit run dir>]

Each take is spoken by the speaker's cloned voice (the production run's elements.json `voice_id`), with the words
around it given to the voice so it lands at the line's pace, then given the crisp finish every swapped voice gets.
Every take is transcribed (ElevenLabs Scribe): a take that does not say every word is thrown out. The best take is
cut to its words with room both sides — PAD_IN before the first word, PAD_OUT after the last, never tight (the
3 Oct "they'll … full refund" fix was cut 0.03 s after its last word and lost the end of "refund"). Writes
<out>/patches/<name>.wav + <name>.json (the takes, what each said, which won and why).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from edit_map import PAD_IN, PAD_OUT  # noqa: E402  (the same room every line gets)
import ve_keys  # noqa: E402  (every key through components/keys/loader.py — SI-194 (readers use loader))

MODEL = "eleven_multilingual_v2"
SETTINGS = {"stability": 0.5, "similarity_boost": 0.85, "style": 0.2, "use_speaker_boost": True}
sys.path.insert(0, str(HERE.parents[1] / "video-production" / "machine"))
from omni import CRISP  # noqa: E402  (the crisp finish every swapped voice gets — one copy, in production)
PACE = 0.32   # seconds a word, used only when the speaker has no lines in the edit map to measure
TAIL = 0.12   # a take must have at least this much after its last word, or it is not a clean ending


def norm(w: str) -> str:
    return re.sub(r"[^a-z0-9']", "", w.lower().replace("’", "'"))


def voice_of(vm: Path, who: str) -> str:
    items = json.loads((vm / "elements.json").read_text()).get("items") or []
    v = next((i.get("voice_id") for i in items if (i.get("id") or i.get("name") or "").upper() == who.upper()), None)
    if not v:
        raise SystemExit(f"word_fix: no cloned voice for {who} in {vm / 'elements.json'}")
    return v


def key() -> str:
    """The ElevenLabs key — stops here, naming the key and where it was looked for, when there is none."""
    k = ve_keys.key("ELEVENLABS_API_KEY")
    if not k:
        raise SystemExit(f"word_fix: {ve_keys.missing('ELEVENLABS_API_KEY')}")
    return k


def speak(voice: str, text: str, before: str, after: str, dest: Path, seed: int) -> None:
    k = key()
    body = {"text": text, "model_id": MODEL, "voice_settings": SETTINGS, "seed": seed}
    if before:
        body["previous_text"] = before
    if after:
        body["next_text"] = after
    req = dest.with_suffix(".req.json"); req.write_text(json.dumps(body))
    # the key rides on stdin (-H @-), never on the command line (video-edit#22)
    r = subprocess.run(["curl", "-s", "-o", str(dest), "-w", "%{http_code}", "-X", "POST",
                        f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=mp3_44100_192",
                        "-H", "@-", "-H", "Content-Type: application/json", "--data-binary", f"@{req}"],
                       input=f"xi-api-key: {k}\n", capture_output=True, text=True, timeout=300)
    req.unlink(missing_ok=True)
    if r.stdout.strip() != "200":
        raise SystemExit(f"word_fix: ElevenLabs said {r.stdout.strip()}: {dest.read_text(errors='ignore')[:300]}")


def heard(f: Path) -> list[dict]:
    k = key()
    o = subprocess.run(["curl", "-s", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text", "-H", "@-",
                        "-F", "model_id=scribe_v1", "-F", "timestamps_granularity=word", "-F", f"file=@{f}"],
                       input=f"xi-api-key: {k}\n", capture_output=True, text=True, timeout=300).stdout
    return [w for w in json.loads(o).get("words") or [] if w.get("type") == "word"]


def dur(f) -> float:
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                       capture_output=True, text=True).stdout.strip()
    return float(o or 0)


def judge(text: str, words: list[dict], length: float) -> dict:
    """Does the take say every word, and is there room after the last one?"""
    want = [norm(w) for w in text.split() if norm(w)]
    got = [norm(w["text"]) for w in words if norm(w["text"])]
    ok = got == want
    a = words[0]["start"] if words else 0.0
    b = words[-1]["end"] if words else 0.0
    return {"says": " ".join(w["text"] for w in words), "all_words": ok, "first": a, "last": b,
            "tail": round(length - b, 3), "clean_end": length - b >= TAIL}


def pace_of(out: Path, who: str) -> float:
    """The speaker's own pace, seconds a word, measured on their lines in the edit map (the middle of them) — so a
    re-said word lands at the speed this person talks, whoever they are."""
    m = out / "edit-map.json"
    if not m.exists():
        return PACE
    rates = sorted(l["len"] / len(l["text"].split()) for l in json.loads(m.read_text())["voice"]
                   if l["who"].upper() == who.upper() and len(l["text"].split()) >= 4)
    return rates[len(rates) // 2] if rates else PACE


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--who", required=True); ap.add_argument("--say", required=True)
    ap.add_argument("--name", required=True); ap.add_argument("--before", default=""); ap.add_argument("--after", default="")
    ap.add_argument("--takes", type=int, default=3); ap.add_argument("--out")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else HERE.parents[2] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    d = out / "patches"; d.mkdir(parents=True, exist_ok=True)
    voice = voice_of(vm, a.who)
    takes = []
    for i in range(1, a.takes + 1):
        raw = d / f"{a.name}-take{i}-raw.mp3"
        speak(voice, a.say, a.before, a.after, raw, seed=i)
        fin = d / f"{a.name}-take{i}.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", CRISP, "-ar", "44100", "-ac", "1", str(fin)], check=True)
        j = judge(a.say, heard(fin), dur(fin))
        takes.append({"take": i, "file": fin.name, **j})
        print(f"  take {i}: {j['says']!r}  all words: {j['all_words']}  room after: {j['tail']:.2f}s")
    good = [t for t in takes if t["all_words"] and t["clean_end"]]
    if not good:
        raise SystemExit(f"word_fix: no take said {a.say!r} whole with room after it — nothing written")
    # the take nearest a natural length for its words (no rushed, no dragged read)
    n = len(a.say.split())
    pace = pace_of(out, a.who)
    best = min(good, key=lambda t: abs((t["last"] - t["first"]) - pace * n))
    src = d / best["file"]
    s0, s1 = max(0.0, best["first"] - PAD_IN), min(dur(src), best["last"] + PAD_OUT)
    wav = d / f"{a.name}.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{s0:.3f}", "-t", f"{s1 - s0:.3f}", "-i", str(src),
                    "-af", "afade=t=in:d=0.01,areverse,afade=t=in:d=0.03,areverse", str(wav)], check=True)
    check = judge(a.say, heard(wav), dur(wav))
    if not check["all_words"]:
        raise SystemExit(f"word_fix: the cut take says {check['says']!r}, not {a.say!r} — nothing kept")
    (d / f"{a.name}.json").write_text(json.dumps({"who": a.who, "voice_id": voice, "say": a.say, "before": a.before,
                                                  "after": a.after, "model": MODEL, "settings": SETTINGS, "takes": takes,
                                                  "picked": best["take"], "cut": [round(s0, 3), round(s1, 3)],
                                                  "pads": [PAD_IN, PAD_OUT], "final_says": check["says"],
                                                  "seconds": round(dur(wav), 3)}, indent=1))
    print(f"word_fix: {wav} · take {best['take']} · {dur(wav):.2f}s · says {check['says']!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
