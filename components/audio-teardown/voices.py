"""VOICE CARDS — one per person: their own clip, what a tool measures, what an ear hears.

the owner, 2026-09-25: "we can make really really really powerful avatar, sub avatar,
casting calls that are direct and detailed and when we generate voice, we know
exactly what to generate."

    1. CLIP      each speaker's lines cut out of the voice track and joined (≤ 90 s)
    2. MEASURED  Praat, the voice scientists' standard tool (GPLv3, runs on this
                 Mac in the venv named by AUDIO_PYTHON): pitch (Hz and how much it moves),
                 jitter, shimmer, harmonics-to-noise; plus pace, talk share and
                 line counts computed from the lines' own timings
    3. HEARD     Gemini listens to the clip alone (prompts/voice-card-v<N>-damon.md):
                 accent, age by ear, texture, read style, delivery style, energy,
                 emotion, emphasis, tics, mic and space, a casting call, a voice prompt
    4. CHECKED   every label against definitions/voice.json and the doctrine's own
                 delivery dial — a value not on a list is kept and marked unknown

The look (face, hair, wardrobe) is joined in the video chain, where the cast
sheet lives; this card carries the times each person speaks so the join can be made.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import gemini as G
import lines as L

HERE = Path(__file__).resolve().parent
sys.path.append(str(HERE.parent / "run-kit"))     # appended, never ahead of this component
from run_kit.paths import repo  # noqa: E402

PY = Path(os.environ.get("AUDIO_PYTHON") or "/nonexistent/audio-python")
VOCAB = json.loads((HERE / "definitions" / "voice.json").read_text())["lists"]
MAX_CLIP = 90.0

PRAAT = r"""
import json, sys, numpy as np, parselmouth
from parselmouth.praat import call
s = parselmouth.Sound(sys.argv[1])
p = s.to_pitch(time_step=0.01, pitch_floor=60, pitch_ceiling=600)
f0 = p.selected_array["frequency"]; f0 = f0[f0 > 0]
out = {"voiced_seconds": round(len(f0) * 0.01, 1)}
if len(f0) > 20:
    st = 12 * np.log2(f0 / np.median(f0))
    out.update(pitch_median_hz=round(float(np.median(f0)), 1),
               pitch_range_hz=[round(float(np.percentile(f0, 10)), 1), round(float(np.percentile(f0, 90)), 1)],
               pitch_movement_semitones=round(float(np.std(st)), 2))
    pp = call(s, "To PointProcess (periodic, cc)", 60, 600)
    out["jitter_percent"] = round(100 * call(pp, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3), 2)
    out["shimmer_percent"] = round(100 * call([s, pp], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6), 2)
    h = call(s.to_harmonicity_cc(), "Get mean", 0, 0)
    out["hnr_db"] = round(h, 1) if h == h else None
print(json.dumps(out))
"""


def delivery_styles():
    """(ids, None) from the doctrine's delivery dial, or ([], why) when it cannot be
    read — the why goes on every card, so an unchecked label is never silent."""
    try:
        d = json.loads((repo(HERE) / "components/marketing-doctrine/delivery.json").read_text())
        dial = next(x for x in d["dials"] if x["id"] == "delivery_style")
        ids = [v["id"] for v in dial["values"]]
        if not ids:
            raise ValueError("delivery_style dial has no values")
        return ids, None
    except Exception as e:
        return [], f"doctrine unreadable: {type(e).__name__}: {str(e)[:160]}"


def cut(voices, segments, out):
    """Join one speaker's segments (≤ MAX_CLIP seconds) into one mp3."""
    keep, total = [], 0.0
    for a, b in segments:
        a, b = max(0.0, a - 0.1), b + 0.15
        if b - a < 0.25:
            continue
        keep.append((a, min(b, a + MAX_CLIP - total)))
        total += keep[-1][1] - keep[-1][0]
        if total >= MAX_CLIP:
            break
    if not keep:
        return None, 0.0
    parts = "".join(f"[0:a]atrim={a:.2f}:{b:.2f},asetpts=PTS-STARTPTS[a{i}];" for i, (a, b) in enumerate(keep))
    parts += "".join(f"[a{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=0:a=1[out]"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(voices), "-filter_complex", parts,
                    "-map", "[out]", "-ac", "1", "-b:a", "96k", str(out)], check=True)
    return out, round(total, 1)


def measure(clip):
    if not PY.exists():
        return {"error": "voice measures not installed (the venv named by AUDIO_PYTHON)"}
    r = subprocess.run([str(PY), "-c", PRAAT, str(clip)], capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stderr or r.stdout)[-200:]}


