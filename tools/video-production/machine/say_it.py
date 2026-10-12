#!/usr/bin/env python3
"""say_it.py — hear how the brand's protected words are said, one short clip
per word, so the owner can LISTEN and confirm them.

the owner, 2026-09-23: "make sure brand names, ingredients, mechanisms are never
mispronounced through AI." The words and their respellings live in
`brands/<brand>/brand-identity/voice/pronunciation.json`; a row marked `confirmed: false` is
a best guess the audio gate warns about every time it is used. This tool reads
each chosen word in the brand's cast voice, exactly the way a real run would
send it (the same swap, the same number rules, the same pins), and writes one
clip per word plus a page to play them from.

    python3 machine/say_it.py brand-a                     # dry run: lists what it would say, spends nothing
    python3 machine/say_it.py brand-a --spend             # makes the clips (ElevenLabs)
    python3 machine/say_it.py brand-a --terms "Brand A,Centella" --spend
    python3 machine/say_it.py brand-a --character june --numbers 3 --spend

Picks, when --terms is not given: the brand name(s), every product name, then
the unconfirmed ingredients and mechanisms, capped at --limit (default 12),
plus --numbers number examples (default 3) from spoken-rules.json. With
--spend each clip is also heard back (speech-to-text) and the match on the
real spelling is recorded — how the audio gate's threshold is calibrated.

Writes `runs/video-production/<brand>/say-it-<YYMMDD>/`: `NN-<word>.mp3`,
`index.json` (term, what was sent, heard, match, confirmed) and `index.html`
(play each one). Exit 0 done · 2 no voice / no lexicon · 3 bad input.
"""
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"vm_{name}", HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


voice = _load("voice")
lexicon = _load("lexicon")
spoken = _load("spoken_numbers")
lp = _load("lineparity")

KIND_ORDER = {"brand": 0, "product": 1, "ingredient": 2, "mechanism": 3, "other": 4}


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "x"


def pick_character(brand: str, character: str | None, cast_root: Path | None = None) -> Path:
    root = cast_root or voice._load("element_paths").casting_root(brand, voice.WORKSPACE)
    if character:
        return root / character
    for home in sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []:
        rec = home / "voice.json"
        if rec.is_file() and (json.loads(rec.read_text()) or {}).get("voice_id"):
            return home
    raise SystemExit(f"no character with a voice_id under {root} — bind one (voice.json) or pass --character")


def choose(rows: list[dict], terms: list[str] | None, limit: int) -> list[dict]:
    if terms:
        by = {r["term"].lower(): r for r in rows}
        missing = [t for t in terms if t.lower() not in by]
        if missing:
            raise SystemExit(f"not in the pronunciation list: {', '.join(missing)}")
        return [by[t.lower()] for t in terms]
    names = [r for r in rows if r["kind"] in ("brand", "product") and r["say_as"] != r["term"]
             or r["kind"] == "brand"]
    rest = [r for r in rows if r not in names and not r.get("confirmed")]
    rest.sort(key=lambda r: (KIND_ORDER.get(r["kind"], 9), -len(r["say_as"])))
    return (names + rest)[:limit]


def number_examples(n: int) -> list[str]:
    ex = []
    for rule in spoken.rules()["rules"]:
        if rule["id"] in ("money", "range", "multiplier", "percent", "time", "year"):
            ex.append(rule["examples"][0][0])
    return ex[:n]


