#!/usr/bin/env python3
"""spelling.py — captions in the SCRIPT's spelling, on the transcriber's clock.

Damon, 2026-09-23: the transcriber writes what it hears, so a brand word or a figure
lands on screen wrong (a brand name spelled as it sounds, "twenty-nine dollars"). The script already has the
right spelling — production sent the voice a respelled or spoken-out copy of it
(`vo/timing.json → said_as` for protected words, `numbers` for figures). This lines the
two up and shows the script's words with the heard words' timings.

    align(heard, line, said=None) -> (words, notes)

`heard` is [{text, start, end}] (source seconds), `line` the scene's script text,
`said` production's swaps {said_as: [{term, say_as}], numbers: [{from, to}]} (optional).
Both sides are turned into what a person SAYS (a figure into its words, a protected word
also into its say_as) and aligned as a sequence (Needleman–Wunsch on those spoken
pieces, a fuzzy letter match counting as the same word). Each script word then takes the
start of its first heard word and the end of its last: "$29" stays "$29" and lasts as
long as "twenty-nine dollars" did. A heard word that lines up with no script word is
kept as heard and named in `notes`; a script word nobody said is left off (it has no
time) and named too. Standard library only.
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

SAME = 0.62      # letters alike enough to be the same word (a brand name heard one vowel and consonant off scores ~0.75)
GAP = -0.45      # a word on one side only
MERGE = 0.72     # a split or run-together word: the joined letters must be this alike

_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def _under_1000(n: int) -> list[str]:
    out = []
    if n >= 100:
        out += [_ONES[n // 100], "hundred"]
        n %= 100
        if not n:
            return out
    if n < 20:
        return out + [_ONES[n]]
    return out + [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])


def int_words(n: int) -> list[str]:
    if n < 1000:
        return _under_1000(n)
    out = []
    for size, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= size:
            out += _under_1000(n // size) + [name]
            n %= size
    return out + (_under_1000(n) if n else [])


def _figure(tok: str) -> list[str] | None:
    """A figure said out: $29 → twenty nine dollars · 29.99 → twenty nine ninety nine ·
    40% → forty percent · 3x → three times · 1,200 → one thousand two hundred."""
    m = re.fullmatch(r"(\$|£|€)?(\d[\d,]*)(?:\.(\d+))?(%|x|×|k)?", tok)
    if not m:
        return None
    cur, whole, frac, tail = m.groups()
    n = int(whole.replace(",", ""))
    out = int_words(n)
    if frac:
        out += int_words(int(frac)) if len(frac) == 2 and cur else ["point"] + [_ONES[int(d)] for d in frac]
    if cur:
        out += [{"$": "dollars", "£": "pounds", "€": "euros"}[cur]] if not (frac and len(frac) == 2) else []
    out += {"%": ["percent"], "x": ["times"], "×": ["times"], "k": ["thousand"]}.get(tail or "", [])
    return out


def _letters(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", t.lower())


def spoken(tok: str, swaps: dict | None = None) -> list[str]:
    """What a person says for one written word, as pieces: a figure is its words, a
    hyphenated word is its parts, everything else its letters."""
    sw = swaps or {}
    bare = tok.strip(".,!?;:\"'()[]…—–")
    for f, to in (sw.get("numbers") or {}).items():
        if bare == f:
            return [p for p in re.split(r"[\s\-]+", to.lower()) if _letters(p)] or [_letters(bare)]
    fig = _figure(bare.lower())
    if fig:
        return fig
    out = []
    for p in re.split(r"[\-–—/]+", bare):
        p = _letters(p)
        for run in re.findall(r"[a-z]+|\d+", p) if re.search(r"\d", p) else ([p] if p else []):
            out += int_words(int(run)) if run.isdigit() else [run]  # SPF30 → spf thirty
    return out


def _swaps(said: dict | None) -> dict:
    said = said or {}
    return {"numbers": {str(r.get("from", "")).strip(): str(r.get("to", "")) for r in said.get("numbers") or [] if r.get("from")},
            "say_as": {_letters(r["term"]): _letters(r["say_as"]) for r in said.get("said_as") or [] if r.get("term") and r.get("say_as")}}


def _sim(script_piece: str, heard_piece: str, say_as: dict) -> float:
    if script_piece == heard_piece:
        return 1.0
    best = difflib.SequenceMatcher(None, script_piece, heard_piece).ratio()
    alt = say_as.get(script_piece) or say_as.get(script_piece.rstrip("s"))
    if alt:
        best = max(best, difflib.SequenceMatcher(None, alt, heard_piece).ratio())
    return best


MOVES = ((1, 1), (1, 2), (1, 3), (2, 1), (3, 1))  # a word the transcriber split into two (a brand name heard as two words) or ran together


def _align(a: list[str], b: list[str], say_as: dict) -> list[tuple[list[int], list[int]]]:
    """Global alignment of two piece lists. A pair (or a run of up to three pieces on one
    side against one on the other) only counts when the letters are alike. Returns the
    matched groups as ([script pieces], [heard pieces])."""
    n, m = len(a), len(b)
    NEG = -1e9
    S = [[NEG] * (m + 1) for _ in range(n + 1)]
    back: dict[tuple[int, int], tuple] = {}
    S[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            best, how = NEG, None
            if i and S[i - 1][j] + GAP > best:
                best, how = S[i - 1][j] + GAP, ("gap", 1, 0)
            if j and S[i][j - 1] + GAP > best:
                best, how = S[i][j - 1] + GAP, ("gap", 0, 1)
            for di, dj in MOVES:
                if i < di or j < dj or S[i - di][j - dj] <= NEG / 2:
                    continue
                s = _sim("".join(a[i - di:i]), "".join(b[j - dj:j]), say_as)
                many = max(di, dj)
                if many > 1:  # a merge only when the joined letters are one word AND clearly better than any one piece alone
                    lone, parts = (a[i - 1], b[j - dj:j]) if di == 1 else (b[j - 1], a[i - di:i])
                    alone = max(_sim(lone, p, say_as) if di == 1 else _sim(p, lone, say_as) for p in parts)
                    if s < MERGE or s < alone + 0.15:
                        continue
                sc = S[i - di][j - dj] + ((s - 0.3 * (many - 1)) * many if s >= SAME else -1.0)
                if sc > best:
                    best, how = sc, ("pair" if s >= SAME else "miss", di, dj)
            S[i][j], back[(i, j)] = best, how
    out, i, j = [], n, m
    while i > 0 or j > 0:
        kind, di, dj = back[(i, j)]
        if kind == "pair":
            out.append((list(range(i - di, i)), list(range(j - dj, j))))
        i, j = i - di, j - dj
    out.reverse()
    return out


def align(heard: list[dict], line: str | None, said: dict | None = None) -> tuple[list[dict], list[str]]:
    """The heard words re-spelled as the script writes them, timed as they were heard."""
    if not heard or not str(line or "").strip():
        return [dict(w) for w in heard or []], []
    sw = _swaps(said)
    script = str(line).split()
    a, a_of = [], []            # script pieces, and the script word each came from
    for k, tok in enumerate(script):
        for p in spoken(tok, sw):
            a.append(p); a_of.append(k)
    b, b_of = [], []            # heard pieces, and the heard word each came from
    for k, w in enumerate(heard):
        for p in spoken(str(w["text"])):
            b.append(p); b_of.append(k)
    got: dict[int, set[int]] = {}   # script word → heard words
    used_heard: set[int] = set()
    for ii, jj in _align(a, b, sw["say_as"]):
        for i in ii:
            for j in jj:
                got.setdefault(a_of[i], set()).add(b_of[j])
                used_heard.add(b_of[j])
    # a heard word shared by two script words ("twenty-eight" matched as two pieces is fine;
    # one heard word split across two script words) is split in time between them
    share: dict[int, list[int]] = {}
    for k, hs in got.items():
        for h in hs:
            share.setdefault(h, []).append(k)
    out, notes = [], []
    for k, tok in enumerate(script):
        hs = sorted(got.get(k) or [])
        if not hs:
            notes.append(f"script word `{tok}` was not heard — left off the captions (no time to show it at)")
            continue
        s, e = heard[hs[0]]["start"], heard[hs[-1]]["end"]
        for h, ks in ((hs[0], share[hs[0]]), (hs[-1], share[hs[-1]])):
            if len(ks) > 1:  # one heard word carries several script words: each gets its slice
                n, pos = len(ks), sorted(ks).index(k)
                w0, w1 = heard[h]["start"], heard[h]["end"]
                if h == hs[0]:
                    s = w0 + (w1 - w0) * pos / n
                if h == hs[-1]:
                    e = w0 + (w1 - w0) * (pos + 1) / n
        said_txt = " ".join(str(heard[h]["text"]) for h in hs)
        row = {"text": tok, "start": round(s, 3), "end": round(e, 3)}
        if _letters(said_txt) != _letters(tok):
            row["heard"] = said_txt
        out.append(row)
    for h, w in enumerate(heard):
        if h not in used_heard:
            out.append({**w, "unaligned": True})
            notes.append(f"heard `{w['text']}` at {w['start']:.2f}s lines up with no word of the script — shown as heard")
    out.sort(key=lambda w: (w["start"], w["end"]))
    return out, notes


def fixed(words: list[dict]) -> list[dict]:
    """The words the script re-spelled — {heard, shown} — for the sheet and the page."""
    return [{"heard": w["heard"], "shown": w["text"], "at": w["start"]} for w in words if w.get("heard")]


if __name__ == "__main__":
    import json
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(0)
    heard = json.loads(Path(sys.argv[1]).read_text())
    ws, ns = align(heard["words"] if isinstance(heard, dict) else heard, sys.argv[2])
    print(json.dumps({"words": ws, "notes": ns}, indent=1, ensure_ascii=False))
