#!/usr/bin/env python3
"""3v · THE CONTROL — the proven ad's own script, in stage 3's shape.

The Variation video chain starts from a proven ad of ours (Damon, 2026-09-28:
"Once you've hit a winner … you're going to control for that existing
awareness stage for sure"). Stage 3 substitutes our brand into somebody
else's script; here the script is already ours and already won, so there is
nothing to substitute. This files VERSION 0 — every transcript line, word for
word — where stage 3's output would be, and the VARIATION route hands it to
every stage that reads `@stage3`. No model.

The prompt file (prompts/stage-3v-control/) is the rule this code keeps.
"""
import json
from pathlib import Path


def _ts(sec):
    sec = float(sec or 0)
    return f"{int(sec // 60)}:{sec % 60:04.1f}"


def render(transcript, proof=None, label=""):
    rows = ["**1. THE INJECTED SCRIPT**", "",
            "| # | Timestamp | Speaker | Source line | Our line |",
            "|---|---|---|---|---|"]
    for t in transcript:
        txt = (t.get("text") or "").replace("|", "/").strip()
        rows.append(f"| {t.get('id')} | {_ts(t.get('start'))} | {t.get('speaker') or ''} "
                    f"| \"{txt}\" | \"{txt}\" |")
    p = ""
    for x in proof or []:
        nums = ", ".join(f"{k} {x[k]:,}" if isinstance(x.get(k), (int, float)) else f"{k} {x[k]}"
                         for k in ("views", "likes", "saves", "shares", "spend", "purchases", "revenue")
                         if x.get(k) is not None)
        p += f" {x['kind'].capitalize()} proof: {nums} ({x.get('source')})."
    rows += ["", "**2. WHAT THIS IS**", "",
             f"VERSION 0 — the control. This is {label or 'the proven ad'}, our own ad, "
             f"unchanged: every line above is what it said, word for word. Nothing was "
             f"substituted, corrected or improved, because this is what earned the numbers."
             + p,
             "", "## ELEMENT LEDGER", "",
             "| # | Element | Status |", "|---|---|---|",
             "| 1 | Every element of the source | Kept |",
             "", "## STRUCTURE QUESTIONS FOR DAMON", "", "None — the control changes nothing.", ""]
    return "\n".join(rows)


def file_control(d, st, out):
    """Write the control for run folder `d` to `out`; returns the model tag."""
    tf = Path(d) / "transcript.json"
    if not tf.is_file():
        raise RuntimeError("3v needs the proven ad's transcript.json in the run folder")
    transcript = json.loads(tf.read_text())
    if not transcript:
        raise RuntimeError("3v: the transcript is empty — the control would carry no lines")
    Path(out).write_text(render(transcript, st.get("proven_proof"), st.get("variation_of") or st.get("label")))
    return "none (control.py)"