def run(brand: str, spend: bool = False, terms: list[str] | None = None, character: str | None = None,
        limit: int = 12, numbers: int = 3, out: Path | None = None, transport=None, stt_transport=None,
        key: str | None = None, cast_root: Path | None = None) -> dict:
    rows = lexicon.load(brand)
    if not rows:
        raise SystemExit(f"{brand} has no pronunciation list at {lexicon.path_of(brand)}")
    home = pick_character(brand, character, cast_root)
    voice_id, model_id, settings = voice.binding(home)
    items = [{"term": r["term"], "kind": r["kind"], "say_as": r["say_as"],
              "confirmed": bool(r.get("confirmed")), "source": r.get("source")}
             for r in choose(rows, terms, limit)]
    items += [{"term": t, "kind": "number", "say_as": spoken.say(t), "confirmed": True,
               "source": "machine/spoken-rules.json"} for t in number_examples(numbers)]
    out = out or (voice.WORKSPACE / "runs" / "video-production" / brand / f"say-it-{datetime.now():%y%m%d}")
    index = {"brand": brand, "character": home.name, "voice_id": voice_id, "model_id": model_id,
             "pins": voice.pins(), "at": voice.now(), "spent": spend, "clips": []}
    url = voice.ELEVEN_TTS.format(voice_id=voice_id)
    k = key if key is not None else voice.key_of()
    if spend and not k:
        raise SystemExit("no ELEVENLABS_API_KEY — in the environment or the Keychain vault")
    chars = 0
    for i, it in enumerate(items, 1):
        body, said = voice.body_for(it["term"] + ".", model_id, rows)
        if settings:
            body["voice_settings"] = settings
        chars += len(body["text"])
        clip = {**it, "file": f"{i:02d}-{slug(it['term'])}.mp3", "sent": body["text"], "said_as": said["said_as"]}
        if spend:
            out.mkdir(parents=True, exist_ok=True)
            audio = (transport or voice.http_transport)("POST", url, body, {
                "xi-api-key": k, "Content-Type": "application/json", "Accept": "audio/mpeg"})
            (out / clip["file"]).write_bytes(audio)
            heard = lp.check(out / clip["file"], it["term"], transport=stt_transport, key=k)
            clip["heard"] = heard["heard"]
            clip["match_real_spelling"] = lexicon.best_match(it["term"], heard["heard"]) if it["kind"] != "number" \
                else heard["match"]
            clip["match_say_as"] = lexicon.best_match(it["say_as"], heard["heard"])
        index["clips"].append(clip)
    index["characters_sent"] = chars
    if spend:
        (out / "index.json").write_text(json.dumps(index, indent=1, ensure_ascii=False) + "\n")
        (out / "index.html").write_text(page(index))
    index["out"] = str(out)
    return index


def page(index: dict) -> str:
    rows = []
    for c in index["clips"]:
        state = "confirmed" if c["confirmed"] else "NOT YET CONFIRMED"
        heard = html.escape(c.get("heard") or "")
        rows.append(
            f"<tr><td><b>{html.escape(c['term'])}</b><br><small>{c['kind']} · {state}</small></td>"
            f"<td><code>{html.escape(c['sent'])}</code></td>"
            f"<td><audio controls preload=none src=\"{c['file']}\"></audio></td>"
            f"<td>{heard}<br><small>match {c.get('match_real_spelling')}</small></td></tr>")
    return f"""<!doctype html><meta charset=utf-8><title>Say it — {index['brand']}</title>
<style>body{{font:15px system-ui;margin:24px;max-width:1000px}}td{{padding:8px;border-bottom:1px solid #ddd;vertical-align:top}}
code{{background:#f4f4f4;padding:2px 4px}}</style>
<h1>How {index['brand']}'s words are said</h1>
<p>Voice: {html.escape(index['character'])} · {index['model_id']} · pins {html.escape(json.dumps(index['pins']))} · {index['at']}</p>
<p>Listen to each. Right → mark it <code>confirmed: true</code> in brands/{index['brand']}/voice/pronunciation.json.
Wrong → change its <code>say_as</code> and make the clip again.</p>
<table><tr><th>word</th><th>sent to the voice</th><th>listen</th><th>what the transcriber heard</th></tr>
{''.join(rows)}</table>
"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("brand")
    ap.add_argument("--spend", action="store_true", help="make the clips (ElevenLabs); the default is a dry run")
    ap.add_argument("--terms", help="comma-separated terms from the list, in the order to say them")
    ap.add_argument("--character")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--numbers", type=int, default=3)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    terms = [t.strip() for t in a.terms.split(",")] if a.terms else None
    try:
        idx = run(a.brand, spend=a.spend, terms=terms, character=a.character, limit=a.limit,
                  numbers=a.numbers, out=Path(a.out) if a.out else None)
    except SystemExit as e:
        print(str(e), file=sys.stderr)
        return 2
    for c in idx["clips"]:
        extra = f"  heard {c['heard']!r} (match {c['match_real_spelling']})" if "heard" in c else ""
        print(f"{c['file']}  {c['term']!r} → sent {c['sent']!r}{'' if c['confirmed'] else '  [unconfirmed]'}{extra}")
    print(f"{len(idx['clips'])} clip(s), {idx['characters_sent']} characters "
          + (f"— written to {idx['out']}" if a.spend else "— dry run, nothing spent"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
