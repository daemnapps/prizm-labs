#!/usr/bin/env python3
"""lexicon.py — the brand's protected words: every brand name, product,
ingredient and mechanism, and how the voice must say it.

the owner, 2026-09-23: "make sure brand names, ingredients, mechanisms are never
mispronounced through AI." The words live with the brand, not here:
`brands/<brand>/brand-identity/voice/pronunciation.json` (rows of {term, say_as, kind,
confirmed, source}). This machine only READS them.

Before a voice or song call, every term in the text is replaced by its
`say_as` — whole word, any case, longest term first, one pass so nothing is
replaced twice. The script is never touched: captions keep the real spelling,
and what was swapped is recorded beside the audio (timing.json / song.json).

Why our own swap and not an ElevenLabs pronunciation dictionary: the
dictionary's phoneme (IPA) rules only work on eleven_flash_v2 and eleven_v3,
and the voice read is eleven_multilingual_v2 (stitching needs it); its alias
rules DO work there, but they live on the ElevenLabs account where nobody on
the team can see them, and the music door takes no dictionary at all. A swap
in the text works on every model, the song included, and every row sits in a
file anyone can read. Doc: https://elevenlabs.io/docs/eleven-api/guides/how-to/text-to-speech/pronunciation-dictionaries

The gate side: `heard_check(line, heard, rows)` — every term in the line must
be heard in the transcript, matched on its ORIGINAL spelling (the transcriber
writes a brand word its own way, so the match is fuzzy: providers.json
gates.protected_words.threshold). `unconfirmed_in(line, rows)` lists the words
nobody has confirmed by ear yet — a warning, never a stop.
"""
from __future__ import annotations

import difflib
import json
import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
KINDS = ("brand", "product", "ingredient", "mechanism", "other")
DEFAULT_THRESHOLD = 0.8


def _workspace() -> Path | None:
    env = os.environ.get("AI_WORKSPACE")
    if env and (Path(env) / "brands").is_dir():
        return Path(env)
    for d in [HERE, *HERE.parents]:
        if (d / "components").is_dir() and (d / "brands").is_dir():
            return d
    return None


# tests point this at a fixture tree; None means the real workspace's brands/
BRANDS_ROOT: Path | None = None


def path_of(brand: str) -> Path | None:
    root = BRANDS_ROOT or ((_workspace() or HERE) / "brands")
    return Path(root) / brand / "brand-identity" / "voice" / "pronunciation.json" if brand else None


def validate(rows: list) -> list[str]:
    """Problems with a lexicon, named. A bad row is refused, never guessed at."""
    probs, seen = [], set()
    for i, r in enumerate(rows, 1):
        if not isinstance(r, dict) or not str(r.get("term", "")).strip():
            probs.append(f"row {i}: no term")
            continue
        if not str(r.get("say_as", "")).strip():
            probs.append(f"row {i} ({r['term']}): no say_as")
        if r.get("kind") not in KINDS:
            probs.append(f"row {i} ({r['term']}): kind {r.get('kind')!r} is not one of {', '.join(KINDS)}")
        if not isinstance(r.get("confirmed"), bool):
            probs.append(f"row {i} ({r['term']}): confirmed must be true or false")
        k = r["term"].strip().lower()
        if k in seen:
            probs.append(f"row {i} ({r['term']}): the term is listed twice")
        seen.add(k)
    return probs


def load(brand: str | None) -> list[dict]:
    """The brand's rows, or [] when the brand has no lexicon yet. A lexicon
    that is there but broken is a stop — a protected word must never be
    silently unprotected."""
    p = path_of(brand or "")
    if not p or not p.is_file():
        return []
    doc = json.loads(p.read_text())
    rows = doc.get("rows") if isinstance(doc, dict) else doc
    probs = validate(rows or [])
    if probs:
        raise SystemExit(f"{p}: the pronunciation list has problems — " + "; ".join(probs))
    return rows or []


def for_run(run: Path) -> list[dict]:
    try:
        brand = (json.loads((Path(run) / "run.json").read_text()) or {}).get("brand")
    except Exception:
        brand = None
    return load(brand)


