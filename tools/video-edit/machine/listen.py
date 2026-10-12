#!/usr/bin/env python3
"""listen.py — the clean pass on the SOUND of an edit map, before anyone hears it (the owner, 3 Oct 2026:
"do another clean pass on the scenes and audio to make sure things are cut cleanly").

    python3 listen.py <video-production-run> [--out <edit run dir>]

Mixes only the soundtrack of the cut — every clip's span under its line (muted where a patch fixes a word),
every own-track line, sound and patch, each at its place — no video is rendered. Then transcribes the mix
word by word (ElevenLabs Scribe) and holds it against the script:
  missing / clipped words · words heard twice · words nobody scripted (made-up speech leaking through)
  · two voices on top of each other · dead air longer than the pace allows.
Writes <out>/listen/: mix.wav, heard.json, listen.json, and prints every finding with its second.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ve_keys  # noqa: E402  (every key through components/keys/loader.py — SI-194 (readers use loader))

SR = 44100
FADE = 0.012           # seconds faded in and out on every piece of sound (de-click)
DEAD_AIR = 0.6          # a silence longer than this between two lines is dead air (pace "tight")


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(n: int) -> str:
    """An integer the way it is said (English) — 29 'twenty nine', 400 'four hundred', 1600 'one thousand six hundred'."""
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + number_words(n % 100))
    if n < 1_000_000:
        return number_words(n // 1000) + " thousand" + ("" if n % 1000 == 0 else " " + number_words(n % 1000))
    return str(n)


def spoken(text: str) -> str:
    """Text as it is SAID: $29 → 'twenty nine dollars', 100% → 'one hundred percent', 60 → 'sixty', 2,000 → 'two
    thousand'. Applied to the script AND to what the transcriber heard, so '$400' and 'four hundred' are the same words.
    Any brand, price or number — nothing here belongs to one ad."""
    def money(mt):
        whole = int(mt.group(1).replace(",", ""))
        return number_words(whole) + (" dollar" if whole == 1 else " dollars")
    text = re.sub(r"\$(\d[\d,]*)(?:\.\d+)?", money, text)
    text = re.sub(r"(\d[\d,]*)\s?%", lambda mt: number_words(int(mt.group(1).replace(",", ""))) + " percent", text)
    text = re.sub(r"\d[\d,]*", lambda mt: number_words(int(mt.group(0).replace(",", ""))), text)
    return text


def _norm(w: str) -> str:
    """One word, compared without case or punctuation; letters of any language are kept."""
    return re.sub(r"[^\w']", "", w.lower().replace("’", "'"), flags=re.UNICODE).replace("_", "")


def words_of(text: str) -> list[str]:
    return [x for x in (_norm(w) for w in spoken(text).split()) if x]


def mix(vm: Path, out: Path, m: dict, d: Path | None = None) -> Path:
    d = d or out / "listen"; d.mkdir(parents=True, exist_ok=True)
    parts = []                                         # (file, start in source, length, at in cut)
    for l in m["voice"] + m["sounds"]:
        if l["kind"] == "in clip":
            parts.append((vm / "clips" / f"{l['clip']}.mp4", l["in"], l["len"], l["a"]))
        else:
            parts.append(((out if l.get("base") else vm) / l["file"], 0.0, l["len"], l["a"]))
    for p in m.get("patches") or []:
        parts.append((out / p["file"], 0.0, p["b"] - p["a"], p["a"]))
    mutes = [(p["mute_a"], p["mute_b"]) for p in m.get("patches") or []]
    inputs, chains = [], []
    for i, (f, ss, ln, at) in enumerate(parts):
        inputs += ["-ss", f"{ss:.3f}", "-t", f"{ln:.3f}", "-i", str(f)]
        mute = "".join(f",volume=enable='between(t,{max(0, ma - at):.3f},{mb - at:.3f})':volume=0"
                       for ma, mb in mutes if f.suffix == ".mp4" and ma < at + ln and mb > at)
        fd = min(FADE, ln / 4)                             # every join faded a hair: no click where two pieces meet
        chains.append(f"[{i}:a]aresample={SR},aformat=channel_layouts=mono{mute},afade=t=in:d={fd:.3f},"
                      f"afade=t=out:st={max(0, ln - fd):.3f}:d={fd:.3f},adelay={int(at * 1000)}:all=1[a{i}]")
    graph = ";".join(chains) + ";" + "".join(f"[a{i}]" for i in range(len(parts))) + \
        f"amix=inputs={len(parts)}:normalize=0,atrim=0:{m['total']:.3f}[out]"
    wav = d / "mix.wav"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", "-ar", str(SR), str(wav)],
                   check=True)
    return wav


def transcribe(wav: Path) -> list[dict]:
    k = ve_keys.key("ELEVENLABS_API_KEY")
    if not k:
        raise SystemExit(f"listen: {ve_keys.missing('ELEVENLABS_API_KEY')}")
    # the key rides on stdin (-H @-), never on the command line (video-edit#22)
    out = subprocess.run(["curl", "-s", "-X", "POST", "https://api.elevenlabs.io/v1/speech-to-text", "-H", "@-",
                          "-F", "model_id=scribe_v1", "-F", "timestamps_granularity=word", "-F", f"file=@{wav}"],
                         input=f"xi-api-key: {k}\n", capture_output=True, text=True, timeout=600).stdout
    return [w for w in json.loads(out).get("words") or [] if w.get("type") == "word"]


def check(m: dict, heard: list[dict]) -> list[dict]:
    lines = sorted(m["voice"] + m["sounds"], key=lambda l: l["a"])
    script = [(w, l) for l in lines for w in words_of(l["text"])]
    got = [(x, w) for w in heard for x in words_of(w["text"])]
    sm = difflib.SequenceMatcher(a=[w for w, _ in script], b=[w for w, _ in got], autojunk=False)
    out = []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "equal":
            continue
        miss = [script[i][0] for i in range(a0, a1)]
        extra = [got[j][0] for j in range(b0, b1)]
        at = got[b0][1]["start"] if b0 < len(got) else (script[a0][1]["a"] if a0 < len(script) else m["total"])
        line = script[a0][1] if a0 < len(script) else script[-1][1]
        if op == "replace" and len(miss) == len(extra) and all(difflib.SequenceMatcher(a=x, b=y).ratio() > 0.6 for x, y in zip(miss, extra)):
            continue                                       # the same words, spelt differently by the transcriber
        out.append({"t": round(at, 2), "what": {"delete": "missing / clipped", "insert": "heard but not scripted",
                                                  "replace": "different words"}[op],
                    "script": " ".join(miss), "heard": " ".join(extra), "line": line["scene"], "who": line["who"]})
    for x, y in zip(lines, lines[1:]):
        gap = y["a"] - x["b"]
        if gap > DEAD_AIR:
            out.append({"t": round(x["b"], 2), "what": f"dead air {gap:.2f}s", "line": f"{x['scene']}→{y['scene']}"})
        if gap < -0.05 and x["kind"] != "sound" and y["kind"] != "sound":
            out.append({"t": round(y["a"], 2), "what": f"two voices overlap {-gap:.2f}s", "line": f"{x['scene']}→{y['scene']}"})
    return sorted(out, key=lambda r: r["t"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("run"); ap.add_argument("--out")
    a = ap.parse_args(argv)
    vm = Path(a.run)
    rj = json.loads((vm / "run.json").read_text())
    out = Path(a.out) if a.out else Path(__file__).resolve().parents[3] / "runs" / "video-edit" / rj["brand"] / rj["label"]
    m = json.loads((out / "edit-map.json").read_text())
    wav = mix(vm, out, m)
    heard = transcribe(wav)
    (out / "listen" / "heard.json").write_text(json.dumps(heard, indent=1))
    found = check(m, heard)
    (out / "listen" / "listen.json").write_text(json.dumps(found, indent=1))
    print(f"listen: {len(heard)} words heard · {len(found)} finding(s) → {out / 'listen'}")
    for f in found:
        print(f"  {f['t']:7.2f}s  {f['what']:<24} {f.get('line', '')}  script: {f.get('script', '')!r}  heard: {f.get('heard', '')!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
