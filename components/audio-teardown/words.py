"""THE WORDS, IN EVERY LANGUAGE — Gemini listening to the voice track.

The only model in the 2026-09-25 test that kept Korean and English exactly as
said. The prompt is a file (prompts/words-v<N>-damon.md, highest wins) so it
is shown and changed like every other prompt, never edited in code.

Order of trust (gemini.py): gemini-3.1-pro-preview, then gemini-3.5-flash
(fast; once turned English into Hangul). Neither answering → the caller falls
back to Scribe's words and flags the swipe.
"""
from pathlib import Path

import gemini as G

HERE = Path(__file__).resolve().parent


def listen(audio):
    """{"model", "prompt", "lines", "tried"}; raises when every model failed or the
    answer is not a list — the caller then falls back to Scribe's words."""
    p, text = G.prompt("words", HERE)
    rows, model, tried = G.ask(audio, text)
    if not isinstance(rows, list):
        raise RuntimeError(f"{model} answered a {type(rows).__name__}, not a list of lines")
    out = []
    for x in rows:
        t = str(x.get("text") or "").strip()
        if not t:
            continue
        out.append({"speaker": str(x.get("speaker") or "Speaker 1"), "start": float(x.get("start") or 0),
                    "end": float(x.get("end") or x.get("start") or 0), "text": t,
                    "language": str(x.get("language") or "").lower()[:3],
                    "also": [str(a).lower()[:3] for a in (x.get("also") or []) if a]})
    return {"model": model, "prompt": p.name, "lines": out, "tried": tried}
