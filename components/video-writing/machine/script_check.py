"""Free script checker: structural checks on a timed ad script, no model, no cost per run.

Report only. Nothing here blocks a brief; the exit code is 0 unless --strict is given.
The existing writing re-check (writing_revalidate.py) is not touched and does not call this.

Input: a markdown file holding the script as a table with a Time column and a Line
column (Speaker, Tag and Scene columns are used when present), for example

    | # | Time | Tag | Speaker | Line | Scene |
    | 1 | 0:00.0-0:01.9 | [SOURCE] | Host | Would you do this? | Close shot, hand slams the table. |

The Time cell may be a range (0:00.0-0:01.9) or a start time only (0:00.1); with start times
each row ends where the next one starts, and the last row's end is not written, so it is left
out of the pace check.

A row is "filmed" when its Tag or Scene says filmed / as filmed / [FILMED], or its Speaker is an
interviewee: its words are already in the footage. The breath and pace checks list filmed rows
under "filmed, can't change" and never raise the level for them.

Each check prints PASS, NOTE (a person may look, no change needed), WARN (a person looks)
or FAIL (fix it). When no row can be read the report says "0 rows checked: no result" and
prints no PASS or FAIL. Wording of the checks is brand-free; every threshold is a constant
below so the owner can tune it in one place.

Fix round 2026-11-07: "0 rows checked: no result" header, filmed rows labelled not flagged,
start-time-only tables read, O2 judged inside the first 3 seconds, -ing action verbs counted.

Round 3 2026-11-07 (adds only; every check and output line above stands):
- A row is also filmed when another table in the same file names it (T<n> in its first cell) and
  labels its words filmed in a cell of their own ("verbatim (filmed)", "FILMED-<source>"). A
  filmed line is reported, never failed: the opening, breath, pace and ending checks print NOTE
  for a fault that sits only on filmed rows.
- Conflict pass: T1 is NOTE, not PASS, when the last row's end is not written (continuity is only
  partly checked); B1 names the rows over 14 words beside those over 18; A2 says so when no row
  is static.
- When the audit is given (--audit, or a 4f-audit.md beside the script), the view quotes the
  audit's own lines on breath and pace after the checks, word for word: the sentences of its
  source-compressed and runtime-sanity findings that carry a duration or a rate, and any other
  sentence that names a caveat on the read (wpm, cadence, unmeasured, an N-second line, a fast
  cut). Nothing is re-checked; the quotes are the audit's.

Design adapted from the short-drama-factory episode checker (MIT licence, "validate_episode.py"
as described in its SKILL.md and references/protective-counterexamples.md): the three-level
FAIL / WARN / NOTE output, and the rules behind its E2 (one breath), E4 (conflict in the first
3 seconds), E5 (no build-up opening), E6 (ends on a cut point), E8 (repetition), E15 (no
monologue in the first 3 seconds), E16 (speech rate against the time written), E21 (talk to
action balance), E24 (dry-talk run) and E26 (empty micro-actions). The code is written here,
for English timed ad tables. Checks that only make sense for a numbered drama episode or a
series ledger (E1 volume band, E3 scene limit, E7 emotion chain across episodes, E10 Chinese
red-line words, E11 mid-episode hook, E17 duration floor, E22 typos, S1-S8) are not included.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---- thresholds (one place) -------------------------------------------------
OPENING_SECONDS = 3.0        # E4, E5, E15: the golden opening
BREATH_WARN_WORDS = 14       # E2: words in one spoken sentence
BREATH_FAIL_WORDS = 18
RATE_WARN_WPS = 3.8          # E16: spoken words per second inside one row
RATE_FAIL_WPS = 4.8
TALK_SHARE_MIN = 0.25        # E21: share of runtime that carries speech
TALK_SHARE_MAX = 0.80
DRY_RUN_MAX = 6              # E24: rows in a row with no new picture
KNIFE_WORDS = 5              # cadence: a short, knife-cut sentence
TIME_TOLERANCE = 0.15        # seconds of gap or overlap between rows

# ---- word lists -------------------------------------------------------------
CONFLICT_WORDS = {
    "no", "not", "never", "nobody", "stop", "wrong", "can't", "cant", "don't", "dont",
    "won't", "wont", "didn't", "didnt", "isn't", "isnt", "why", "fail", "failed", "lost",
    "hate", "fight", "broke", "broken", "afraid", "lie", "lied", "worst", "ruined", "refuse",
    "versus", "vs", "before", "after", "mistake", "wasted", "waste", "ashamed", "embarrassed",
}
TENSION_ACTION = {
    "slams", "throws", "shoves", "pushes", "grabs", "rips", "tears", "smashes", "holds",
    "points", "stares", "storms", "slaps", "drops", "shows", "raises", "pulls", "blocks",
    "refuses", "laughs", "recoils", "gasps", "cuts", "snaps", "turns", "covers", "hides",
}
ACTION_VERBS = TENSION_ACTION | {
    "walks", "runs", "reaches", "pours", "opens", "closes", "picks", "lifts", "presses",
    "brushes", "washes", "scrubs", "wipes", "applies", "puts", "places", "hands", "carries",
    "types", "writes", "pays", "signs", "drives", "climbs", "jumps", "dances", "cooks",
    "cuts", "pans", "zooms", "enters", "exits", "leans", "steps", "hugs", "kisses", "waves",
    "swipes", "taps", "scrolls", "unboxes", "pulls", "pushes", "sprays", "splashes",
    "looks", "glances", "nods", "smiles", "turning", "holding", "pointing", "brushing",
    "washing", "reaching", "walking", "pouring", "opening", "running", "showing",
}
OPENING_BUILDUP = re.compile(
    r"^\W*(hi|hello|hey|hey guys|welcome|good (morning|evening|afternoon)|"
    r"today|in this video|let me tell you|so,? today|my name is|have you ever wondered|"
    r"before we (start|begin))\b", re.I)
WRAPUP_LINE = re.compile(
    r"\b(thanks? for watching|thank you for watching|see you (next|in the)|in conclusion|"
    r"to sum up|that's all for today|until next time)\b", re.I)
END_CARD = re.compile(r"\b(end card|title card|fade (out|to black)|logo (lockup|sting)|"
                      r"cut to black|black frame|outro)\b", re.I)
MICRO = re.compile(
    r"\b(slight(ly)? (flicker|start|nod|frown|smile|twitch|tremble)|"
    r"(a )?(flicker|flash) of (the )?eyes|eyes? (flicker|flutter|narrow slightly)|"
    r"lost in thought|(a )?small sigh|barely (nods?|moves?|smiles?)|"
    r"(a )?(faint|slight|subtle|tiny) (smile|frown|shift|movement|change)|"
    r"takes a breath|blinks?|gulps?|swallows?)\b", re.I)
STATIC_START = re.compile(r"^\W*(hold|same\b|stays|static|still\b|unchanged|as before|continues)", re.I)
VOICE_SPEAKER = re.compile(r"\b(narrat|vo\b|v\.o|voice|monolog|inner)\w*", re.I)
NO_SPEECH = re.compile(r"^\W*(hold\b|no words|silent|\(?none\)?|[-–—]+)\W*$", re.I)
TIME_RANGE = re.compile(
    r"(\d+):(\d{1,2}(?:\.\d+)?)\s*[-–—]\s*(\d+):(\d{1,2}(?:\.\d+)?)")
TIME_PLAIN = re.compile(r"(\d+(?:\.\d+)?)\s*s?\s*[-–—]\s*(\d+(?:\.\d+)?)\s*s?")
TIME_POINT = re.compile(r"^\W*(?:(\d+):(\d{1,2}(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*s)\W*$")
FILMED_MARK = re.compile(r"\b(as filmed|filmed)\b|\[filmed\]", re.I)
FILMED_SPEAKER = re.compile(r"^\W*interviewee", re.I)
FILMED_LABEL = re.compile(r"^\W*(verbatim\s*\(\s*filmed\s*\)|(as\s+)?\[?filmed\]?(-[\w-]+)?(\s*\([^)]*\))?)\W*$", re.I)
ROW_REF = re.compile(r"\bT(\d+)\b")
# The audit's own lines on breath and pace (quoted, never re-checked)
AUDIT_PACE_BLOCK = re.compile(r"source (not )?compressed|runtime sanity", re.I)
AUDIT_FIGURE = re.compile(r"\b\d+(?:\.\d+)?\s?s\b|\b\d+(?:\.\d+)?-second\b|\bseconds?\b|\bwpm\b|"
                          r"\d+:\d{2}(?:\.\d+)?\s*[–—-]\s*\d+:\d{2}", re.I)
AUDIT_CAVEAT = re.compile(r"\bwpm\b|\bwords? (?:a|per) (?:second|minute)\b|\bunmeasured\b|\bcadence\b|"
                          r"\bread duration\b|\bpace\b|\bbreaths?\b|\blong run\b|\b\d+(?:\.\d+)?-second\b|"
                          r"\bmeasured speech\b|\b(?:cut|cuts|close|read) (?:is |are )?fast\b|\bfast (?:cut|cuts|close|read)\b", re.I)
AUDIT_SKIP = re.compile(r"provenance", re.I)
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’$%.-]*")


# ---- parsing ----------------------------------------------------------------
def _cells(line):
    parts = [c.strip() for c in line.strip().strip("|").split("|")]
    return parts


def _seconds(text):
    """(start, end) for a range, (start, None) for a start time only, None when unreadable."""
    m = TIME_RANGE.search(text)
    if m:
        a = int(m.group(1)) * 60 + float(m.group(2))
        b = int(m.group(3)) * 60 + float(m.group(4))
        return a, b
    m = TIME_PLAIN.search(text)
    if m:
        return float(m.group(1)), float(m.group(2))
    m = TIME_POINT.match(_clean(text))
    if m:
        if m.group(1) is not None:
            return int(m.group(1)) * 60 + float(m.group(2)), None
        return float(m.group(3)), None
    return None


def _clean(text):
    return re.sub(r"[*_`]", "", text).strip().strip('"“”').strip()


def parse_rows(text):
    """Return the rows of the first table that has a Time column and a Line column."""
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|"):
            j = i
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                j += 1
            block = lines[i:j]
            i = j
            header = [h.lower() for h in _cells(block[0])]
            time_ix = next((k for k, h in enumerate(header) if h.startswith("time")), None)
            line_ix = next((k for k, h in enumerate(header)
                            if h in ("line", "lines", "spoken", "text", "dialogue", "words")), None)
            if time_ix is None or line_ix is None:
                continue
            speaker_ix = next((k for k, h in enumerate(header) if h.startswith("speaker")), None)
            scene_ix = next((k for k, h in enumerate(header)
                             if h.startswith("scene") or h.startswith("picture") or h.startswith("visual")), None)
            tag_ix = next((k for k, h in enumerate(header) if h == "tag"), None)
            num_ix = next((k for k, h in enumerate(header) if h in ("#", "beat", "no", "n")), None)
            rows = []
            for raw in block[1:]:
                cells = _cells(raw)
                if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    continue
                if len(cells) <= max(time_ix, line_ix):
                    continue
                span = _seconds(cells[time_ix])
                if span is None:
                    continue
                get = lambda ix: _clean(cells[ix]) if ix is not None and ix < len(cells) else ""
                spoken = get(line_ix)
                has_speech = bool(spoken) and not NO_SPEECH.match(spoken) and not spoken.upper().startswith("HOLD")
                tag, speaker, scene = get(tag_ix), get(speaker_ix), get(scene_ix)
                rows.append({
                    "n": get(num_ix) or str(len(rows) + 1),
                    "start": span[0], "end": span[1],
                    "tag": tag, "speaker": speaker,
                    "line": spoken if has_speech else "",
                    "raw_line": spoken, "scene": scene,
                    "filmed": bool(FILMED_MARK.search(tag) or FILMED_MARK.search(scene)
                                   or FILMED_SPEAKER.match(speaker)),
                    "open_end": False,
                })
            if rows:
                _filmed_elsewhere(lines[:j - len(block)] + lines[j:], rows)
                return _close_ends(rows)
        else:
            i += 1
    return []


def _norm(text):
    return " ".join(w.lower() for w in words(text))


def _filmed_elsewhere(other, rows):
    """Rows another table names (T<n>) and labels filmed in a cell of their own."""
    refs, texts = set(), []
    for line in other:
        if not line.lstrip().startswith("|"):
            continue
        cells = [_clean(c) for c in _cells(line)]
        if len(cells) < 2 or not any(FILMED_LABEL.match(c) for c in cells[1:] if c):
            continue
        refs.update(ROW_REF.findall(cells[0]))
        texts.append(_norm(" ".join(cells[1:])))
    if not refs and not texts:
        return
    for r in rows:
        if r["filmed"]:
            continue
        key = _norm(r["line"])
        if re.sub(r"^\W*T", "", r["n"]) in refs or (len(key.split()) >= 3 and any(key in t for t in texts)):
            r["filmed"] = True


def _close_ends(rows):
    """Start-time-only rows end where the next row starts; the last one stays open."""
    for a, b in zip(rows, rows[1:]):
        if a["end"] is None:
            a["end"] = b["start"]
    if rows[-1]["end"] is None:
        rows[-1]["end"] = rows[-1]["start"]
        rows[-1]["open_end"] = True
    return rows


def _filmed_note(items):
    return "filmed, can't change: " + "; ".join(items[:4]) if items else ""


def _join(*parts):
    return "; ".join(p for p in parts if p)


def _acts(text):
    """Action verbs in a scene, counting -ing forms (picking -> picks)."""
    out = set()
    for w in (w.lower() for w in words(text)):
        if w in ACTION_VERBS:
            out.add(w)
        elif w.endswith("ing") and len(w) > 5:
            stem = w[:-3]
            for cand in (stem + "s", stem + "es", stem[:-1] + "s" if len(stem) > 2 and stem[-1] == stem[-2] else ""):
                if cand in ACTION_VERBS:
                    out.add(w)
                    break
    return out


def words(text):
    return WORD.findall(text)


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?!…])\s+", text) if words(s)]


# ---- checks -----------------------------------------------------------------
def _res(code, name, level, detail, source):
    return {"code": code, "check": name, "level": level, "detail": detail, "mirrors": source}


def check_timing(rows):
    bad = []
    for r in rows:
        if r["open_end"]:
            continue
        if r["end"] <= r["start"]:
            bad.append("row %s: ends at %.1fs, not after its start %.1fs" % (r["n"], r["end"], r["start"]))
    for a, b in zip(rows, rows[1:]):
        gap = b["start"] - a["end"]
        if abs(gap) > TIME_TOLERANCE:
            kind = "gap" if gap > 0 else "overlap"
            bad.append("rows %s-%s: %.1fs %s" % (a["n"], b["n"], abs(gap), kind))
    if bad:
        return _res("T1", "timing is continuous", "WARN", "; ".join(bad[:6]), "E16")
    if rows[-1]["open_end"]:
        return _res("T1", "timing is continuous", "NOTE",
                    "%d rows, start times only: each row ends where the next starts; last row starts at %.1fs, "
                    "its end is not written" % (len(rows), rows[-1]["start"]), "E16")
    return _res("T1", "timing is continuous", "PASS",
                "%d rows, %.1fs, no gap or overlap" % (len(rows), rows[-1]["end"] - rows[0]["start"]), "E16")


def check_opening_conflict(rows):
    opening = [r for r in rows if r["start"] < OPENING_SECONDS]
    signals = []
    for r in opening:
        low = [w.lower() for w in words(r["line"])]
        if "?" in r["line"]:
            signals.append("row %s asks a question" % r["n"])
        hits = sorted(set(low) & CONFLICT_WORDS)
        if hits:
            signals.append("row %s says %s" % (r["n"], "/".join(hits)))
        sc = {w.lower() for w in words(r["scene"])}
        acts = sorted(sc & TENSION_ACTION)
        if acts:
            signals.append("row %s shows %s" % (r["n"], "/".join(acts)))
    if signals:
        return _res("O1", "conflict in the first 3 seconds", "PASS", "; ".join(signals[:4]), "E4")
    spoken = [r for r in opening if r["line"]]
    if spoken and all(r["filmed"] for r in spoken):
        return _res("O1", "conflict in the first 3 seconds", "NOTE",
                    _filmed_note(["row %s" % r["n"] for r in spoken])
                    + " (nothing in the first %.0fs asks, denies, shows tension or contrast)" % OPENING_SECONDS, "E4")
    return _res("O1", "conflict in the first 3 seconds", "FAIL",
                "nothing in the first %.0fs asks, denies, shows tension or contrast" % OPENING_SECONDS, "E4")


def check_opening_buildup(rows):
    first = next((r for r in rows if r["line"]), None)
    if first is None:
        return _res("O2", "no build-up opening", "NOTE", "no spoken line in the script", "E5")
    if first["start"] >= OPENING_SECONDS:
        return _res("O2", "no build-up opening", "PASS",
                    "no speech in the first %.0fs; first line at %.1fs (row %s)"
                    % (OPENING_SECONDS, first["start"], first["n"]), "E5")
    if OPENING_BUILDUP.search(first["line"]) and first["filmed"]:
        return _res("O2", "no build-up opening", "NOTE",
                    _filmed_note(['row %s opens with a greeting or set-up: "%s"' % (first["n"], first["line"][:60])]), "E5")
    if OPENING_BUILDUP.search(first["line"]):
        return _res("O2", "no build-up opening", "FAIL",
                    'row %s opens with a greeting or set-up: "%s"' % (first["n"], first["line"][:60]), "E5")
    return _res("O2", "no build-up opening", "PASS", 'first line: "%s"' % first["line"][:60], "E5")


def check_opening_voice(rows):
    early = [r for r in rows if r["line"] and r["start"] < OPENING_SECONDS and VOICE_SPEAKER.search(r["speaker"])]
    if early:
        return _res("O3", "no voice-over in the first 3 seconds", "WARN",
                    "row %s is carried by %s" % (early[0]["n"], early[0]["speaker"]), "E15")
    return _res("O3", "no voice-over in the first 3 seconds", "PASS", "the opening is on-camera speech or silence", "E15")


def check_breath(rows):
    fail, warn, filmed = [], [], []
    for r in rows:
        for s in sentences(r["line"]):
            n = len(words(s))
            if n <= BREATH_WARN_WORDS:
                continue
            tag = 'row %s: %d words "%s..."' % (r["n"], n, s[:40])
            if r["filmed"]:
                filmed.append(tag)
            elif n > BREATH_FAIL_WORDS:
                fail.append(tag)
            else:
                warn.append(tag)
    note = _filmed_note(filmed)
    if fail:
        return _res("B1", "one breath per sentence", "FAIL",
                    _join("%d over %d words, %d over %d: %s" % (len(fail), BREATH_FAIL_WORDS, len(warn), BREATH_WARN_WORDS,
                                                                "; ".join(fail[:3])),
                          "over %d: %s" % (BREATH_WARN_WORDS, "; ".join(warn[:3])) if warn else "", note), "E2")
    if warn:
        return _res("B1", "one breath per sentence", "WARN",
                    _join("%d over %d words: %s" % (len(warn), BREATH_WARN_WORDS, "; ".join(warn[:3])), note), "E2")
    if filmed:
        return _res("B1", "one breath per sentence", "NOTE", note, "E2")
    return _res("B1", "one breath per sentence", "PASS", "every sentence is %d words or fewer" % BREATH_WARN_WORDS, "E2")


def check_cadence(rows):
    lengths = [len(words(s)) for r in rows for s in sentences(r["line"])]
    if len(lengths) < 4:
        return _res("B2", "short and long lines alternate", "NOTE", "fewer than 4 sentences", "dialogue dimension 7")
    short = sum(1 for n in lengths if n <= KNIFE_WORDS)
    if short == 0:
        return _res("B2", "short and long lines alternate", "WARN",
                    "no sentence of %d words or fewer in %d sentences" % (KNIFE_WORDS, len(lengths)), "dialogue dimension 7")
    return _res("B2", "short and long lines alternate", "PASS",
                "%d of %d sentences are %d words or fewer" % (short, len(lengths), KNIFE_WORDS), "dialogue dimension 7")


def check_rate(rows):
    fail, warn, filmed, open_rows = [], [], [], []
    for r in rows:
        n, dur = len(words(r["line"])), r["end"] - r["start"]
        if r["open_end"] and n:
            open_rows.append("row %s: end not written, pace not checked" % r["n"])
            continue
        if n < 4 or dur <= 0:
            continue
        wps = n / dur
        if wps <= RATE_WARN_WPS:
            continue
        tag = "row %s: %d words in %.1fs (%.1f/s)" % (r["n"], n, dur, wps)
        if r["filmed"]:
            filmed.append(tag)
        elif wps > RATE_FAIL_WPS:
            fail.append(tag)
        else:
            warn.append(tag)
    extra = _join(_filmed_note(filmed), "; ".join(open_rows))
    if fail:
        return _res("B3", "the words fit the time written", "FAIL", _join("; ".join(fail[:4]), extra), "E16")
    if warn:
        return _res("B3", "the words fit the time written", "WARN", _join("; ".join(warn[:4]), extra), "E16")
    if filmed:
        return _res("B3", "the words fit the time written", "NOTE", extra, "E16")
    return _res("B3", "the words fit the time written", "PASS",
                _join("no row above %.1f words per second" % RATE_WARN_WPS, extra), "E16")


def check_balance(rows):
    total = rows[-1]["end"] - rows[0]["start"]
    if total <= 0:
        return _res("A1", "talk against action balance", "NOTE", "no runtime", "E21")
    talk = sum(r["end"] - r["start"] for r in rows if r["line"])
    share = talk / total
    detail = "speech covers %.0f%% of %.0fs" % (share * 100, total)
    if rows[-1]["open_end"]:
        detail += " (start times only: a spoken row counts as speech for its whole span)"
    if share < TALK_SHARE_MIN or share > TALK_SHARE_MAX:
        return _res("A1", "talk against action balance", "WARN",
                    detail + ", outside %.0f-%.0f%%" % (TALK_SHARE_MIN * 100, TALK_SHARE_MAX * 100), "E21")
    return _res("A1", "talk against action balance", "PASS", detail, "E21")


def _static(scene):
    if not scene.strip():
        return True
    if STATIC_START.match(scene):
        return True
    toks = {w.lower() for w in words(scene)}
    return len(toks) <= 6 and not _acts(scene)


def check_dry_run(rows):
    best, run, at = 0, 0, None
    for r in rows:
        if _static(r["scene"]):
            run += 1
            if run > best:
                best, at = run, r["n"]
        else:
            run = 0
    if best > DRY_RUN_MAX:
        return _res("A2", "no long stretch with no new picture", "WARN",
                    "%d rows in a row with no new action, ending at row %s" % (best, at), "E24")
    if best == 0:
        return _res("A2", "no long stretch with no new picture", "PASS",
                    "every one of %d rows shows a new action; no static row (limit %d in a row)" % (len(rows), DRY_RUN_MAX), "E24")
    return _res("A2", "no long stretch with no new picture", "PASS",
                "longest static run is %d rows (limit %d)" % (best, DRY_RUN_MAX), "E24")


def check_micro(rows):
    hits = []
    for r in rows:
        m = MICRO.search(r["scene"])
        if not m:
            continue
        if not _acts(MICRO.sub(" ", r["scene"])):
            hits.append('row %s: "%s"' % (r["n"], m.group(0)))
    if hits:
        return _res("A3", "no empty micro-actions", "WARN",
                    "only a micro-action, nothing filmable: " + "; ".join(hits[:4]), "E26")
    return _res("A3", "no empty micro-actions", "PASS", "no row relies on a flicker, blink or sigh alone", "E26")


def check_repeat(rows):
    seen, dup = {}, []
    for r in rows:
        for s in sentences(r["line"]):
            key = " ".join(w.lower() for w in words(s))
            if len(key.split()) < 3:
                continue
            if key in seen:
                dup.append('row %s repeats row %s: "%s"' % (r["n"], seen[key], s[:40]))
            else:
                seen[key] = r["n"]
    if dup:
        return _res("R1", "no repeated line", "WARN", "; ".join(dup[:3]), "E8")
    return _res("R1", "no repeated line", "PASS", "no spoken sentence appears twice", "E8")


def check_ending(rows):
    last = rows[-1]
    if WRAPUP_LINE.search(last["line"]) and last["filmed"] and not END_CARD.search(last["scene"]):
        return _res("E1", "ends mid-action", "NOTE",
                    _filmed_note(["row %s closes on a wrap-up line" % last["n"]]), "E6")
    if WRAPUP_LINE.search(last["line"]) or END_CARD.search(last["scene"]):
        return _res("E1", "ends mid-action", "FAIL",
                    "row %s closes on a wrap-up line or a card, not an action" % last["n"], "E6")
    acts = sorted(_acts(last["scene"]))
    if acts:
        return _res("E1", "ends mid-action", "PASS",
                    "row %s ends on action: %s" % (last["n"], "/".join(acts[:3])), "E6")
    return _res("E1", "ends mid-action", "WARN",
                "row %s shows no action in progress at the final cut" % last["n"], "E6")


CHECKS = [check_timing, check_opening_conflict, check_opening_buildup, check_opening_voice,
          check_breath, check_cadence, check_rate, check_balance, check_dry_run, check_micro,
          check_repeat, check_ending]


NO_RESULT = "0 rows checked: no result"


def _title(heading):
    return heading.capitalize().replace(" i ", " I ")


def _audit_sentences(text):
    return [t.strip() for t in re.split(r"(?<=[.?!])\s+(?=[A-Z0-9\"“(\[~])", text) if t.strip()]


def _audit_pick(text, pace):
    """The sentences worth quoting, with "…" where sentences were left out between them."""
    out, gap = [], False
    for sent in _audit_sentences(text):
        keep = AUDIT_CAVEAT.search(sent) or (pace and AUDIT_FIGURE.search(sent))
        if keep:
            if gap and out:
                out.append("…")
            out.append(sent)
            gap = False
        else:
            gap = True
    return " ".join(out)


def audit_lines(text):
    """The audit's own lines on breath and pace, quoted word for word: [{"where", "quote"}]."""
    found, heading = [], ""
    lines = text.splitlines()
    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line or re.fullmatch(r"[-*_]{3,}", line):
            continue
        bold = re.fullmatch(r"\*\*([^*]+)\*\*", line)
        if line.startswith("#") or bold:
            heading = _clean(bold.group(1) if bold else line.lstrip("#"))
            continue
        if AUDIT_SKIP.search(heading):
            continue
        if line.startswith("|"):
            cells = [_clean(c) for c in _cells(line)]
            if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                continue
            nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
            if nxt.startswith("|") and all(re.fullmatch(r":?-{2,}:?", c) for c in _cells(nxt) if c):
                continue    # a header row
            if len(cells) >= 4 and re.fullmatch(r"\d+|[—–-]", cells[0]):
                name = cells[1]
                where = "Check %s, %s" % (cells[0], name) if cells[0].isdigit() else name
                quote = _audit_pick(cells[-1], bool(AUDIT_PACE_BLOCK.search(name)))
            else:
                where = _title(heading) if heading else "Table row"
                quote = _audit_pick(" | ".join(c for c in cells if c), bool(AUDIT_PACE_BLOCK.search(heading)))
        else:
            item = re.match(r"^(\d+)[.)]\s+(.*)$", line)
            body = _clean(item.group(2) if item else line.lstrip("-* ").strip())
            where = (_title(heading) if heading else "Audit") + (", point %s" % item.group(1) if item else "")
            quote = _audit_pick(body, bool(AUDIT_PACE_BLOCK.search(heading)))
        if quote:
            found.append({"where": where, "quote": quote})
    return found