def _pattern(term: str) -> str:
    # whole word, any run of spaces, and a ™/® stuck to the end goes with it
    body = r"\s+".join(re.escape(p) for p in term.split())
    return rf"(?<![\w]){body}(?![\w])[™®]?"


def apply(text: str, rows: list[dict]) -> tuple[str, list[dict]]:
    """(text as the model should read it, [{term, say_as, found}]). Longest
    term first, case-insensitive, one pass — a say_as is never re-read."""
    rows = [r for r in rows or [] if r.get("term") and r.get("say_as")]
    if not rows or not text:
        return text or "", []
    order = sorted(rows, key=lambda r: len(r["term"]), reverse=True)
    rx = re.compile("|".join(f"({_pattern(r['term'])})" for r in order), re.I)
    subs: list[dict] = []

    def repl(m):
        r = order[m.lastindex - 1]
        if r["say_as"] != r["term"]:
            subs.append({"term": r["term"], "say_as": r["say_as"], "found": m.group(0)})
        return r["say_as"]
    return rx.sub(repl, text), subs


def terms_in(text: str, rows: list[dict]) -> list[dict]:
    """The rows whose term is in the line (longest first; a term inside a
    longer one that matched is not counted twice)."""
    rows = [r for r in rows or [] if r.get("term")]
    if not rows or not text:
        return []
    order = sorted(rows, key=lambda r: len(r["term"]), reverse=True)
    rx = re.compile("|".join(f"({_pattern(r['term'])})" for r in order), re.I)
    out, seen = [], set()
    for m in rx.finditer(text):
        r = order[m.lastindex - 1]
        if r["term"] not in seen:
            seen.add(r["term"])
            out.append(r)
    return out


def _words(s: str) -> list[str]:
    s = re.sub(r"\[[^\]]*\]", " ", s or "").lower()
    return re.sub(r"[^\w\s]", " ", s).split()


def best_match(term: str, heard: str) -> float:
    """How well the term is heard anywhere in the transcript: the best
    character match between the term and any run of words about its length,
    with and without the spaces (a transcriber may write "vel une")."""
    want = " ".join(_words(term))
    if not want:
        return 1.0
    got = _words(heard)
    n = len(want.split())
    best = 0.0
    for size in {max(1, n - 1), n, n + 1}:
        for i in range(0, max(1, len(got) - size + 1)):
            span = got[i:i + size]
            if not span:
                continue
            for a, b in ((" ".join(span), want), ("".join(span), want.replace(" ", ""))):
                best = max(best, difflib.SequenceMatcher(None, a, b).ratio())
    return round(best, 3)


def heard_check(line: str, heard: str, rows: list[dict], threshold: float = DEFAULT_THRESHOLD) -> list[dict]:
    """[{term, match, heard_ok}] for every protected term in the line."""
    return [{"term": r["term"], "say_as": r["say_as"], "match": (m := best_match(r["term"], heard)),
             "heard_ok": m >= threshold, "confirmed": bool(r.get("confirmed"))}
            for r in terms_in(line, rows)]


def unconfirmed_in(line: str, rows: list[dict]) -> list[str]:
    return [r["term"] for r in terms_in(line, rows) if not r.get("confirmed")]


def threshold_of() -> float:
    try:
        reg = json.loads((HERE / "providers.json").read_text())
        return float(((reg.get("gates") or {}).get("protected_words") or {}).get("threshold", DEFAULT_THRESHOLD))
    except Exception:
        return DEFAULT_THRESHOLD


def for_model(text: str, rows: list[dict]) -> tuple[str, dict]:
    """The ONE step every voice and song call goes through: the protected
    words swapped for their say_as, then every figure said in words.
    Returns (text to send, {said_as: [...], numbers: [...]}) for the record."""
    sn = _spoken()
    swapped, subs = apply(text, rows)
    said, nums = sn.say_logged(swapped)
    return said, {"said_as": subs, "numbers": nums}


def _spoken():
    import importlib.util
    spec = importlib.util.spec_from_file_location("vm_spoken_numbers", HERE / "spoken_numbers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