def check(card, styles):
    """Every label against its list. Unknown values are kept and named, never replaced."""
    unknown = []
    for field, allowed in list(VOCAB.items()) + [("delivery_style", styles)]:
        v = card.get(field)
        for x in (v if isinstance(v, list) else [v]):
            if x and allowed and str(x).replace(" (unsure)", "") not in allowed:
                unknown.append(f"{field}: {x}")
    return unknown


def cards(lines, voices_track, out_dir, total_seconds):
    """[card] for every speaker in the lines."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    styles, unreadable = delivery_styles()
    ptext_path, ptext = G.prompt("voice-card", HERE)
    talk = {}
    for l in lines:
        talk[l["speaker"]] = talk.get(l["speaker"], 0) + max(0.0, l["end"] - l["start"])
    all_talk = sum(talk.values()) or 1.0
    res = []
    for n, who in enumerate(dict.fromkeys(l["speaker"] for l in lines), 1):
        mine = [l for l in lines if l["speaker"] == who]
        clip, secs = cut(voices_track, [(l["start"], l["end"]) for l in mine], out_dir / f"voice-{n}.mp3")
        words = sum(L.count_words(l["text"], l.get("language") or "") for l in mine)
        measured = {"lines": len(mine), "talk_seconds": round(talk[who], 1),
                    "talk_share_percent": round(100 * talk[who] / all_talk),
                    "words_per_minute": round(60 * words / talk[who]) if talk[who] > 1 else None,
                    "first_speaks": mine[0]["start"], "speaks_at": [[l["start"], l["end"]] for l in mine]}
        card = {"speaker": who, "clip": clip.name if clip else None, "clip_seconds": secs, "measured": measured}
        if unreadable:
            card["doctrine_unreadable"] = unreadable       # delivery_style left unchecked, and said so
        if clip:
            measured.update(measure(clip))
            show = {k: v for k, v in measured.items() if k != "speaks_at"}
            text = (ptext.replace("{measured}", json.dumps(show, ensure_ascii=False))
                    .replace("{lines}", "\n".join(f"- {l['text']}" for l in mine)[:4000])
                    .replace("{lists}", json.dumps(VOCAB, ensure_ascii=False))
                    .replace("{delivery_styles}", ", ".join(styles)))
            try:
                heard, model, tried = G.ask(clip, text)
                card.update(heard if isinstance(heard, dict) else {})
                card["heard_by"] = model
            except Exception as e:
                card["heard_error"] = str(e)[:200]
            card["unknown_labels"] = check(card, styles)
        else:
            card["heard_error"] = "too little speech to cut a clip"
        res.append(card)
    (out_dir / "voice-cards.json").write_text(json.dumps({"prompt": ptext_path.name, "cards": res},
                                                         indent=1, ensure_ascii=False) + "\n")
    return res


def render(cards_):
    md = ["### VOICES — one card per person", "",
          "Each person's own lines, cut out of the swipe with the music removed. Measured by a tool "
          "(pitch, pace, talk share), heard by a model (accent, age by ear, texture, delivery). "
          "The casting call and voice prompt are written to cast or generate a matching voice.", ""]
    for c in cards_:
        m = c.get("measured", {})
        md += [f"**{c['speaker']}** — speaks {m.get('talk_share_percent')}% of the time, {m.get('lines')} lines, "
               f"~{m.get('words_per_minute')} words/min",
               f"- Language · accent: {', '.join(c.get('languages') or [])} · {c.get('accent', '—')}",
               f"- Age · gender (by ear): {c.get('age_band', '—')} · {c.get('gender_presentation', '—')}",
               f"- Pitch: {c.get('pitch_band', '—')} (median {m.get('pitch_median_hz', '—')} Hz, "
               f"moves {m.get('pitch_movement_semitones', '—')} semitones) · texture: {', '.join(c.get('texture') or []) or '—'}",
               f"- Read · delivery · energy: {c.get('read_style', '—')} · {c.get('delivery_style', '—')} · {c.get('energy', '—')}",
               f"- Emotion: {c.get('emotion', '—')}",
               f"- Pace: {c.get('pace', '—')}",
               f"- Punches: {', '.join(c.get('emphasis') or []) or '—'} · tics: {', '.join(c.get('tics') or []) or '—'}",
               f"- Mic · talks to: {c.get('mic_space', '—')} · {c.get('talks_to', '—')}",
               f"- **Casting call:** {c.get('casting_call', '—')}",
               f"- **Voice prompt:** {c.get('voice_prompt', '—')}"]
        if c.get("unknown_labels"):
            md.append(f"- Labels not on the lists (kept, to review): {', '.join(c['unknown_labels'])}")
        if c.get("heard_error"):
            md.append(f"- Not heard: {c['heard_error']}")
        if c.get("doctrine_unreadable"):
            md.append(f"- Delivery style not checked — {c['doctrine_unreadable']}")
        md.append("")
    return "\n".join(md)