def run(text):
    rows = parse_rows(text)
    if not rows:
        return {"rows": 0, "result": "none", "filmed": 0,
                "results": [_res("P0", "script table found", "NONE",
                            "no table with a Time column and a Line column whose times can be read", "-")],
                "counts": {"FAIL": 0, "WARN": 0, "NOTE": 0, "PASS": 0}}
    results = [c(rows) for c in CHECKS]
    counts = {k: 0 for k in ("FAIL", "WARN", "NOTE", "PASS")}
    for r in results:
        counts[r["level"]] += 1
    return {"rows": len(rows), "result": "checked", "filmed": sum(1 for r in rows if r["filmed"]),
            "runtime": round(rows[-1]["end"] - rows[0]["start"], 1),
            "results": results, "counts": counts}


def render(report):
    out = []
    c = report["counts"]
    if not report["rows"]:
        out.append("SCRIPT CHECK (report only, blocks nothing): " + NO_RESULT)
        for r in report["results"]:
            out.append("  %s" % r["detail"])
        out += _render_audit(report)
        return "\n".join(out)
    filmed = " (%d filmed)" % report["filmed"] if report.get("filmed") else ""
    out.append("SCRIPT CHECK (report only, blocks nothing): %d FAIL · %d WARN · %d NOTE · %d PASS · %s rows%s"
               % (c["FAIL"], c["WARN"], c["NOTE"], c["PASS"], report["rows"], filmed))
    for r in report["results"]:
        out.append("  %-4s %-4s %-38s %s" % (r["level"], r["code"], r["check"], r["detail"]))
    out += _render_audit(report)
    return "\n".join(out)


def run_with_audit(text, audit=None):
    """run(), plus the audit's own lines on breath and pace when the audit is given."""
    report = run(text)
    if audit is not None:
        report["audit_lines"] = audit_lines(audit)
    return report


def _render_audit(report):
    if "audit_lines" not in report:
        return []
    if not report["audit_lines"]:
        return ["AUDIT (quoted, not re-checked): no line on breath or pace in the audit"]
    return ["AUDIT (quoted, not re-checked): the audit's own lines on breath and pace"] + \
        ['  - %s: "%s"' % (a["where"], a["quote"]) for a in report["audit_lines"]]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Free script checker. Report only.")
    ap.add_argument("script", help="markdown file holding the timed script table")
    ap.add_argument("--json", action="store_true", help="print the report as JSON")
    ap.add_argument("--strict", action="store_true", help="exit 1 when any check is FAIL (off by default)")
    ap.add_argument("--audit", help="the audit's output, quoted after the checks (default: 4f-audit.md beside the script)")
    a = ap.parse_args(argv)
    p = Path(a.script)
    if not p.is_file():
        print("no such file: %s" % p, file=sys.stderr)
        return 2
    audit = Path(a.audit) if a.audit else p.parent / "4f-audit.md"
    if a.audit and not audit.is_file():
        print("no such audit file: %s" % audit, file=sys.stderr)
        return 2
    report = run(p.read_text(encoding="utf-8"))
    if audit.is_file():
        report["audit_lines"] = audit_lines(audit.read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, ensure_ascii=False) if a.json else render(report))
    return 1 if a.strict and report["counts"]["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
